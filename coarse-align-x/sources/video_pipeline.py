"""
HORIZON Phase 5B: Measurement Quality & Uncertainty Video Pipeline
========================================================================
Connects ExternalVideoSource to the EXISTING HybridBeaconDetector without
modifying HYBRID mathematics or adding another perception engine.

Exposes complete measurement information:
  - centroid
  - confidence
  - candidate quality
  - candidate geometry
  - classical confidence
  - neural confidence
  - detector agreement
  - validity
  - uncertainty derived strictly from physical quantities (no fabrication)
  - innovation when estimator is engaged
  - temporal jump classification (handoff, ambiguity, noise, edge, true motion)

Strict Invariants:
  - Uses the EXACT existing HybridBeaconDetector.
  - Zero modifications to classical, neural, fusion, or centroiding math.
  - Zero new perception engines (no VideoDetector, MP4Detector, NoiseDetector).
  - Common Frame strictly validated by validate_input_frame().
  - Authoritative timebase from VideoTimebase / FramePacket.
  - Uncertainty derived purely from photon statistics and spatial discrepancy.
"""

from __future__ import annotations

from dataclasses import dataclass
import logging
from pathlib import Path
import time
from typing import Any, Dict, List, Optional, Tuple, Union
import numpy as np

from pat.mode_manager import PATModeManager
from pat.state import PATMode, PATState
from control.camera_controller import PATCameraController
from simulator.perception.config import DetectorConfig
from simulator.perception.detector import DetectionQuality, DetectionResult
from simulator.perception.hybrid_detector import HybridBeaconDetector
from simulator.perception.preprocessing import validate_input_frame
from sources.csv_aligner import GroundTruthCSVAligner, GroundTruthSample
from sources.dynamic_roi import DynamicROI, DynamicROIManager
from sources.error_budget import (
    ComponentStatistics,
    ComponentStatus,
    ErrorBudgetAnalyzer,
    ErrorBudgetSummary,
    ErrorComponentValue,
    FrameErrorBudget,
)
from sources.external_video_source import ExternalVideoSource
from sources.frame_packet import FramePacket
from sources.failure_forensics import FailureEvent, FailureForensicsEngine, ForensicWindow
from sources.latency_profiler import EndToEndLatencyReport, FrameLatencyRecord, LatencyProfiler
from sources.temporal_consistency import JumpCause, TemporalConsistencyAnalyzer
from tracking.association.track import Track
from tracking.estimation.imm_kalman import InteractingMultipleModelFilter
from tracking.estimation.kalman import TargetKalmanFilter
from tracking.estimation.state import EstimatorStatus, StateEstimate

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PipelineMeasurementRecord:
    """Telemetry record for a single frame measurement produced by Existing HYBRID.

    Exposes:
        frame_id: Sequential source video frame index
        timestamp: Authoritative video presentation timestamp (seconds)
        dt: Authoritative source timestep (seconds)
        centroid: Subpixel centroid (u_proc, v_proc) in 640x480 Common Frame space
        centroid_original: Subpixel centroid (u_orig, v_orig) mapped back to original MP4 space
        confidence: Fused detection confidence [0.0, 1.0] from existing HYBRID
        detected: Whether target was detected
        bounding_box: Bounding box (x, y, w, h) in Common Frame space
        source: Fusion decision source ("CLASSICAL_ONLY", "NEURAL_ONLY", "FUSED", etc.)
        agreement_state: Spatial/temporal candidate agreement state
        decode_latency_ms: Video frame decode duration in ms
        processing_latency_ms: End-to-end perception processing duration in ms
        is_dropped: Whether this frame was flagged as dropped or discontinuous
        candidate_quality: Decomposed optical quality metrics (SNR, contrast, flux, etc.)
        candidate_geometry: Geometric properties (area, aspect, scale, clipping)
        classical_confidence: Raw confidence from classical optical detector [0.0, 1.0]
        neural_confidence: Raw confidence from neural YOLOv8n detector [0.0, 1.0]
        detector_agreement: Discrepancy details between classical and neural paths
        validity: Boolean flag indicating if observation passed all optical gates
        uncertainty: 1-sigma centroid observation uncertainty (sigma_u, sigma_v) in pixels
        innovation: Estimator innovation residual (y_u, y_v) in pixels if estimator engaged
        innovation_mahalanobis: Normalized Mahalanobis distance of innovation
        jump_classification: Root cause if a measurement jump occurred (JumpCause)
        roi_bbox: Bounding box (x, y, w, h) of dynamic ROI if engaged
        is_roi_used: True if dynamic ROI was engaged
        estimated_state: Filtered position (x, y) in Common Frame pixels
        estimated_velocity: Filtered velocity (vx, vy) in px/s
        covariance: 4x4 state covariance matrix
        model_probabilities: (P_CV, P_CA, P_MANEUVER) IMM mode probabilities
        pat_mode: Current PAT operating mode string (e.g. "TRACK", "DEGRADED", "REACQUIRE")
        pat_state: Complete serialized PATState container
        pan_error_deg: Line-of-sight pan error in degrees
        tilt_error_deg: Line-of-sight tilt error in degrees
        commanded_pan_rate: Controller coarse pointing pan rate command in deg/s
        commanded_tilt_rate: Controller coarse pointing tilt rate command in deg/s
        is_saturated: Boolean flag indicating if commanded rate hit saturation limits
    """

    frame_id: int
    timestamp: float
    dt: float
    centroid: Optional[Tuple[float, float]]
    centroid_original: Optional[Tuple[float, float]]
    confidence: float
    detected: bool
    bounding_box: Optional[Tuple[float, float, float, float]]
    source: Optional[str]
    agreement_state: Optional[str]
    decode_latency_ms: float
    processing_latency_ms: float
    is_dropped: bool = False
    candidate_quality: Optional[Dict[str, Any]] = None
    candidate_geometry: Optional[Dict[str, Any]] = None
    classical_confidence: Optional[float] = None
    neural_confidence: Optional[float] = None
    detector_agreement: Optional[Dict[str, Any]] = None
    validity: bool = True
    uncertainty: Optional[Tuple[float, float]] = None
    innovation: Optional[Tuple[float, float]] = None
    innovation_mahalanobis: Optional[float] = None
    jump_classification: Optional[str] = None
    roi_bbox: Optional[Tuple[int, int, int, int]] = None
    is_roi_used: bool = False
    estimated_state: Optional[Tuple[float, float]] = None
    estimated_velocity: Optional[Tuple[float, float]] = None
    covariance: Optional[np.ndarray] = None
    model_probabilities: Optional[Tuple[float, float, float]] = None
    pat_mode: Optional[str] = None
    pat_state: Optional[Dict[str, Any]] = None
    pan_error_deg: float = 0.0
    tilt_error_deg: float = 0.0
    commanded_pan_rate: float = 0.0
    commanded_tilt_rate: float = 0.0
    is_saturated: bool = False
    latency_record: Optional[FrameLatencyRecord] = None
    latency_breakdown_ms: Optional[Dict[str, float]] = None
    forensic_event: Optional[FailureEvent] = None
    """Phase 10B: populated when this frame constitutes a tracking failure event."""
    error_budget: Optional[FrameErrorBudget] = None
    """Phase 11B: populated when reference ground truth coordinates are available."""

    def to_dict(self) -> Dict[str, Any]:
        """Convert measurement record to serializable dictionary."""
        return {
            "frame_id": self.frame_id,
            "timestamp": round(self.timestamp, 6),
            "dt": round(self.dt, 6),
            "centroid": (
                (round(self.centroid[0], 4), round(self.centroid[1], 4))
                if self.centroid is not None
                else None
            ),
            "centroid_original": (
                (round(self.centroid_original[0], 4), round(self.centroid_original[1], 4))
                if self.centroid_original is not None
                else None
            ),
            "confidence": round(self.confidence, 4),
            "detected": self.detected,
            "bounding_box": (
                (
                    round(self.bounding_box[0], 2),
                    round(self.bounding_box[1], 2),
                    round(self.bounding_box[2], 2),
                    round(self.bounding_box[3], 2),
                )
                if self.bounding_box is not None
                else None
            ),
            "source": self.source,
            "agreement_state": self.agreement_state,
            "decode_latency_ms": round(self.decode_latency_ms, 3),
            "processing_latency_ms": round(self.processing_latency_ms, 3),
            "is_dropped": self.is_dropped,
            "candidate_quality": self.candidate_quality,
            "candidate_geometry": self.candidate_geometry,
            "classical_confidence": (
                round(self.classical_confidence, 4)
                if self.classical_confidence is not None
                else None
            ),
            "neural_confidence": (
                round(self.neural_confidence, 4)
                if self.neural_confidence is not None
                else None
            ),
            "detector_agreement": self.detector_agreement,
            "validity": self.validity,
            "uncertainty": (
                (round(self.uncertainty[0], 4), round(self.uncertainty[1], 4))
                if self.uncertainty is not None
                else None
            ),
            "innovation": (
                (round(self.innovation[0], 4), round(self.innovation[1], 4))
                if self.innovation is not None
                else None
            ),
            "innovation_mahalanobis": (
                round(self.innovation_mahalanobis, 4)
                if self.innovation_mahalanobis is not None
                else None
            ),
            "jump_classification": self.jump_classification,
            "roi_bbox": self.roi_bbox,
            "is_roi_used": self.is_roi_used,
            "estimated_state": (
                (round(self.estimated_state[0], 4), round(self.estimated_state[1], 4))
                if self.estimated_state is not None
                else None
            ),
            "estimated_velocity": (
                (round(self.estimated_velocity[0], 4), round(self.estimated_velocity[1], 4))
                if self.estimated_velocity is not None
                else None
            ),
            "covariance": (
                self.covariance.tolist()
                if self.covariance is not None
                else None
            ),
            "model_probabilities": (
                (
                    round(self.model_probabilities[0], 4),
                    round(self.model_probabilities[1], 4),
                    round(self.model_probabilities[2], 4),
                )
                if self.model_probabilities is not None
                else None
            ),
            "pat_mode": self.pat_mode,
            "pat_state": self.pat_state,
            "pan_error_deg": round(self.pan_error_deg, 4),
            "tilt_error_deg": round(self.tilt_error_deg, 4),
            "commanded_pan_rate": round(self.commanded_pan_rate, 4),
            "commanded_tilt_rate": round(self.commanded_tilt_rate, 4),
            "is_saturated": self.is_saturated,
            "latency_breakdown_ms": self.latency_breakdown_ms,
            "latency_record": self.latency_record.to_dict() if self.latency_record is not None else None,
            "forensic_event": self.forensic_event.to_dict() if self.forensic_event is not None else None,
            "error_budget": self.error_budget.to_dict() if self.error_budget is not None else None,
        }


