"""
HORIZON Classical Beacon Detector Engine
===============================================
Phase 4 Classical optical beacon detector for coarse alignment of FSOC terminals.
Performs:
  1. Strict input validation (640×480, uint8, grayscale)
  2. Preprocessing & adaptive impulse noise removal
  3. Background floor & noise variance estimation
  4. Adaptive thresholding & candidate connected component extraction
  5. Multi-criteria candidate scoring & distractor rejection
  6. Subpixel centroiding (Weighted CoG, Geometric, or 2D Gaussian Surface Fit)
  7. Normalized confidence calculation in [0.0, 1.0]

Strict Invariant: Zero ground-truth leakage or dependencies.
"""

from __future__ import annotations

from dataclasses import dataclass
import time
from typing import Optional, Tuple
import cv2
import numpy as np

from simulator.perception.candidate import BeaconCandidate, extract_candidates
from simulator.perception.centroid import (
    compute_gaussian_fit,
    compute_geometric_centroid,
    compute_weighted_cog,
)
from simulator.perception.config import DetectorConfig
from simulator.perception.diagnostics import (
    DetectionDiagnostics,
    create_annotated_frame,
)
from simulator.perception.preprocessing import (
    apply_adaptive_median_filter,
    estimate_background_statistics,
    validate_input_frame,
)


@dataclass(frozen=True)
class DetectionResult:
    """Standardized output of the perception beacon detector."""
    detected: bool
    centroid: Optional[Tuple[float, float]]  # (u, v) in sensor coordinates
    bbox: Optional[Tuple[int, int, int, int]]  # (x, y, w, h)
    confidence: float                        # Range [0.0, 1.0]
    candidate_count: int
    method_used: str
    processing_time_ms: float
    diagnostics: Optional[DetectionDiagnostics] = None
    timestamp: float = 0.0
    candidates: Optional[Tuple[BeaconCandidate, ...]] = None
    detector_source: str = "CLASSICAL"
    centroid_source: str = "WEIGHTED_COG"
    agreement_state: str = "AGREEMENT"
    fused_confidence: float = 0.0
    decision_reason: str = ""
    unified_candidates: Optional[Tuple[Any, ...]] = None


class ClassicalBeaconDetector:
    """Classical computer-vision beacon detector for FSOC optical camera feeds.

    Parameters:
        config: DetectorConfig dataclass.
    """

    def __init__(self, config: Optional[DetectorConfig] = None) -> None:
        self._config = config or DetectorConfig()

    @property
    def config(self) -> DetectorConfig:
        return self._config

    def detect(
        self,
        frame: np.ndarray,
        timestamp: float = 0.0,
        collect_diagnostics: bool = False,
    ) -> DetectionResult:
        """Process a 640×480 optical frame and locate the beacon centroid.

        Args:
            frame: 2D uint8 optical camera frame (640×480).
            timestamp: Optional simulation timestamp in seconds.
            collect_diagnostics: Toggle creation of diagnostic visual artifacts.

        Returns:
            DetectionResult dataclass containing detected flag, centroid (u, v),
            confidence, bounding box, and timing metadata.
        """
        t_start = time.perf_counter()

        # 1. Input Validation
        valid_frame = validate_input_frame(
            frame,
            expected_width=self._config.input_width,
            expected_height=self._config.input_height,
        )

        # 2. Preprocessing & Background Estimation
        preprocessed = apply_adaptive_median_filter(
            valid_frame, self._config.preprocessing
        )
        bg_level, noise_std = estimate_background_statistics(preprocessed)

        # 3. Candidate Extraction & Scoring
        candidates, thresh_mask = extract_candidates(
            frame=valid_frame,
            preprocessed=preprocessed,
            bg_level=bg_level,
            noise_std=noise_std,
            config=self._config.scoring,
        )

        # 4. Candidate Selection
        selected: Optional[BeaconCandidate] = None
        if candidates:
            best_cand = candidates[0]
            if best_cand.score >= self._config.min_detection_confidence:
                selected = best_cand

        # 5. Centroid Computation
        centroid: Optional[Tuple[float, float]] = None
        method_used = self._config.centroid.method
        roi_crop: Optional[np.ndarray] = None

        if selected is not None:
            x, y, w, h = selected.bbox
            pad = self._config.centroid.roi_padding_px

            # Bounded ROI extraction
            x1 = max(0, x - pad)
            y1 = max(0, y - pad)
            x2 = min(self._config.input_width, x + w + pad)
            y2 = min(self._config.input_height, y + h + pad)

            roi_orig = valid_frame[y1:y2, x1:x2]
            roi_mask = thresh_mask[y1:y2, x1:x2]
            roi_crop = roi_orig.copy()

            if method_used == "geometric":
                centroid = compute_geometric_centroid(roi_mask, x1, y1)
            elif method_used == "gaussian_fit":
                u, v, fit_ok = compute_gaussian_fit(
                    roi_orig,
                    roi_mask,
                    bg_level,
                    x1,
                    y1,
                    self._config.centroid,
                )
                centroid = (u, v)
                if not fit_ok:
                    method_used = "gaussian_fit_fallback_cog"
            else:  # default "weighted_cog"
                centroid = compute_weighted_cog(
                    roi_orig, roi_mask, bg_level, x1, y1
                )

        # 6. Confidence Assignment
        confidence = float(selected.score) if selected is not None else 0.0
        confidence = float(np.clip(confidence, 0.0, 1.0))

        # 7. Diagnostics Assembly
        diagnostics: Optional[DetectionDiagnostics] = None
        if collect_diagnostics:
            annotated = create_annotated_frame(
                valid_frame, candidates, selected, centroid
            )
            diagnostics = DetectionDiagnostics(
                raw_frame=valid_frame.copy(),
                preprocessed_frame=preprocessed.copy(),
                threshold_mask=thresh_mask.copy(),
                annotated_frame=annotated,
                roi_crop=roi_crop,
            )

        t_end = time.perf_counter()
        elapsed_ms = (t_end - t_start) * 1000.0

        return DetectionResult(
            detected=(selected is not None),
            centroid=centroid,
            bbox=selected.bbox if selected is not None else None,
            confidence=confidence,
            candidate_count=len(candidates),
            method_used=method_used,
            processing_time_ms=elapsed_ms,
            diagnostics=diagnostics,
            timestamp=float(timestamp),
            candidates=tuple(candidates),
        )
