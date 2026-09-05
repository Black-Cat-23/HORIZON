"""
HORIZON Hybrid Perception & Confidence Fusion Engine (Phase 8)
========================================================================
Combines Phase 4 Classical Optical Detector and Phase 7 YOLOv8n Neural Engine
into a unified, explainable, and zero-ground-truth perception layer ("OURS").

Performs:
  1. Concurrent proposal generation (Classical connected components + Neural YOLO proposals)
  2. Spatial overlap (IoU) and subpixel centroid distance candidate matching
  3. Feature consistency scoring (Spatial, Size, Optical Contrast, Temporal Kinematic)
  4. Configurable weight matrix confidence fusion & agreement state classification
  5. Strong disagreement detection & transparent fallback rules
  6. Subpixel optical centroid refinement (Weighted CoG / Gaussian Surface Fit) inside ROI

Strict Invariant: Zero ground-truth leakage or dependencies.
"""

from __future__ import annotations

import logging
import time
from typing import List, Optional, Tuple, Any
import cv2
import numpy as np

from simulator.perception.candidate import BeaconCandidate
from simulator.perception.candidate_matcher import (
    CandidateMatcher,
    MatchState,
    MatchedPair,
    compute_centroid_distance,
    compute_iou,
)
from simulator.perception.centroid import (
    compute_gaussian_fit,
    compute_geometric_centroid,
    compute_weighted_cog,
)
from simulator.perception.config import DetectorConfig, HybridDetectorConfig
from simulator.perception.consistency_features import (
    compute_optical_agreement,
    compute_size_agreement,
    compute_spatial_agreement,
    compute_temporal_agreement,
)
from simulator.perception.detector import ClassicalBeaconDetector, DetectionResult
from simulator.perception.hybrid_candidate import CandidateSource, UnifiedCandidate
from simulator.perception.neural_detector import NeuralBeaconDetector
from simulator.perception.preprocessing import validate_input_frame

logger = logging.getLogger(__name__)


