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
import math
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
    compute_appearance_agreement,
    compute_estimator_consistency,
    compute_optical_agreement,
    compute_size_agreement,
    compute_spatial_agreement,
    compute_temporal_agreement,
)
from simulator.perception.detector import ClassicalBeaconDetector, DetectionQuality, DetectionResult
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
            velocity_scale_factor=getattr(self._fusion_cfg, "velocity_scale_factor", 60.0),
            max_matching_distance_cap=getattr(self._fusion_cfg, "max_matching_distance_cap", 80.0),
        )
        self._frames_since_full_hybrid: int = 0

    def reset_scheduler(self) -> None:
        """Reset the adaptive perception scheduling frame counter."""
        self._frames_since_full_hybrid = 0

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
        velocity_hint_px_s: float = 0.0,
        pat_mode: Optional[str] = None,
        track_quality: float = 0.0,
        consecutive_hits: int = 0,
        roi: Optional[Union[Any, Tuple[int, int, int, int]]] = None,
    ) -> DetectionResult:
        """Process optical sensor frame using configured perception mode (CLASSICAL, NEURAL, or HYBRID).

        Args:
            frame: 2D uint8 sensor frame (640×480).
            timestamp: Simulation timestamp in seconds.
            collect_diagnostics: Toggle creation of visual diagnostics.
            estimator_prediction: Optional predicted beacon position from Phase 5 estimator.
            prediction_covariance: Optional (2,2) prediction covariance matrix.
            velocity_hint_px_s: Optional estimated beacon velocity magnitude (px/s).
            pat_mode: Optional PAT state machine mode (e.g. "TRACK", "SEARCH", "DEGRADED").
            track_quality: Current track quality metric (0.0 to 1.0).
            consecutive_hits: Consecutive measurement hits count.
            roi: Optional DynamicROI or (x1, y1, x2, y2) bounding region of interest.

        Returns:
            DetectionResult dataclass with detection status, refined centroid, and telemetry.
        """
        mode = self._config.perception_mode.upper()

        if mode == "CLASSICAL":
            return self._classical_detector.detect(frame, timestamp, collect_diagnostics, roi=roi)
        elif mode == "NEURAL":
            return self._neural_detector.detect(frame, timestamp, collect_diagnostics, roi=roi)
        elif mode != "HYBRID":
            logger.warning("Unknown perception_mode %s; falling back to HYBRID", mode)

        # Mode == "HYBRID"
        sched_cfg = getattr(self._hybrid_cfg, "scheduling", None)
        if sched_cfg is not None and getattr(sched_cfg, "enabled", False) and pat_mode is not None:
            # 1. Eligibility Check
            needs_full_hybrid = False
            if pat_mode.upper() in [m.upper() for m in sched_cfg.always_full_modes]:
                needs_full_hybrid = True
            elif track_quality < sched_cfg.high_quality_threshold:
                needs_full_hybrid = True
            elif consecutive_hits < sched_cfg.min_stable_hits:
                needs_full_hybrid = True
            elif sched_cfg.recalibration_period_frames <= 1 or self._frames_since_full_hybrid >= sched_cfg.recalibration_period_frames:
                needs_full_hybrid = True

            if needs_full_hybrid:
                self._frames_since_full_hybrid = 0
                return self._detect_hybrid(
                    frame, timestamp, collect_diagnostics, estimator_prediction, prediction_covariance, velocity_hint_px_s, roi=roi
                )

            # 2. Fast Path Attempt (Classical Only)
            t_fast_start = time.perf_counter()
            res_c = self._classical_detector.detect(frame, timestamp, collect_diagnostics, roi=roi)

            # 3. Escalation Evaluation
            escalate = False
            escalation_reason = ""
            if not res_c.detected:
                escalate = True
                escalation_reason = "Classical fast-path found no candidate"
            elif sched_cfg.escalate_on_low_confidence and res_c.confidence < sched_cfg.classical_escalation_confidence:
                escalate = True
                escalation_reason = f"Classical confidence {res_c.confidence:.2f} < {sched_cfg.classical_escalation_confidence:.2f}"
            elif sched_cfg.escalate_on_multiple_candidates and res_c.candidate_count > 1:
                escalate = True
                escalation_reason = f"Multiple candidates ({res_c.candidate_count}) in scene"
            elif estimator_prediction is not None and res_c.centroid is not None:
                is_valid_est, d2_est, _ = compute_estimator_consistency(
                    res_c.centroid, estimator_prediction, prediction_covariance, velocity_hint_px_s=velocity_hint_px_s
                )
                if not is_valid_est:
                    escalate = True
                    escalation_reason = f"Fast-path candidate failed Kalman gate (d2={d2_est:.2f} > 9.21)"

            if escalate:
                self._frames_since_full_hybrid = 0
                res_hybrid = self._detect_hybrid(
                    frame, timestamp, collect_diagnostics, estimator_prediction, prediction_covariance, velocity_hint_px_s, roi=roi
                )
                res_hybrid.decision_reason = f"ESCALATED: {escalation_reason} | {res_hybrid.decision_reason}"
                return res_hybrid

            # Fast path accepted safely
            self._frames_since_full_hybrid += 1
            t_fast_end = time.perf_counter()
            res_c.processing_time_ms = (t_fast_end - t_fast_start) * 1000.0
            res_c.method_used = "classical_fast_path"
            res_c.detector_source = "HYBRID_FAST_PATH"
            res_c.agreement_state = "FAST_PATH_NOMINAL"
            res_c.fused_confidence = res_c.confidence
            res_c.decision_reason = f"Fast-path nominal track ({consecutive_hits} hits, quality={track_quality:.2f})"
            return res_c

        return self._detect_hybrid(
            frame, timestamp, collect_diagnostics, estimator_prediction, prediction_covariance, velocity_hint_px_s, roi=roi
        )

    def _detect_hybrid(
        self,
        frame: np.ndarray,
        timestamp: float,
        collect_diagnostics: bool,
        estimator_prediction: Optional[Tuple[float, float]],
        prediction_covariance: Optional[np.ndarray],
        velocity_hint_px_s: float = 0.0,
        roi: Optional[Union[Any, Tuple[int, int, int, int]]] = None,
    ) -> DetectionResult:
        t_start = time.perf_counter()

        valid_frame = validate_input_frame(
            frame,
            expected_width=self._config.input_width,
            expected_height=self._config.input_height,
        )

        # Determine ROI bbox and usage (Phase 6B)
        is_roi = False
        roi_bbox = None
        if roi is not None:
            if hasattr(roi, "x1") and hasattr(roi, "x2"):
                is_roi = not getattr(roi, "is_full_frame", False)
                roi_bbox = (int(roi.x1), int(roi.y1), int(roi.width), int(roi.height)) if is_roi else None
            elif isinstance(roi, (tuple, list)) and len(roi) == 4:
                rx1, ry1, rx2, ry2 = int(roi[0]), int(roi[1]), int(roi[2]), int(roi[3])
                if rx2 <= rx1:
                    rx2, ry2 = rx1 + int(roi[2]), ry1 + int(roi[3])
                is_roi = not (rx1 <= 0 and ry1 <= 0 and rx2 >= self._config.input_width and ry2 >= self._config.input_height)
                roi_bbox = (rx1, ry1, rx2 - rx1, ry2 - ry1) if is_roi else None

        # 1. Execute Classical and Neural Detectors Concurrently (within ROI if specified)
        res_c = self._classical_detector.detect(
            valid_frame,
            timestamp,
            collect_diagnostics,
            roi=roi,
            estimator_prediction=estimator_prediction,
            prediction_covariance=prediction_covariance,
        )
        res_n = self._neural_detector.detect(
            valid_frame,
            timestamp,
            collect_diagnostics,
            roi=roi,
            estimator_prediction=estimator_prediction,
        )

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
                roi_bbox=roi_bbox,
                is_roi_used=is_roi,
            )

        # 3. Candidate Matching with dynamic velocity gating
        matched_pairs, un_c, un_n = self._matcher.match_candidates(
            classical_candidates, neural_candidates, velocity_hint_px_s=velocity_hint_px_s
        )

        # 4. Feature Scoring & Confidence Fusion across all candidates
        scored_candidates: List[Tuple[float, UnifiedCandidate, str, str]] = []

        # Process Matched Pairs (BOTH)
        for pair in matched_pairs:
            s_spatial = compute_spatial_agreement(
                pair.centroid_distance,
                velocity_hint_px_s=velocity_hint_px_s,
            )
            s_size = compute_size_agreement(pair.classical.area, pair.neural.area)
            s_optical = compute_optical_agreement(
                pair.classical.local_contrast, pair.classical.background_estimate
            )
            s_appearance = compute_appearance_agreement(pair.fused_candidate)
            s_temporal = compute_temporal_agreement(
                pair.fused_candidate.centroid, estimator_prediction, prediction_covariance
            )
            is_valid_est, d2_est, s_est = compute_estimator_consistency(
                pair.fused_candidate.centroid, estimator_prediction, prediction_covariance, velocity_hint_px_s=velocity_hint_px_s
            )

            c_class = pair.classical.classical_confidence or 0.0
            c_neur = pair.neural.neural_confidence or 0.0
            det_conf = float(0.5 * (c_class + c_neur))

            # Dynamic weight formulation (LE-01 & HC-02)
            w = self._fusion_cfg
            neural_w = w.neural_weight if self._neural_detector.is_model_loaded else 0.0
            temporal_w = w.temporal_weight if estimator_prediction is not None else 0.0

            raw_score = (
                w.classical_weight * c_class
                + neural_w * c_neur
                + w.spatial_weight * s_spatial
                + w.size_weight * s_size
                + w.optical_weight * s_optical
                + temporal_w * s_temporal
            )
            total_weight = (
                w.classical_weight
                + neural_w
                + w.spatial_weight
                + w.size_weight
                + w.optical_weight
                + temporal_w
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
                f"Candidate selected because matched Classical+Neural agreement (dist={pair.centroid_distance:.2f}px, "
                f"IoU={pair.iou:.2f}, spatial={s_spatial:.2f}, optical={s_optical:.2f}, temporal={s_temporal:.2f}) "
                f"strongly supports beacon hypothesis"
            )

            enriched_cand = UnifiedCandidate(
                candidate_id=pair.fused_candidate.candidate_id,
                centroid_x=pair.fused_candidate.centroid_x,
                centroid_y=pair.fused_candidate.centroid_y,
                bbox_x=pair.fused_candidate.bbox_x,
                bbox_y=pair.fused_candidate.bbox_y,
                bbox_width=pair.fused_candidate.bbox_width,
                bbox_height=pair.fused_candidate.bbox_height,
                area=pair.fused_candidate.area,
                peak_intensity=pair.fused_candidate.peak_intensity,
                mean_intensity=pair.fused_candidate.mean_intensity,
                background_estimate=pair.fused_candidate.background_estimate,
                local_contrast=pair.fused_candidate.local_contrast,
                classical_confidence=pair.fused_candidate.classical_confidence,
                neural_confidence=pair.fused_candidate.neural_confidence,
                source=pair.fused_candidate.source,
                valid=pair.fused_candidate.valid and is_valid_est,
                raw_classical_candidate=pair.fused_candidate.raw_classical_candidate,
                raw_neural_bbox=pair.fused_candidate.raw_neural_bbox,
                contour=pair.fused_candidate.contour,
                spatial_evidence=s_spatial,
                optical_evidence=s_optical,
                temporal_evidence=s_temporal,
                appearance_evidence=s_appearance,
                detector_confidence=det_conf,
                estimator_consistency=s_est,
                decision_reason=reason,
                rejection_reason="",
            )
            scored_candidates.append((fused_score, enriched_cand, agr_state, reason))

        # Process Classical-Only Candidates
        for cand in un_c:
            c_class = cand.classical_confidence or 0.0
            s_optical = compute_optical_agreement(cand.local_contrast, cand.background_estimate)
            s_appearance = compute_appearance_agreement(cand)
            s_temporal = compute_temporal_agreement(
                cand.centroid, estimator_prediction, prediction_covariance
            )
            is_valid_est, d2_est, s_est = compute_estimator_consistency(
                cand.centroid, estimator_prediction, prediction_covariance, velocity_hint_px_s=velocity_hint_px_s
            )

            # Adaptive Optical-Neural Verification:
            # Physically genuine optical emitters (high contrast/SNR) must not be suppressed
            # merely because YOLOv8 missed them. Scale penalty smoothly based on optical evidence.
            if not self._neural_detector.is_model_loaded:
                penalty = 1.0
            else:
                contrast_ev = min(cand.local_contrast / 3.5, 1.0)
                snr_ev = min(max(cand.peak_intensity - cand.background_estimate, 0.0) / 18.0, 1.0)
                optical_strength = max(contrast_ev, snr_ev)
                temporal_strength = s_temporal if estimator_prediction is not None else 0.5
                # Modulate penalty by appearance agreement so irregular glints / noise clusters are penalized
                appearance_strength = s_appearance
                penalty = float(np.clip((0.30 + 0.35 * optical_strength + 0.20 * temporal_strength) * appearance_strength, 0.15, 1.0))

            if estimator_prediction is not None:
                base_score = (
                    0.35 * c_class
                    + 0.25 * s_optical
                    + 0.25 * s_appearance
                    + 0.15 * s_temporal
                )
            else:
                d_center = math.hypot(cand.centroid_x - 320.0, cand.centroid_y - 240.0)
                s_boresight = math.exp(-0.5 * (d_center / 150.0) ** 2)
                base_score = (
                    0.35 * c_class
                    + 0.25 * s_optical
                    + 0.20 * s_appearance
                    + 0.20 * s_boresight
                )
            fused_score = float(np.clip(base_score * penalty, 0.0, 1.0))
            reason = (
                f"Candidate selected via classical optical detection (contrast={cand.local_contrast:.1f}, "
                f"confidence={c_class:.2f}, temporal={s_temporal:.2f})"
            )
            rej_reason = (
                f"Unmatched classical optical candidate score below threshold (penalty={penalty:.2f})"
                if penalty < 1.0 else "Classical candidate score below threshold"
            )

            enriched_cand = UnifiedCandidate(
                candidate_id=cand.candidate_id,
                centroid_x=cand.centroid_x,
                centroid_y=cand.centroid_y,
                bbox_x=cand.bbox_x,
                bbox_y=cand.bbox_y,
                bbox_width=cand.bbox_width,
                bbox_height=cand.bbox_height,
                area=cand.area,
                peak_intensity=cand.peak_intensity,
                mean_intensity=cand.mean_intensity,
                background_estimate=cand.background_estimate,
                local_contrast=cand.local_contrast,
                classical_confidence=cand.classical_confidence,
                neural_confidence=None,
                source=CandidateSource.CLASSICAL,
                valid=cand.valid and is_valid_est,
                raw_classical_candidate=cand.raw_classical_candidate,
                raw_neural_bbox=None,
                contour=cand.contour,
                spatial_evidence=0.0,
                optical_evidence=s_optical,
                temporal_evidence=s_temporal,
                appearance_evidence=s_appearance,
                detector_confidence=c_class,
                estimator_consistency=s_est,
                decision_reason=reason,
                rejection_reason=rej_reason,
            )
            scored_candidates.append(
                (fused_score, enriched_cand, "SINGLE_SOURCE_CLASSICAL", reason)
            )

        # Process Neural-Only Candidates
        for cand in un_n:
            c_neur = cand.neural_confidence or 0.0
            s_appearance = compute_appearance_agreement(cand)
            s_temporal = compute_temporal_agreement(
                cand.centroid, estimator_prediction, prediction_covariance
            )
            is_valid_est, d2_est, s_est = compute_estimator_consistency(
                cand.centroid, estimator_prediction, prediction_covariance, velocity_hint_px_s=velocity_hint_px_s
            )

            if estimator_prediction is not None:
                fused_score = float(np.clip((0.50 * c_neur + 0.50 * s_temporal) * s_est, 0.0, 1.0))
            else:
                fused_score = float(np.clip(c_neur * (0.50 + 0.50 * s_appearance), 0.0, 1.0))

            reason = (
                f"Candidate selected via neural bounding box detection (confidence={c_neur:.2f}, "
                f"temporal={s_temporal:.2f})"
            )
            rej_reason = "Unmatched neural proposal below threshold"

            enriched_cand = UnifiedCandidate(
                candidate_id=cand.candidate_id,
                centroid_x=cand.centroid_x,
                centroid_y=cand.centroid_y,
                bbox_x=cand.bbox_x,
                bbox_y=cand.bbox_y,
                bbox_width=cand.bbox_width,
                bbox_height=cand.bbox_height,
                area=cand.area,
                peak_intensity=None,
                mean_intensity=None,
                background_estimate=None,
                local_contrast=None,
                classical_confidence=None,
                neural_confidence=cand.neural_confidence,
                source=CandidateSource.NEURAL,
                valid=cand.valid and is_valid_est,
                raw_classical_candidate=None,
                raw_neural_bbox=cand.raw_neural_bbox,
                contour=None,
                spatial_evidence=0.0,
                optical_evidence=0.5,
                temporal_evidence=s_temporal,
                appearance_evidence=s_appearance,
                detector_confidence=c_neur,
                estimator_consistency=s_est,
                decision_reason=reason,
                rejection_reason=rej_reason,
            )
            scored_candidates.append(
                (fused_score, enriched_cand, "SINGLE_SOURCE_NEURAL", reason)
            )

        # Sort scored candidates: valid candidates (passing estimator gate) first, then by fused confidence descending
        scored_candidates.sort(key=lambda x: (x[1].valid, x[0]), reverse=True)
        top_score, top_candidate, top_agr, top_reason = scored_candidates[0]

        # 5. Acceptance Gate & Fallback Handling (Championship Rule)
        # Dual-source matched candidates (BOTH) carry semantic verification and can tolerate temporary estimator lag.
        # Single-source candidates (CLASSICAL only) MUST strictly satisfy the estimator Mahalanobis gate when tracking.
        cand_optical_strong = (
            top_candidate.detector_confidence is not None and top_candidate.detector_confidence >= 0.55
        )
        if estimator_prediction is not None:
            if top_candidate.source == CandidateSource.BOTH:
                is_candidate_valid = top_candidate.valid or cand_optical_strong
            else:
                # Single-source (Classical-only or Neural-only) MUST strictly satisfy estimator gate
                is_candidate_valid = top_candidate.valid
        else:
            # Cold search acquisition without prior tracking: allow strong emitter
            is_candidate_valid = top_candidate.valid or cand_optical_strong

        is_accepted = (top_score >= self._fusion_cfg.acceptance_threshold) and is_candidate_valid
        partial_thresh = getattr(self._fusion_cfg, "partial_confidence_threshold", 0.20)
        is_partial = (
            not is_accepted
            and top_candidate.source == CandidateSource.BOTH
            and top_score >= partial_thresh
            and is_candidate_valid
        )

        if not is_accepted and not is_partial:
            t_end = time.perf_counter()
            agr_state = "REJECTED_ESTIMATOR_GATE" if not is_candidate_valid else "REJECTED_LOW_CONFIDENCE"
            rej_reason = (
                f"Candidate rejected because Mahalanobis gate failed under tracking (valid={top_candidate.valid})"
                if not is_candidate_valid
                else f"Candidate rejected because top confidence {top_score:.3f} below acceptance threshold {self._fusion_cfg.acceptance_threshold:.3f}"
            )
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
                agreement_state=agr_state,
                fused_confidence=top_score,
                decision_reason=rej_reason,
            )

        if is_partial:
            top_agr = "PARTIAL_CONFIDENCE"
            top_reason = (
                f"{top_reason} [Partial confidence acceptance: dual-source match confirmed under high disturbance]"
            )

        # 6. Optical Subpixel Centroid Refinement on Selected ROI
        final_centroid, centroid_method = self._refine_centroid(
            valid_frame, top_candidate
        )

        # 7. Physical Centroid Uncertainty & Candidate Quality Derivation
        cand_c = getattr(top_candidate, "raw_classical_candidate", None)
        if cand_c is not None:
            base_sigma_u = float(cand_c.sigma_u_px)
            base_sigma_v = float(cand_c.sigma_v_px)
            is_clipped = bool(cand_c.clipped_by_edge)
        else:
            area = float(top_candidate.area)
            snr = float(10.0 * (top_candidate.neural_confidence or 0.5))
            fwhm = max(1.0, math.sqrt(area))
            sig = fwhm / (2.355 * max(snr, 0.1) * math.sqrt(max(area, 1.0)))
            base_sigma_u = float(sig)
            base_sigma_v = float(sig)
            is_clipped = False

        # If detectors disagree on position, add spatial disagreement in quadrature
        discrepancy_px = 0.0
        if top_agr == "DISAGREEMENT":
            discrepancy_px = 1.5

        sigma_u = math.sqrt(base_sigma_u ** 2 + discrepancy_px ** 2)
        sigma_v = math.sqrt(base_sigma_v ** 2 + discrepancy_px ** 2)

        # Edge clipping doubles uncertainty due to partial boundary occlusion
        if is_clipped:
            sigma_u *= 2.0
            sigma_v *= 2.0

        sigma_u = float(np.clip(sigma_u, 0.01, 5.0))
        sigma_v = float(np.clip(sigma_v, 0.01, 5.0))

        quality = DetectionQuality(
            snr=float(cand_c.snr) if cand_c else float(10.0 * (top_candidate.neural_confidence or 0.5)),
            circularity=float(cand_c.circularity) if cand_c else 0.85,
            compactness=float(cand_c.compactness) if cand_c else 0.85,
            symmetry=float(cand_c.symmetry) if cand_c else 0.85,
            radial_consistency=float(cand_c.radial_consistency) if cand_c else 0.85,
            size_plausibility=float(cand_c.size_plausibility) if cand_c else 0.85,
            local_contrast=float(cand_c.local_contrast) if cand_c else float(top_candidate.local_contrast or 50.0),
            bg_mean=float(cand_c.background_level) if cand_c else float(top_candidate.background_estimate or 20.0),
            bg_variance=float(cand_c.bg_variance) if cand_c else 4.0,
            integrated_flux=float(cand_c.integrated_flux) if cand_c else float(top_candidate.area * 50.0),
            clipped_by_edge=is_clipped,
            scale_class_px=int(getattr(cand_c, "scale_class", 10)) if cand_c else 10,
            candidate_count=len(scored_candidates),
            centroid_method=centroid_method,
            gaussian_fit_succeeded=(centroid_method == "gaussian_fit"),
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
            sigma_u_px=sigma_u,
            sigma_v_px=sigma_v,
            quality=quality,
            roi_bbox=roi_bbox,
            is_roi_used=is_roi,
        )

    def _extract_classical_unified(self, res_c: DetectionResult) -> List[UnifiedCandidate]:
        out = []
        if not res_c.candidates:
            return out

        for i, cand in enumerate(res_c.candidates):
            contrast = cand.peak_intensity - cand.background_level
            min_contrast = float(getattr(self._fusion_cfg, "min_contrast_floor_adu", 12.0))
            min_snr = float(getattr(self._fusion_cfg, "min_snr_floor", 1.2))
            if contrast < min_contrast or cand.snr < min_snr:
                continue

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
                    local_contrast=contrast,
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

        # Use classical candidate bbox if available for optical subpixel centering (LE-08)
        if candidate.raw_classical_candidate is not None:
            x, y, w, h = candidate.raw_classical_candidate.bbox
        else:
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
            if roi_mask.sum() == 0:
                roi_mask = np.ones(roi.shape, dtype=np.uint8)

        bg_level = candidate.background_estimate or float(np.median(frame))
        method = self._config.centroid.method

        if method == "gaussian_fit":
            u_c, v_c, _, _, success = compute_gaussian_fit(
                roi_frame=roi,
                roi_mask=roi_mask,
                bg_level=bg_level,
                x_offset=x1,
                y_offset=y1,
                config=self._config.centroid,
            )
            return (u_c, v_c), "GAUSSIAN_FIT" if success else "WEIGHTED_COG"
        elif method == "weighted_cog":
            u_c, v_c, _, _ = compute_weighted_cog(
                roi_frame=roi,
                roi_mask=roi_mask,
                bg_level=bg_level,
                x_offset=x1,
                y_offset=y1,
            )
            return (u_c, v_c), "WEIGHTED_COG"
        else:
            u_c, v_c, _, _ = compute_geometric_centroid(
                roi_mask=roi_mask,
                x_offset=x1,
                y_offset=y1,
            )
            return (u_c, v_c), "GEOMETRIC"
