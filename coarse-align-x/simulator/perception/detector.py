"""
HORIZON Classical Beacon Detector Engine
===============================================
Phase 4 UPGRADE: High-quality optical-spot reference detector and uncertainty provider.

Implements:
  1. Strict input validation (640×480, uint8, grayscale)
  2. Preprocessing & adaptive impulse noise removal
  3. Adaptive background model with per-candidate annular estimation
  4. Adaptive thresholding responding to local conditions (not a global constant)
  5. Multi-candidate representation with rich quality fields per candidate
  6. Optical shape validation (compactness, symmetry, radial consistency, size plausibility)
  7. Subpixel centroiding with propagated uncertainty (Weighted CoG + Gaussian fit)
  8. Centroid uncertainty estimation (sigma_u, sigma_v) — no ground truth used
  9. Detection quality metrics breakdown per quality dimension
 10. False-lock defense via multi-gate rejection (5 independent rejection criteria)
 11. Edge/clipping detection and flagging
 12. Detection diagnostics with profiling breakdown

Strict Invariant: Zero ground-truth leakage or dependencies.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

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
class DetectionQuality:
    """Decomposed detection quality metrics — not a single opaque score.

    Each dimension is independently interpretable for diagnostics and tracking
    quality gating. No single dimension dominates the final accepted/rejected decision.
    """
    snr: float                   # Signal-to-noise ratio of selected candidate
    circularity: float           # Shape circularity score [0, 1]
    compactness: float           # Shape compactness score [0, 1]
    symmetry: float              # Bilateral symmetry score [0, 1]
    radial_consistency: float    # Gaussian profile consistency [0, 1]
    size_plausibility: float     # Scale match quality [0, 1]
    local_contrast: float        # Peak minus local background (DN)
    bg_mean: float               # Estimated local background mean (DN)
    bg_variance: float           # Estimated local background variance
    integrated_flux: float       # Background-subtracted total signal flux
    clipped_by_edge: bool        # True if beacon touches frame boundary
    scale_class_px: int          # Best matching beacon scale (5/10/15/20)
    candidate_count: int         # Total candidate count before selection
    centroid_method: str         # Centroid method used (weighted_cog / gaussian_fit / geometric)
    gaussian_fit_succeeded: bool # Whether Gaussian fit converged


@dataclass(frozen=True)
class DetectionResult:
    """Standardised output of the Phase 4 perception beacon detector.

    Exposes centroid uncertainty estimates and quality breakdown.
    Zero ground-truth information is used or leaked.
    """
    # Core detection outputs
    detected: bool
    centroid: Optional[Tuple[float, float]]   # (u, v) subpixel sensor coordinates
    bbox: Optional[Tuple[int, int, int, int]] # (x, y, w, h) bounding box
    confidence: float                          # [0.0, 1.0] composite score

    # Performance profiling
    processing_time_ms: float                  # Total processing wall-clock time
    candidate_count: int                       # Number of valid candidates extracted
    method_used: str                           # Centroid method identifier

    # Centroid uncertainty (derived from photon-noise statistics only)
    # Default 1.0 px used by legacy callers (neural, hybrid) that don't propagate uncertainty yet
    sigma_u_px: float = 1.0                    # 1-sigma uncertainty in u (pixels)
    sigma_v_px: float = 1.0                    # 1-sigma uncertainty in v (pixels)

    # Rich quality breakdown (not collapsed into one number)
    quality: Optional[DetectionQuality] = None

    # All valid candidates with full quality fields
    candidates: Optional[Tuple[BeaconCandidate, ...]] = None

    # Metadata
    timestamp: float = 0.0
    diagnostics: Optional[DetectionDiagnostics] = None

    # Extended fields for hybrid/fusion layers
    detector_source: str = "CLASSICAL"
    centroid_source: str = "WEIGHTED_COG"
    agreement_state: str = "AGREEMENT"
    fused_confidence: float = 0.0
    decision_reason: str = ""
    unified_candidates: Optional[Tuple[Any, ...]] = None


class ClassicalBeaconDetector:
    """Classical computer-vision beacon detector for FSOC optical camera feeds.

    Phase 4 Upgrade: Fully adaptive, multi-scale, uncertainty-providing detector.
    Processes 640×480 uint8 grayscale frames and outputs:
      - Subpixel centroid (u, v)
      - Centroid uncertainty (sigma_u, sigma_v) from photon-noise propagation
      - Full candidate list with rich per-candidate quality fields
      - Detection quality breakdown per dimension

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

        Phase 4 Pipeline:
          1. Input Validation
          2. Adaptive Impulse Noise Removal
          3. Robust Global Background Statistics (MAD)
          4. Adaptive Threshold & Multi-Candidate Extraction
             (Annular per-candidate background model + 5-gate rejection)
          5. Best Candidate Selection (false-lock defense: score threshold gate)
          6. Subpixel Centroid Computation with Uncertainty Propagation
          7. Detection Quality Metrics Assembly
          8. Diagnostics Collection (optional, controlled by flag)

        Args:
            frame:               2D uint8 optical camera frame (640×480).
            timestamp:           Optional simulation timestamp in seconds.
            collect_diagnostics: Toggle creation of diagnostic visual artifacts.

        Returns:
            DetectionResult with centroid, uncertainty, candidates, quality metrics.
        """
        t_start = time.perf_counter()

        # -----------------------------------------------------------------------
        # Stage 1: Input Validation
        # -----------------------------------------------------------------------
        t_s1 = time.perf_counter()
        valid_frame = validate_input_frame(
            frame,
            expected_width=self._config.input_width,
            expected_height=self._config.input_height,
        )
        t_s1 = (time.perf_counter() - t_s1) * 1000.0

        # -----------------------------------------------------------------------
        # Stage 2: Preprocessing & Global Background Estimation
        # -----------------------------------------------------------------------
        t_s2 = time.perf_counter()
        preprocessed = apply_adaptive_median_filter(
            valid_frame, self._config.preprocessing
        )
        bg_level, noise_std = estimate_background_statistics(preprocessed)
        t_s2 = (time.perf_counter() - t_s2) * 1000.0

        # -----------------------------------------------------------------------
        # Stage 3: Adaptive Candidate Extraction (multi-scale, adaptive threshold)
        # -----------------------------------------------------------------------
        t_s3 = time.perf_counter()
        candidates, thresh_mask = extract_candidates(
            frame=valid_frame,
            preprocessed=preprocessed,
            bg_level=bg_level,
            noise_std=noise_std,
            config=self._config.scoring,
        )
        t_s3 = (time.perf_counter() - t_s3) * 1000.0

        # -----------------------------------------------------------------------
        # Stage 4: Best Candidate Selection with False-Lock Defense
        # False-lock defense: selected candidate must exceed minimum confidence
        # threshold. All other candidates are retained in the output for
        # downstream tracking layers to inspect.
        # -----------------------------------------------------------------------
        selected: Optional[BeaconCandidate] = None
        if candidates:
            best_cand = candidates[0]
            if best_cand.score >= self._config.min_detection_confidence:
                selected = best_cand
            # Secondary false-lock check: if edge-clipped candidate is the
            # ONLY candidate and its score is marginal, prefer no detection
            # over false lock (anti-edge hallucination)
            if (
                selected is not None
                and selected.clipped_by_edge
                and len(candidates) == 1
                and selected.score < self._config.min_detection_confidence + 0.10
            ):
                selected = None

        # -----------------------------------------------------------------------
        # Stage 5: Subpixel Centroid Computation with Uncertainty
        # -----------------------------------------------------------------------
        t_s5 = time.perf_counter()
        centroid: Optional[Tuple[float, float]] = None
        sigma_u: float = 1.0
        sigma_v: float = 1.0
        method_used = self._config.centroid.method
        roi_crop: Optional[np.ndarray] = None
        gaussian_fit_ok: bool = False

        if selected is not None:
            x, y, w, h = selected.bbox
            pad = self._config.centroid.roi_padding_px

            # Bounded ROI extraction with edge clamping
            x1 = max(0, x - pad)
            y1 = max(0, y - pad)
            x2 = min(self._config.input_width, x + w + pad)
            y2 = min(self._config.input_height, y + h + pad)

            roi_orig = valid_frame[y1:y2, x1:x2]
            roi_mask = thresh_mask[y1:y2, x1:x2]
            roi_crop = roi_orig.copy()

            # Use per-candidate adaptive background for centroid computation
            bg_for_centroid = selected.background_level

            if method_used == "geometric":
                u, v, sigma_u, sigma_v = compute_geometric_centroid(
                    roi_mask, x1, y1
                )
                centroid = (u, v)

            elif method_used == "gaussian_fit":
                u, v, sigma_u, sigma_v, gaussian_fit_ok = compute_gaussian_fit(
                    roi_orig,
                    roi_mask,
                    bg_for_centroid,
                    x1,
                    y1,
                    self._config.centroid,
                )
                centroid = (u, v)
                if not gaussian_fit_ok:
                    method_used = "gaussian_fit_fallback_cog"

            else:  # default "weighted_cog"
                u, v, sigma_u, sigma_v = compute_weighted_cog(
                    roi_orig, roi_mask, bg_for_centroid, x1, y1
                )
                centroid = (u, v)

        t_s5 = (time.perf_counter() - t_s5) * 1000.0

        # -----------------------------------------------------------------------
        # Stage 6: Confidence & Quality Metrics Assembly
        # -----------------------------------------------------------------------
        confidence = float(selected.score) if selected is not None else 0.0
        confidence = float(np.clip(confidence, 0.0, 1.0))

        quality: Optional[DetectionQuality] = None
        if selected is not None:
            quality = DetectionQuality(
                snr=selected.snr,
                circularity=selected.circularity,
                compactness=selected.compactness,
                symmetry=selected.symmetry,
                radial_consistency=selected.radial_consistency,
                size_plausibility=selected.size_plausibility,
                local_contrast=selected.local_contrast,
                bg_mean=selected.background_level,
                bg_variance=selected.bg_variance,
                integrated_flux=selected.integrated_flux,
                clipped_by_edge=selected.clipped_by_edge,
                scale_class_px=selected.scale_class,
                candidate_count=len(candidates),
                centroid_method=method_used,
                gaussian_fit_succeeded=gaussian_fit_ok,
            )

        # -----------------------------------------------------------------------
        # Stage 7: Diagnostics Assembly
        # -----------------------------------------------------------------------
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
            sigma_u_px=sigma_u,
            sigma_v_px=sigma_v,
            candidate_count=len(candidates),
            method_used=method_used,
            processing_time_ms=elapsed_ms,
            quality=quality,
            diagnostics=diagnostics,
            timestamp=float(timestamp),
            candidates=tuple(candidates),
        )