class HybridBeaconDetector:
    """Phase 8 Hybrid Perception Engine combining Classical and Neural detectors.

    Parameters:
        config: DetectorConfig dataclass containing hybrid settings.
    """

    def __init__(self, config: Optional[DetectorConfig] = None) -> None:
        self._config = config or DetectorConfig()
        self._hybrid_cfg: HybridDetectorConfig = self._config.hybrid
        self._fusion_cfg = self._hybrid_cfg.fusion

        self._classical_detector = ClassicalBeaconDetector(self._config)
        self._neural_detector = NeuralBeaconDetector(self._config)

        self._matcher = CandidateMatcher(
            max_centroid_distance_px=self._fusion_cfg.max_matching_distance_px,
            min_iou_threshold=self._fusion_cfg.min_matching_iou,
        )

    @property
    def config(self) -> DetectorConfig:
        return self._config

    @property
    def classical_detector(self) -> ClassicalBeaconDetector:
        return self._classical_detector

    @property
    def neural_detector(self) -> NeuralBeaconDetector:
        return self._neural_detector

    def detect(
        self,
        frame: np.ndarray,
        timestamp: float = 0.0,
        collect_diagnostics: bool = False,
        estimator_prediction: Optional[Tuple[float, float]] = None,
        prediction_covariance: Optional[np.ndarray] = None,
    ) -> DetectionResult:
        """Process optical sensor frame using configured perception mode (CLASSICAL, NEURAL, or HYBRID).

        Args:
            frame: 2D uint8 sensor frame (640×480).
            timestamp: Simulation timestamp in seconds.
            collect_diagnostics: Toggle creation of visual diagnostics.
            estimator_prediction: Optional predicted beacon position from Phase 5 estimator.
            prediction_covariance: Optional (2,2) prediction covariance matrix.

        Returns:
            DetectionResult dataclass with detection status, refined centroid, and telemetry.
        """
        mode = self._config.perception_mode.upper()

        if mode == "CLASSICAL":
            return self._classical_detector.detect(frame, timestamp, collect_diagnostics)
        elif mode == "NEURAL":
            return self._neural_detector.detect(frame, timestamp, collect_diagnostics)
        elif mode != "HYBRID":
            logger.warning("Unknown perception_mode %s; falling back to HYBRID", mode)

        # Mode == "HYBRID"
        return self._detect_hybrid(
            frame, timestamp, collect_diagnostics, estimator_prediction, prediction_covariance
        )

    def _detect_hybrid(
        self,
        frame: np.ndarray,
        timestamp: float,
        collect_diagnostics: bool,
        estimator_prediction: Optional[Tuple[float, float]],
        prediction_covariance: Optional[np.ndarray],
    ) -> DetectionResult:
        t_start = time.perf_counter()

        valid_frame = validate_input_frame(
            frame,
            expected_width=self._config.input_width,
            expected_height=self._config.input_height,
        )

        # 1. Execute Classical and Neural Detectors Concurrently
        res_c = self._classical_detector.detect(valid_frame, timestamp, collect_diagnostics)
        res_n = self._neural_detector.detect(valid_frame, timestamp, collect_diagnostics)

        # 2. Candidate Extraction & Normalization
        classical_candidates = self._extract_classical_unified(res_c)
        neural_candidates = self._extract_neural_unified(res_n)

        # Fallback handling when one or both detectors produce no proposals
        if not classical_candidates and not neural_candidates:
            t_end = time.perf_counter()
            return DetectionResult(
                detected=False,
                centroid=None,
                bbox=None,
                confidence=0.0,
                candidate_count=0,
                method_used="hybrid_fusion",
                processing_time_ms=(t_end - t_start) * 1000.0,
                timestamp=timestamp,
                detector_source="HYBRID",
                centroid_source=self._config.centroid.method.upper(),
                agreement_state="NO_VALID_CANDIDATE",
                fused_confidence=0.0,
                decision_reason="No candidates proposed by Classical or Neural detectors",
            )

        # 3. Candidate Matching
        matched_pairs, un_c, un_n = self._matcher.match_candidates(
            classical_candidates, neural_candidates
        )

        # 4. Feature Scoring & Confidence Fusion across all candidates
        scored_candidates: List[Tuple[float, UnifiedCandidate, str, str]] = []

        # Process Matched Pairs (BOTH)
        for pair in matched_pairs:
            s_spatial = compute_spatial_agreement(pair.centroid_distance)
            s_size = compute_size_agreement(pair.classical.area, pair.neural.area)
            s_optical = compute_optical_agreement(
                pair.classical.local_contrast, pair.classical.background_estimate
            )
            s_temporal = compute_temporal_agreement(
                pair.fused_candidate.centroid, estimator_prediction, prediction_covariance
            )

            c_class = pair.classical.classical_confidence or 0.0
            c_neur = pair.neural.neural_confidence or 0.0

            # Weight formulation: normalized
            w = self._fusion_cfg
            raw_score = (
                w.classical_weight * c_class
                + w.neural_weight * c_neur
                + w.spatial_weight * s_spatial
                + w.size_weight * s_size
                + w.optical_weight * s_optical
                + w.temporal_weight * s_temporal
            )
            total_weight = (
                w.classical_weight
                + w.neural_weight
                + w.spatial_weight
                + w.size_weight
                + w.optical_weight
                + w.temporal_weight
            )
            fused_score = float(np.clip(raw_score / max(total_weight, 1e-5), 0.0, 1.0))

            # Agreement state determination
            if s_spatial > 0.70 and s_size > 0.50:
                agr_state = "AGREEMENT"
            elif s_spatial > 0.40:
                agr_state = "PARTIAL_AGREEMENT"
            else:
                agr_state = "DISAGREEMENT"

            reason = (
                f"Matched Classical+Neural pair (dist={pair.centroid_distance:.2f}px, IoU={pair.iou:.2f})"
            )
            scored_candidates.append((fused_score, pair.fused_candidate, agr_state, reason))

        # Process Classical-Only Candidates
        for cand in un_c:
            c_class = cand.classical_confidence or 0.0
            s_optical = compute_optical_agreement(cand.local_contrast, cand.background_estimate)
            s_temporal = compute_temporal_agreement(
                cand.centroid, estimator_prediction, prediction_covariance
            )

            # Suppress isolated small noise specks lacking neural proposal match or strong contrast
            penalty = 1.0
            if self._neural_detector.is_model_loaded:
                if cand.area < 6.0 or (cand.local_contrast is not None and cand.local_contrast < 35.0):
                    penalty = 0.25

            fused_score = float(
                np.clip((0.60 * c_class + 0.25 * s_optical + 0.15 * s_temporal) * penalty, 0.0, 1.0)
            )
            scored_candidates.append(
                (fused_score, cand, "CLASSICAL_ONLY", "Unmatched Classical optical candidate")
            )

        # Process Neural-Only Candidates
        for cand in un_n:
            c_neur = cand.neural_confidence or 0.0
            s_temporal = compute_temporal_agreement(
                cand.centroid, estimator_prediction, prediction_covariance
            )

            fused_score = float(np.clip(0.70 * c_neur + 0.30 * s_temporal, 0.0, 1.0))
            scored_candidates.append(
                (fused_score, cand, "NEURAL_ONLY", "Unmatched Neural bounding box proposal")
            )

        # Sort scored candidates by fused confidence score descending
        scored_candidates.sort(key=lambda x: x[0], reverse=True)
        top_score, top_candidate, top_agr, top_reason = scored_candidates[0]

        # 5. Acceptance Gate & Fallback Handling
        if top_score < self._fusion_cfg.acceptance_threshold:
            t_end = time.perf_counter()
            return DetectionResult(
                detected=False,
                centroid=None,
                bbox=None,
                confidence=top_score,
                candidate_count=len(scored_candidates),
                method_used="hybrid_fusion",
                processing_time_ms=(t_end - t_start) * 1000.0,
                timestamp=timestamp,
                detector_source="HYBRID",
                centroid_source="NONE",
                agreement_state="REJECTED_LOW_CONFIDENCE",
                fused_confidence=top_score,
                decision_reason=f"Top candidate confidence {top_score:.3f} below acceptance threshold {self._fusion_cfg.acceptance_threshold:.3f}",
            )

        # 6. Optical Subpixel Centroid Refinement on Selected ROI
        final_centroid, centroid_method = self._refine_centroid(
            valid_frame, top_candidate
        )

        t_end = time.perf_counter()
        total_time_ms = (t_end - t_start) * 1000.0

        all_unified = tuple([sc[1] for sc in scored_candidates])

        return DetectionResult(
            detected=True,
            centroid=final_centroid,
            bbox=top_candidate.bbox,
            confidence=top_score,
            candidate_count=len(scored_candidates),
            method_used="hybrid_fusion",
            processing_time_ms=total_time_ms,
            timestamp=timestamp,
            candidates=res_c.candidates,
            detector_source="HYBRID",
            centroid_source=centroid_method,
            agreement_state=top_agr,
            fused_confidence=top_score,
            decision_reason=top_reason,
            unified_candidates=all_unified,
        )

    def _extract_classical_unified(self, res_c: DetectionResult) -> List[UnifiedCandidate]:
        out = []
        if not res_c.detected or not res_c.candidates:
            return out

        for i, cand in enumerate(res_c.candidates):
            # Compute centroid from candidate contour/bbox
            M = cv2.moments(cand.contour)
            if M["m00"] != 0:
                cx = float(M["m10"] / M["m00"])
                cy = float(M["m01"] / M["m00"])
            else:
                cx = float(cand.bbox[0] + cand.bbox[2] / 2.0)
                cy = float(cand.bbox[1] + cand.bbox[3] / 2.0)

            out.append(
                UnifiedCandidate(
                    candidate_id=f"C_{i}",
                    centroid_x=cx,
                    centroid_y=cy,
                    bbox_x=cand.bbox[0],
                    bbox_y=cand.bbox[1],
                    bbox_width=cand.bbox[2],
                    bbox_height=cand.bbox[3],
                    area=cand.area_px,
                    peak_intensity=cand.peak_intensity,
                    mean_intensity=cand.mean_intensity,
                    background_estimate=cand.background_level,
                    local_contrast=cand.peak_intensity - cand.background_level,
                    classical_confidence=cand.score,
                    neural_confidence=None,
                    source=CandidateSource.CLASSICAL,
                    valid=True,
                    raw_classical_candidate=cand,
                    contour=cand.contour,
                )
            )
        return out

    def _extract_neural_unified(self, res_n: DetectionResult) -> List[UnifiedCandidate]:
        out = []
        if not res_n.detected or res_n.centroid is None or res_n.bbox is None:
            return out

        x, y, w, h = res_n.bbox
        cx, cy = res_n.centroid
        out.append(
            UnifiedCandidate(
                candidate_id="N_0",
                centroid_x=cx,
                centroid_y=cy,
                bbox_x=x,
                bbox_y=y,
                bbox_width=w,
                bbox_height=h,
                area=float(w * h),
                peak_intensity=None,
                mean_intensity=None,
                background_estimate=None,
                local_contrast=None,
                classical_confidence=None,
                neural_confidence=res_n.confidence,
                source=CandidateSource.NEURAL,
                valid=True,
                raw_neural_bbox=res_n.bbox,
            )
        )
        return out

    def _refine_centroid(
        self, frame: np.ndarray, candidate: UnifiedCandidate
    ) -> Tuple[Tuple[float, float], str]:
        """Perform optical subpixel centroid refinement on the candidate ROI."""
        if not self._fusion_cfg.enable_optical_centroid_refinement:
            return (candidate.centroid_x, candidate.centroid_y), "GEOMETRIC"

        x, y, w, h = candidate.bbox
        pad = self._config.centroid.roi_padding_px
        h_f, w_f = frame.shape[:2]

        x1 = max(0, x - pad)
        y1 = max(0, y - pad)
        x2 = min(w_f, x + w + pad)
        y2 = min(h_f, y + h + pad)

        roi = frame[y1:y2, x1:x2]
        if roi.size == 0:
            return (candidate.centroid_x, candidate.centroid_y), "GEOMETRIC"

        roi_mask = np.ones(roi.shape, dtype=np.uint8)
        if candidate.contour is not None:
            # Shift contour to ROI coordinates
            cnt_roi = candidate.contour.copy()
            cnt_roi[:, :, 0] -= x1
            cnt_roi[:, :, 1] -= y1
            roi_mask = np.zeros(roi.shape, dtype=np.uint8)
            cv2.drawContours(roi_mask, [cnt_roi], -1, 255, thickness=-1)

        bg_level = candidate.background_estimate or float(np.median(frame))
        method = self._config.centroid.method

        if method == "gaussian_fit":
            u_c, v_c, success = compute_gaussian_fit(
                roi_frame=roi,
                roi_mask=roi_mask,
                bg_level=bg_level,
                x_offset=x1,
                y_offset=y1,
                config=self._config.centroid,
            )
            return (u_c, v_c), "GAUSSIAN_FIT" if success else "WEIGHTED_COG"
        elif method == "weighted_cog":
            u_c, v_c = compute_weighted_cog(
                roi_frame=roi,
                roi_mask=roi_mask,
                bg_level=bg_level,
                x_offset=x1,
                y_offset=y1,
            )
            return (u_c, v_c), "WEIGHTED_COG"
        else:
            u_c, v_c = compute_geometric_centroid(
                roi_mask=roi_mask,
                x_offset=x1,
                y_offset=y1,
            )
            return (u_c, v_c), "GEOMETRIC"