class ExternalHybridPipeline:
    """Connects ExternalVideoSource to the EXISTING HybridBeaconDetector.

    Coordinates the ingestion of external MP4 frames, converts them into
    the standardized Common Frame representation (640x480, uint8), feeds
    them into the existing HYBRID perception engine, and captures rich,
    trustworthy measurements with physical uncertainty and jump diagnostics.
    """

    def __init__(
        self,
        video_source: Union[ExternalVideoSource, str, Path],
        detector: Optional[HybridBeaconDetector] = None,
        detector_config: Optional[DetectorConfig] = None,
        estimator: Optional[Union[TargetKalmanFilter, InteractingMultipleModelFilter]] = None,
        enable_estimator: bool = True,
        enable_dynamic_roi: bool = True,
        track: Optional[Track] = None,
        pat_manager: Optional[PATModeManager] = None,
        controller: Optional[PATCameraController] = None,
        ground_truth: Optional[Union[GroundTruthCSVAligner, str, Path]] = None,
        sensor_fov_deg: float = 4.0,
        sensor_width_px: int = 640,
    ) -> None:
        """Initialize the External MP4 -> HYBRID -> IMM-EKF -> PAT -> Controller pipeline.

        Args:
            video_source: Either an open ExternalVideoSource instance or a path to MP4.
            detector: Existing HybridBeaconDetector instance (if None, creates standard instance).
            detector_config: Optional DetectorConfig (ignored if detector instance is provided).
            estimator: Optional estimator (IMM-EKF or TargetKalmanFilter) to calculate innovations.
            enable_estimator: If True, engages IMM-EKF tracking to compute state estimates.
            enable_dynamic_roi: If True, derives dynamic ROI from estimator prediction (Phase 6B).
            track: Optional Track instance encapsulating data association and IMM-EKF.
            pat_manager: Optional PATModeManager instance controlling PAT state progression.
            controller: Optional existing PATCameraController for shadow pointing rate commands.
            ground_truth: Optional GroundTruthCSVAligner or path to ground-truth CSV file (Phase 11B).
            sensor_fov_deg: Camera field of view in degrees (default 4.0 deg).
            sensor_width_px: Camera sensor horizontal pixel count (default 640 px).
        """
        if isinstance(video_source, (str, Path)):
            self._source = ExternalVideoSource(video_source)
            self._owns_source = True
        elif isinstance(video_source, ExternalVideoSource):
            self._source = video_source
            self._owns_source = False
        else:
            raise TypeError(
                f"video_source must be an ExternalVideoSource, str, or Path, got {type(video_source).__name__}"
            )

        # Existing HYBRID is the ONLY perception engine
        if detector is not None:
            if not isinstance(detector, HybridBeaconDetector):
                raise TypeError(
                    f"detector must be an instance of HybridBeaconDetector, got {type(detector).__name__}"
                )
            self._detector = detector
        else:
            cfg = detector_config or DetectorConfig(perception_mode="HYBRID")
            self._detector = HybridBeaconDetector(cfg)

        # Existing Estimator (IMM-EKF) & Data Association (Phase 7B)
        self._enable_estimator = enable_estimator
        self._track: Optional[Track] = None
        self._pat_manager: Optional[PATModeManager] = None

        if self._enable_estimator:
            if track is not None:
                self._track = track
            elif estimator is not None:
                if isinstance(estimator, InteractingMultipleModelFilter):
                    self._track = Track(filter_type="IMM_ADAPTIVE_EKF")
                    self._track._filter = estimator
                else:
                    self._track = Track(kalman_config=getattr(estimator, "_config", None), filter_type="KALMAN")
                    self._track._filter = estimator
            else:
                self._track = Track(filter_type="IMM_ADAPTIVE_EKF")

            self._pat_manager = pat_manager or PATModeManager()

        # Existing Controller (PATCameraController) (Phase 8B Shadow Pointing)
        # Uses exact existing controller with default gain scheduling; zero video-specific tuning
        self._controller: Optional[PATCameraController] = controller or PATCameraController()

        # Dynamic ROI Management (Phase 6B)
        self._enable_dynamic_roi = enable_dynamic_roi
        self._roi_manager = DynamicROIManager()
        self._last_detected_geometry: Tuple[float, float] = (15.0, 15.0)

        # Temporal Consistency Analyzer
        self._temporal_analyzer = TemporalConsistencyAnalyzer()

        # Phase 9B End-to-End Direct Latency Profiler
        self._latency_profiler = LatencyProfiler()

        # Phase 10B Frame-Level Failure Forensics Engine
        self._forensics = FailureForensicsEngine()

        # Phase 11B Tracking Error-Budget Analysis
        if isinstance(ground_truth, (str, Path)):
            self._gt_aligner: Optional[GroundTruthCSVAligner] = GroundTruthCSVAligner(ground_truth)
        elif isinstance(ground_truth, GroundTruthCSVAligner):
            self._gt_aligner = ground_truth
        else:
            self._gt_aligner = None

        self._error_budget_analyzer = ErrorBudgetAnalyzer(
            sensor_fov_deg=sensor_fov_deg,
            sensor_width_px=sensor_width_px,
        )

        self._records: List[PipelineMeasurementRecord] = []

    @property
    def enable_dynamic_roi(self) -> bool:
        """Whether dynamic ROI processing is enabled."""
        return self._enable_dynamic_roi

    @enable_dynamic_roi.setter
    def enable_dynamic_roi(self, value: bool) -> None:
        self._enable_dynamic_roi = bool(value)

    @property
    def roi_manager(self) -> DynamicROIManager:
        """Dynamic ROI manager instance."""
        return self._roi_manager

    @property
    def source(self) -> ExternalVideoSource:
        """The underlying external video source."""
        return self._source

    @property
    def detector(self) -> HybridBeaconDetector:
        """The existing HYBRID perception engine."""
        return self._detector

    @property
    def track(self) -> Optional[Track]:
        """The existing target track lifecycle manager."""
        return self._track

    @property
    def estimator(self) -> Optional[Union[TargetKalmanFilter, InteractingMultipleModelFilter]]:
        """The state estimator (IMM-EKF or Kalman) underlying the track."""
        return self._track.filter if self._track is not None else None

    @property
    def pat_manager(self) -> Optional[PATModeManager]:
        """The existing PAT Mode Manager."""
        return self._pat_manager

    @property
    def controller(self) -> Optional[PATCameraController]:
        """The existing PAT camera controller for shadow pointing."""
        return self._controller

    @property
    def temporal_analyzer(self) -> TemporalConsistencyAnalyzer:
        """The temporal consistency jump analyzer."""
        return self._temporal_analyzer

    @property
    def latency_profiler(self) -> LatencyProfiler:
        """The Phase 9B direct monotonic latency profiler."""
        return self._latency_profiler

    @property
    def forensics_engine(self) -> FailureForensicsEngine:
        """The Phase 10B failure forensics engine."""
        return self._forensics

    @property
    def failure_events(self) -> List[FailureEvent]:
        """All Phase 10B failure events detected so far."""
        return self._forensics.events

    @property
    def forensic_windows(self) -> List[ForensicWindow]:
        """All Phase 10B forensic inspection windows (before/failure/after)."""
        return self._forensics.forensic_windows

    @property
    def error_budget_analyzer(self) -> ErrorBudgetAnalyzer:
        """The Phase 11B tracking error budget analyzer."""
        return self._error_budget_analyzer

    @property
    def ground_truth_aligner(self) -> Optional[GroundTruthCSVAligner]:
        """The ground-truth trajectory aligner if configured."""
        return self._gt_aligner

    def set_ground_truth(self, ground_truth: Union[GroundTruthCSVAligner, str, Path]) -> bool:
        """Load or set ground-truth reference trajectory for error-budget analysis."""
        if isinstance(ground_truth, (str, Path)):
            self._gt_aligner = GroundTruthCSVAligner(ground_truth)
        elif isinstance(ground_truth, GroundTruthCSVAligner):
            self._gt_aligner = ground_truth
        else:
            raise TypeError(
                f"Expected GroundTruthCSVAligner or path, got {type(ground_truth).__name__}"
            )
        return self._gt_aligner.is_loaded

    def compute_latency_report(self) -> EndToEndLatencyReport:
        """Generate statistical metrics (mean, median, P95, P99, max) across all 7 stages."""
        return self._latency_profiler.generate_report()

    def compute_error_budget(self) -> ErrorBudgetSummary:
        """Generate statistical summary of tracking error budget across all processed frames."""
        return self._error_budget_analyzer.generate_summary()

    def format_error_budget_table(self) -> str:
        """Render formatted tracking error budget table."""
        return self.compute_error_budget().format_table()

    @property
    def records(self) -> List[PipelineMeasurementRecord]:
        """Telemetry records of all processed frames."""
        return list(self._records)

    def open(self) -> bool:
        """Open the underlying video source if not already opened."""
        if not self._source.is_open():
            return self._source.open()
        return True

    def reset(self) -> None:
        """Reset stream, track, PAT manager, controller, temporal history, latency profiler, and clear records."""
        self._source.reset()
        if self._track is not None:
            self._track.reset()
        if self._pat_manager is not None:
            self._pat_manager = PATModeManager(self._pat_manager.thresholds)
        if self._controller is not None:
            self._controller.reset()
        self._temporal_analyzer.reset()
        self._latency_profiler.reset()
        self._forensics.reset()
        self._error_budget_analyzer.reset()
        self._records.clear()

    def process_frame(self) -> Optional[Tuple[PipelineMeasurementRecord, DetectionResult]]:
        """Process the next frame in the stream through the existing HYBRID pipeline.

        Pipeline Steps:
          1. Read external frame packet and geometry-preserving processing frame.
          2. Validate the Common Frame format (strictly 640x480, 2D, uint8).
          3. Pass Common Frame to existing HYBRID detector.
          4. Map subpixel centroid to original coordinates if geometry transformed.
          5. Extract physical uncertainty and optical quality dimensions.
          6. Update estimator with observation trustworthiness and capture innovation.
          7. Perform temporal jump consistency evaluation across consecutive frames.
          8. Record and return measurement telemetry.

        Returns:
            Tuple of (PipelineMeasurementRecord, DetectionResult) or None if EOF / invalid.
        """
        if not self._source.is_open():
            if not self.open():
                return None

        # 1. Read Common Frame from external source
        packet, _ = self._source.read_processing_frame()
        if not packet.valid or packet.frame is None:
            return None
        proc_frame = packet.frame

        t_prep_start = time.perf_counter()

        # 2. Strict Common Frame validation using existing perception preprocessor
        common_frame = validate_input_frame(proc_frame, expected_width=640, expected_height=480)

        # 3. Dynamic ROI calculation (Phase 6B)
        dynamic_roi: Optional[DynamicROI] = None
        pred_pos: Optional[Tuple[float, float]] = None
        pred_cov: Optional[np.ndarray] = None

        filter_obj = self._track.filter if self._track is not None else None
        if self._enable_dynamic_roi and filter_obj is not None and filter_obj.is_initialized:
            dt_step = max(1e-4, float(packet.dt)) if packet.dt > 0 else 0.0333
            pred_x, pred_cov = filter_obj.predict(dt_step)
            pred_pos = (
                (float(pred_x[0, 0]), float(pred_x[1, 0]))
                if pred_x.ndim == 2
                else (float(pred_x[0]), float(pred_x[1]))
            )
            track_conf = 1.0
            if self._pat_manager is not None:
                track_conf = float(self._pat_manager.state.track_quality)
            elif hasattr(filter_obj, "health") and filter_obj.health is not None:
                track_conf = float(filter_obj.health.track_health)

            dynamic_roi = self._roi_manager.compute_roi(
                predicted_position=pred_pos,
                covariance=pred_cov,
                image_shape=(480, 640),
                target_geometry=self._last_detected_geometry,
                confidence=track_conf,
                track_age=filter_obj.track_age,
                consecutive_misses=filter_obj.consecutive_misses,
                filter_status=self._track.status if self._track else EstimatorStatus.UNINITIALIZED,
            )

        t_prep_end = time.perf_counter()

        # 4. Existing HYBRID detection (Phase 4B/5B/6B)
        t_hybrid_start = time.perf_counter()
        det_result: DetectionResult = self._detector.detect(
            common_frame,
            timestamp=packet.timestamp,
            collect_diagnostics=True,
            estimator_prediction=pred_pos if (dynamic_roi and not dynamic_roi.is_full_frame) else None,
            prediction_covariance=pred_cov if (dynamic_roi and not dynamic_roi.is_full_frame) else None,
            roi=dynamic_roi,
        )

        # False-Loss Defense: If missed inside dynamic ROI, immediately fall back to full-frame recovery
        if not det_result.detected and dynamic_roi is not None and not dynamic_roi.is_full_frame:
            det_result_full = self._detector.detect(
                common_frame,
                timestamp=packet.timestamp,
                collect_diagnostics=True,
            )
            if det_result_full.detected:
                det_result = det_result_full

        t_hybrid_end = time.perf_counter()
        proc_latency_ms = (t_hybrid_end - t_hybrid_start) * 1000.0

        # Update geometry adaptation
        if det_result.detected and det_result.bbox is not None:
            bw, bh = float(det_result.bbox[2]), float(det_result.bbox[3])
            if bw >= 2.0 and bh >= 2.0:
                self._last_detected_geometry = (bw, bh)

        # Update timebase processing throughput
        if self._source.timebase:
            self._source.timebase.record_processing_latency(proc_latency_ms)

        # 5. Extract Measurement Centroids
        centroid_proc: Optional[Tuple[float, float]] = None
        centroid_orig: Optional[Tuple[float, float]] = None

        if det_result.detected and det_result.centroid is not None:
            centroid_proc = (float(det_result.centroid[0]), float(det_result.centroid[1]))
            # Reversible coordinate mapping to original MP4 frame space
            if self._source.geometry_transformer is not None:
                orig_pt = self._source.geometry_transformer.processing_to_original(
                    centroid_proc[0], centroid_proc[1]
                )
                centroid_orig = (float(orig_pt[0]), float(orig_pt[1]))
            else:
                centroid_orig = centroid_proc

        source_name = getattr(det_result, "detector_source", "HYBRID")
        agreement_name = getattr(det_result, "agreement_state", "AGREEMENT")
        if hasattr(source_name, "name"):
            source_name = source_name.name
        if hasattr(agreement_name, "name"):
            agreement_name = agreement_name.name

        bbox = getattr(det_result, "bbox", None)
        bbox_tuple = (
            (float(bbox[0]), float(bbox[1]), float(bbox[2]), float(bbox[3]))
            if bbox is not None
            else None
        )

        # Candidate Quality, Geometry, Confidence & Uncertainty extraction
        cand_quality_dict: Optional[Dict[str, Any]] = None
        q = det_result.quality
        if q is not None:
            cand_quality_dict = {
                "snr": round(float(q.snr), 2),
                "circularity": round(float(q.circularity), 3),
                "compactness": round(float(q.compactness), 3),
                "symmetry": round(float(q.symmetry), 3),
                "radial_consistency": round(float(q.radial_consistency), 3),
                "size_plausibility": round(float(q.size_plausibility), 3),
                "local_contrast": round(float(q.local_contrast), 2),
                "bg_mean": round(float(q.bg_mean), 2),
                "bg_variance": round(float(q.bg_variance), 2),
                "integrated_flux": round(float(q.integrated_flux), 1),
                "scale_class_px": int(q.scale_class_px),
                "centroid_method": str(q.centroid_method),
            }

        cand_geom_dict: Optional[Dict[str, Any]] = None
        if bbox_tuple is not None:
            w, h = bbox_tuple[2], bbox_tuple[3]
            area = w * h
            is_clipped = bool(q.clipped_by_edge) if q is not None else False
            cand_geom_dict = {
                "bbox": bbox_tuple,
                "area_px": round(float(area), 1),
                "width": round(float(w), 1),
                "height": round(float(h), 1),
                "aspect_ratio": round(float(w / max(1e-3, h)), 2),
                "clipped_by_edge": is_clipped,
            }

        c_conf: Optional[float] = None
        n_conf: Optional[float] = None
        agreement_info: Optional[Dict[str, Any]] = None

        if det_result.unified_candidates:
            top_uc = det_result.unified_candidates[0]
            c_conf = float(top_uc.classical_confidence) if top_uc.classical_confidence is not None else None
            n_conf = float(top_uc.neural_confidence) if top_uc.neural_confidence is not None else None
            agreement_info = {
                "state": str(agreement_name),
                "decision_reason": getattr(det_result, "decision_reason", ""),
            }

        uncertainty: Optional[Tuple[float, float]] = None
        if det_result.detected:
            uncertainty = (float(det_result.sigma_u_px), float(det_result.sigma_v_px))

        # 6. Inform Estimator & Data Association (Phase 7B)
        t_est_start = time.perf_counter()
        estimate: Optional[StateEstimate] = None
        inno_vec: Optional[Tuple[float, float]] = None
        inno_mahal: Optional[float] = None
        est_state: Optional[Tuple[float, float]] = None
        est_vel: Optional[Tuple[float, float]] = None
        cov_mat: Optional[np.ndarray] = None
        mode_probs: Optional[Tuple[float, float, float]] = None

        if self._track is not None and self._enable_estimator:
            meas_for_track = centroid_proc if det_result.detected else None
            conf_for_track = float(det_result.confidence) if det_result.detected else 0.0
            estimate = self._track.step(
                measurement=meas_for_track,
                confidence=conf_for_track,
                timestamp=packet.timestamp,
                gimbal_pan_rate=0.0,
                gimbal_tilt_rate=0.0,
                is_sensor_step=True,
                spot_uncertainty=uncertainty,
            )

            if estimate is not None:
                est_state = (float(estimate.estimated_x), float(estimate.estimated_y))
                est_vel = (float(estimate.estimated_vx), float(estimate.estimated_vy))
                cov_mat = estimate.covariance.copy() if estimate.covariance is not None else None
                if estimate.innovation is not None:
                    inno_vec = (float(estimate.innovation[0, 0]), float(estimate.innovation[1, 0]))
                inno_mahal = float(estimate.mahalanobis_distance)
                if estimate.estimator_health is not None:
                    mode_probs = estimate.estimator_health.model_probabilities
                elif hasattr(self._track.filter, "mode_probabilities"):
                    mode_probs = self._track.filter.mode_probabilities

        t_est_end = time.perf_counter()

        # 7. PAT Mode Manager Integration (Phase 7B)
        t_pat_start = time.perf_counter()
        pat_state: Optional[PATState] = None
        pat_mode_str: Optional[str] = None
        pat_dict: Optional[Dict[str, Any]] = None

        if self._pat_manager is not None and estimate is not None:
            cov_trace = float(estimate.position_uncertainty**2)
            is_meas_valid = bool(
                det_result.detected
                and estimate.filter_status != EstimatorStatus.REJECTED_MEASUREMENT
            )
            pat_state = self._pat_manager.process_step(
                dt=max(1e-4, float(packet.dt)) if packet.dt > 0 else 0.0333,
                timestamp_s=packet.timestamp,
                detection_valid=is_meas_valid,
                detection_confidence=float(det_result.confidence) if is_meas_valid else 0.0,
                mahalanobis_d2=float(estimate.mahalanobis_distance**2),
                covariance_trace=cov_trace,
                estimated_u_px=float(estimate.estimated_x),
                estimated_v_px=float(estimate.estimated_y),
                estimated_vx_px_s=float(estimate.estimated_vx),
                estimated_vy_px_s=float(estimate.estimated_vy),
                current_pan_deg=0.0,
                current_tilt_deg=0.0,
                is_new_frame=True,
            )
            pat_mode_str = pat_state.mode.value
            pat_dict = pat_state.to_dict()

        t_pat_end = time.perf_counter()

        # 8. Controller Output Computation (Phase 8B Shadow Pointing)
        t_ctrl_start = time.perf_counter()
        cmd_pan_rate = 0.0
        cmd_tilt_rate = 0.0
        pan_err_deg = 0.0
        tilt_err_deg = 0.0
        is_sat = False

        if pat_state is not None and self._controller is not None:
            pan_err_deg = float(pat_state.pan_error_deg)
            tilt_err_deg = float(pat_state.tilt_error_deg)
            dt_step = max(1e-4, float(packet.dt)) if packet.dt > 0 else 0.0333
            reacq_pan = (
                float(pat_state.reacquire_pan_rate)
                if hasattr(pat_state, "reacquire_pan_rate")
                else 0.0
            )
            reacq_tilt = (
                float(pat_state.reacquire_tilt_rate)
                if hasattr(pat_state, "reacquire_tilt_rate")
                else 0.0
            )
            vx_val = float(estimate.estimated_vx) if estimate else 0.0
            vy_val = float(estimate.estimated_vy) if estimate else 0.0

            cmd_pan_rate, cmd_tilt_rate, _, _, _, _, is_sat = (
                self._controller.compute_control_command(
                    dt=dt_step,
                    pat_state=pat_state,
                    search_pan_rate=0.0,
                    search_tilt_rate=0.0,
                    reacquire_pan_rate=reacq_pan,
                    reacquire_tilt_rate=reacq_tilt,
                    estimated_vx_px_s=vx_val,
                    estimated_vy_px_s=vy_val,
                )
            )

        t_ctrl_end = time.perf_counter()
        t_cmd_avail = t_ctrl_end

        # 9. Phase 9B Direct Latency Profiling
        t_frame_avail = packet.frame_available_t if packet.frame_available_t > 0 else t_prep_start
        t_dec_start = packet.decode_start_t if packet.decode_start_t > 0 else t_prep_start
        t_dec_end = packet.decode_end_t if packet.decode_end_t > 0 else t_prep_start

        lat_rec = self._latency_profiler.record_frame(
            frame_id=packet.frame_id,
            video_timestamp=packet.timestamp,
            frame_available_t=t_frame_avail,
            decode_start_t=t_dec_start,
            decode_end_t=t_dec_end,
            preprocessing_start_t=t_prep_start,
            preprocessing_end_t=t_prep_end,
            hybrid_start_t=t_hybrid_start,
            hybrid_end_t=t_hybrid_end,
            imm_ekf_start_t=t_est_start,
            imm_ekf_end_t=t_est_end,
            pat_start_t=t_pat_start,
            pat_end_t=t_pat_end,
            controller_start_t=t_ctrl_start,
            controller_end_t=t_ctrl_end,
            command_available_t=t_cmd_avail,
        )

        latency_breakdown = {
            "decode_ms": lat_rec.decode_ms,
            "preprocessing_ms": lat_rec.preprocessing_ms,
            "hybrid_ms": lat_rec.hybrid_ms,
            "estimation_ms": lat_rec.estimation_ms,
            "pat_ms": lat_rec.pat_ms,
            "controller_ms": lat_rec.controller_ms,
            "total_ms": lat_rec.total_ms,
        }

        # 10. Temporal Consistency & Jump Diagnosis across (k-1, k, k+1)
        jump_diag = self._temporal_analyzer.record_frame(
            frame_id=packet.frame_id,
            timestamp=packet.timestamp,
            dt=packet.dt,
            centroid=centroid_proc,
            confidence=float(det_result.confidence),
            detected=bool(det_result.detected),
            detector_source=str(source_name),
            quality=cand_quality_dict,
            candidate_count=det_result.candidate_count,
            clipped_by_edge=bool(q.clipped_by_edge) if q is not None else False,
        )
        jump_cause_str = jump_diag.cause.value if jump_diag is not None else "NONE"

        record = PipelineMeasurementRecord(
            frame_id=packet.frame_id,
            timestamp=packet.timestamp,
            dt=packet.dt,
            centroid=centroid_proc,
            centroid_original=centroid_orig,
            confidence=float(det_result.confidence),
            detected=bool(det_result.detected),
            bounding_box=bbox_tuple,
            source=str(source_name),
            agreement_state=str(agreement_name),
            decode_latency_ms=packet.decode_latency_ms,
            processing_latency_ms=proc_latency_ms,
            is_dropped=bool(getattr(packet, "dropped_frames", 0) > 0),
            candidate_quality=cand_quality_dict,
            candidate_geometry=cand_geom_dict,
            classical_confidence=c_conf,
            neural_confidence=n_conf,
            detector_agreement=agreement_info,
            validity=bool(det_result.detected),
            uncertainty=uncertainty,
            innovation=inno_vec,
            innovation_mahalanobis=inno_mahal,
            jump_classification=jump_cause_str,
            roi_bbox=det_result.roi_bbox,
            is_roi_used=det_result.is_roi_used,
            estimated_state=est_state,
            estimated_velocity=est_vel,
            covariance=cov_mat,
            model_probabilities=mode_probs,
            pat_mode=pat_mode_str,
            pat_state=pat_dict,
            pan_error_deg=pan_err_deg,
            tilt_error_deg=tilt_err_deg,
            commanded_pan_rate=cmd_pan_rate,
            commanded_tilt_rate=cmd_tilt_rate,
            is_saturated=is_sat,
            latency_record=lat_rec,
            latency_breakdown_ms=latency_breakdown,
        )

        # Phase 10B: ingest into failure forensics engine
        forensic_event = self._forensics.ingest(record)

        # Phase 11B: evaluate error budget against reference coordinates if ground truth is loaded
        ref_pos: Optional[Tuple[float, float]] = None
        ref_vel: Optional[Tuple[float, float]] = None
        if self._gt_aligner is not None and self._gt_aligner.is_loaded:
            gt_sample = self._gt_aligner.get_aligned_sample(packet.timestamp)
            if gt_sample is not None:
                ref_pos = (float(gt_sample.u), float(gt_sample.v))
                ref_vel = (float(gt_sample.vx), float(gt_sample.vy))

        frame_budget = self._error_budget_analyzer.ingest(
            record=record,
            reference_pos=ref_pos,
            reference_vel=ref_vel,
            geometry_transformer=self._source.geometry_transformer,
        )

        # Rebuild record with attached forensics event and error budget
        record = PipelineMeasurementRecord(
            frame_id=record.frame_id,
            timestamp=record.timestamp,
            dt=record.dt,
            centroid=record.centroid,
            centroid_original=record.centroid_original,
            confidence=record.confidence,
            detected=record.detected,
            bounding_box=record.bounding_box,
            source=record.source,
            agreement_state=record.agreement_state,
            decode_latency_ms=record.decode_latency_ms,
            processing_latency_ms=record.processing_latency_ms,
            is_dropped=record.is_dropped,
            candidate_quality=record.candidate_quality,
            candidate_geometry=record.candidate_geometry,
            classical_confidence=record.classical_confidence,
            neural_confidence=record.neural_confidence,
            detector_agreement=record.detector_agreement,
            validity=record.validity,
            uncertainty=record.uncertainty,
            innovation=record.innovation,
            innovation_mahalanobis=record.innovation_mahalanobis,
            jump_classification=record.jump_classification,
            roi_bbox=record.roi_bbox,
            is_roi_used=record.is_roi_used,
            estimated_state=record.estimated_state,
            estimated_velocity=record.estimated_velocity,
            covariance=record.covariance,
            model_probabilities=record.model_probabilities,
            pat_mode=record.pat_mode,
            pat_state=record.pat_state,
            pan_error_deg=record.pan_error_deg,
            tilt_error_deg=record.tilt_error_deg,
            commanded_pan_rate=record.commanded_pan_rate,
            commanded_tilt_rate=record.commanded_tilt_rate,
            is_saturated=record.is_saturated,
            latency_record=record.latency_record,
            latency_breakdown_ms=record.latency_breakdown_ms,
            forensic_event=forensic_event,
            error_budget=frame_budget,
        )

        self._records.append(record)
        return record, det_result

    def run(self, max_frames: Optional[int] = None) -> List[PipelineMeasurementRecord]:
        """Process the entire external video stream sequentially through HYBRID.

        Args:
            max_frames: Optional maximum frame limit to process.

        Returns:
            List of PipelineMeasurementRecord for every processed frame.
        """
        if not self._source.is_open():
            if not self.open():
                return []

        count = 0
        while not self._source.is_eof:
            if max_frames is not None and count >= max_frames:
                break
            res = self.process_frame()
            if res is None:
                break
            count += 1

        return self.records

    def close(self) -> None:
        """Close source if owned."""
        if self._owns_source and self._source.is_open():
            self._source.close()

    def __enter__(self) -> ExternalHybridPipeline:
        self.open()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.close()
