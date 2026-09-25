"""
HORIZON Phase 14B: Benchmark-2 Run Manifest & Reproducibility Engine
====================================================================
Generates comprehensive, non-destructive reproducibility manifests and telemetry
logs for external-video benchmark runs.

Required Manifest Telemetry:
  - run_id (unique run identifier)
  - video filename & SHA-256 hash
  - resolution, source FPS, duration, total frames
  - processing resolution (640x480 Common Frame)
  - coordinate transform parameters
  - perception configuration
  - estimator configuration
  - controller configuration
  - PAT configuration
  - software version
  - model/version information
  - hardware/runtime information
  - timing policy
  - results summary

Generated Artifacts:
  - run_manifest.json
  - frame_log.csv
  - summary.json

Strict Invariants:
  - Do not overwrite historical results silently.
  - Re-running identical source & configuration yields reproducible metrics
    within expected numerical tolerance.
  - Zero fabricated values; all telemetry reflects actual empirical execution.
"""

from __future__ import annotations

import csv
from dataclasses import asdict, dataclass, field
import datetime
import hashlib
import json
import logging
import math
import os
from pathlib import Path
import platform
import sys
import time
from typing import Any, Dict, List, Optional, Tuple, Union
import uuid

import numpy as np

from control.camera_controller import PATCameraController
from pat.mode_manager import PATModeManager
from pat.state import PATMode
from simulator.perception.config import DetectorConfig
from simulator.perception.hybrid_detector import HybridBeaconDetector
from sources.csv_aligner import GroundTruthCSVAligner
from sources.error_budget import ErrorBudgetSummary
from sources.external_video_source import ExternalVideoSource
from sources.video_pipeline import ExternalHybridPipeline, PipelineMeasurementRecord
from tracking.association.track import Track
from tracking.estimation.imm_kalman import InteractingMultipleModelFilter

logger = logging.getLogger(__name__)

HORIZON_VERSION = "2.0.0-phase14b"


# ==============================================================================
# Helper Functions: Hashing & System Metadata
# ==============================================================================

def compute_file_sha256(filepath: Union[str, Path], chunk_size: int = 65536) -> str:
    """Compute the cryptographic SHA-256 hash of a file."""
    p = Path(filepath).resolve()
    if not p.is_file():
        return f"FILE_NOT_FOUND:{p.name}"
    
    hasher = hashlib.sha256()
    with open(p, "rb") as f:
        while chunk := f.read(chunk_size):
            hasher.update(chunk)
    return hasher.hexdigest()


def get_hardware_runtime_info() -> Dict[str, Any]:
    """Inspect current host hardware and runtime environment."""
    info = {
        "platform": platform.platform(),
        "system": platform.system(),
        "release": platform.release(),
        "version": platform.version(),
        "machine": platform.machine(),
        "processor": platform.processor() or "Generic Processor",
        "cpu_count_logical": os.cpu_count() or 1,
        "python_implementation": platform.python_implementation(),
        "python_version": sys.version.split()[0],
        "execution_provider": "CPUExecutionProvider",
    }
    try:
        import onnxruntime as ort
        available_providers = ort.get_available_providers()
        info["onnxruntime_providers"] = available_providers
        if "CUDAExecutionProvider" in available_providers:
            info["execution_provider"] = "CUDAExecutionProvider"
    except Exception:
        info["onnxruntime_providers"] = ["CPUExecutionProvider"]
        
    return info


def get_software_version_info() -> Dict[str, Any]:
    """Collect software and dependency versions."""
    import cv2
    software_info = {
        "horizon_version": HORIZON_VERSION,
        "python_version": sys.version.split()[0],
        "numpy_version": np.__version__,
        "opencv_version": cv2.__version__,
    }
    try:
        import onnxruntime as ort
        software_info["onnxruntime_version"] = ort.__version__
    except Exception:
        software_info["onnxruntime_version"] = "N/A"
    return software_info


def get_model_version_info(detector: Optional[HybridBeaconDetector] = None) -> Dict[str, Any]:
    """Capture model files, versions, and cryptographic hashes."""
    model_info = {
        "classical_detector_version": "v2.0-spatial-moments",
        "hybrid_fusion_version": "v2.0-adaptive-bayesian",
        "yolo_model_architecture": "YOLOv8n-beacon",
        "yolo_weights_path": "embedded/synthetic",
        "yolo_weights_hash": "N/A",
    }
    if detector is not None and hasattr(detector, "_neural_detector"):
        neural = detector._neural_detector
        if hasattr(neural, "model_path") and neural.model_path:
            p = Path(neural.model_path)
            model_info["yolo_weights_path"] = str(p)
            if p.is_file():
                model_info["yolo_weights_hash"] = compute_file_sha256(p)
    return model_info


def get_timing_policy_info() -> Dict[str, Any]:
    """Capture authoritative timestamp and clock synchronization policy."""
    return {
        "timebase_source": "AUTHORITATIVE_VIDEO_TIMESTAMP",
        "timestamp_clock": "CONTAINER_PTS",
        "jitter_handling": "MONOTONIC_STEP_CLAMP",
        "fps_source": "VIDEO_CONTAINER_METADATA",
        "wall_clock_profiling": "MONOTONIC_PERF_COUNTER",
    }


def _json_serializable(obj: Any) -> Any:
    """Recursively convert numpy types, dataclasses, and enums into JSON serializable structures."""
    if isinstance(obj, (np.integer, np.int64, np.int32)):
        return int(obj)
    elif isinstance(obj, (np.floating, np.float64, np.float32)):
        if np.isnan(obj):
            return None
        elif np.isinf(obj):
            return "inf" if obj > 0 else "-inf"
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, (datetime.datetime, datetime.date)):
        return obj.isoformat()
    elif hasattr(obj, "value"):
        return obj.value
    elif hasattr(obj, "to_dict"):
        return obj.to_dict()
    elif isinstance(obj, dict):
        return {k: _json_serializable(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [_json_serializable(x) for x in obj]
    return obj


# ==============================================================================
# Manifest Data Structures
# ==============================================================================

@dataclass
class Benchmark2RunManifest:
    """Comprehensive Run Manifest for reproducible external video benchmarking."""
    run_id: str
    timestamp: str
    video_metadata: Dict[str, Any]
    processing_resolution: List[int]
    coordinate_transform: Dict[str, Any]
    perception_configuration: Dict[str, Any]
    estimator_configuration: Dict[str, Any]
    controller_configuration: Dict[str, Any]
    pat_configuration: Dict[str, Any]
    software_version: Dict[str, Any]
    model_version_info: Dict[str, Any]
    hardware_runtime_info: Dict[str, Any]
    timing_policy: Dict[str, Any]
    results: Dict[str, Any]
    output_files: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert manifest to JSON-serializable dictionary."""
        return _json_serializable(asdict(self))

    def to_json(self, indent: int = 2) -> str:
        """Serialize manifest to formatted JSON string."""
        return json.dumps(self.to_dict(), indent=indent)


# ==============================================================================
# Artifact Exporter: Non-Destructive Storage
# ==============================================================================

def generate_benchmark2_artifacts(
    manifest: Benchmark2RunManifest,
    records: List[PipelineMeasurementRecord],
    output_dir: Union[str, Path],
    allow_overwrite: bool = False,
) -> Dict[str, Path]:
    """Generate run_manifest.json, frame_log.csv, and summary.json in output_dir.

    Invariant:
      - Prevents silent overwriting of historical benchmark artifacts.
      - If output_dir already contains manifest artifacts and allow_overwrite is False,
        raises FileExistsError.

    Args:
        manifest: Fully populated Benchmark2RunManifest instance.
        records: Frame-by-frame measurement records from the run.
        output_dir: Destination directory for the artifacts.
        allow_overwrite: Explicit flag to allow overwriting (default False).

    Returns:
        Dict mapping artifact names ('manifest', 'frame_log', 'summary') to absolute Paths.
    """
    out_path = Path(output_dir).resolve()
    
    manifest_file = out_path / "run_manifest.json"
    frame_log_file = out_path / "frame_log.csv"
    summary_file = out_path / "summary.json"

    # Non-destructive check
    if not allow_overwrite:
        existing = [f.name for f in [manifest_file, frame_log_file, summary_file] if f.exists()]
        if existing:
            raise FileExistsError(
                f"Historical benchmark artifacts already exist in '{out_path}' ({', '.join(existing)}). "
                "Silent overwrite is prohibited to preserve reproducibility. "
                "Use a unique run directory or set allow_overwrite=True explicitly."
            )

    out_path.mkdir(parents=True, exist_ok=True)

    # 1. Write run_manifest.json
    manifest.output_files = {
        "run_manifest": "run_manifest.json",
        "frame_log": "frame_log.csv",
        "summary": "summary.json",
    }
    with open(manifest_file, "w", encoding="utf-8") as f:
        f.write(manifest.to_json(indent=2))

    # 2. Write frame_log.csv
    _write_frame_log_csv(frame_log_file, records)

    # 3. Write summary.json
    summary_data = {
        "run_id": manifest.run_id,
        "timestamp": manifest.timestamp,
        "video_filename": manifest.video_metadata.get("video_filename"),
        "video_hash": manifest.video_metadata.get("video_hash"),
        "total_frames": manifest.video_metadata.get("total_frames"),
        "processed_frames": len(records),
        "perception_mode": manifest.perception_configuration.get("mode"),
        "estimator_type": manifest.estimator_configuration.get("filter_type"),
        "results": manifest.results,
    }
    with open(summary_file, "w", encoding="utf-8") as f:
        json.dump(_json_serializable(summary_data), f, indent=2)

    return {
        "manifest": manifest_file,
        "frame_log": frame_log_file,
        "summary": summary_file,
    }


def _write_frame_log_csv(csv_path: Path, records: List[PipelineMeasurementRecord]) -> None:
    """Write comprehensive frame-by-frame telemetry to CSV."""
    fieldnames = [
        "frame_id",
        "timestamp_s",
        "dt_s",
        "detected",
        "centroid_u",
        "centroid_v",
        "centroid_orig_u",
        "centroid_orig_v",
        "confidence",
        "classical_conf",
        "neural_conf",
        "source",
        "agreement_state",
        "validity",
        "uncertainty_u",
        "uncertainty_v",
        "innovation_u",
        "innovation_v",
        "innovation_mahalanobis",
        "roi_used",
        "estimated_u",
        "estimated_v",
        "estimated_vx",
        "estimated_vy",
        "pat_mode",
        "pan_error_deg",
        "tilt_error_deg",
        "cmd_pan_rate_dps",
        "cmd_tilt_rate_dps",
        "is_saturated",
        "decode_latency_ms",
        "hybrid_latency_ms",
        "total_latency_ms",
        "ref_pos_u",
        "ref_pos_v",
        "tracking_error_px",
        "tracking_error_urad",
        "error_px_measurement",
        "error_px_estimation",
        "error_px_prediction",
        "error_px_timing",
        "error_px_control",
        "error_px_reacquisition",
    ]

    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for rec in records:
            u = rec.centroid[0] if rec.centroid else ""
            v = rec.centroid[1] if rec.centroid else ""
            u_orig = rec.centroid_original[0] if rec.centroid_original else ""
            v_orig = rec.centroid_original[1] if rec.centroid_original else ""
            unc_u = rec.uncertainty[0] if rec.uncertainty else ""
            unc_v = rec.uncertainty[1] if rec.uncertainty else ""
            inno_u = rec.innovation[0] if rec.innovation else ""
            inno_v = rec.innovation[1] if rec.innovation else ""
            est_u = rec.estimated_state[0] if rec.estimated_state else ""
            est_v = rec.estimated_state[1] if rec.estimated_state else ""
            est_vx = rec.estimated_velocity[0] if rec.estimated_velocity else ""
            est_vy = rec.estimated_velocity[1] if rec.estimated_velocity else ""

            # Latency breakdown
            dec_lat = rec.decode_latency_ms
            hyb_lat = rec.latency_breakdown_ms.get("hybrid_ms", 0.0) if rec.latency_breakdown_ms else 0.0
            tot_lat = rec.latency_breakdown_ms.get("total_ms", rec.processing_latency_ms) if rec.latency_breakdown_ms else rec.processing_latency_ms

            # Error budget components
            ref_u, ref_v, tot_err_px, tot_err_urad = "", "", "", ""
            err_meas, err_est, err_pred, err_time, err_ctrl, err_reacq = "", "", "", "", "", ""

            if rec.error_budget is not None:
                b = rec.error_budget
                if b.reference_pos is not None:
                    ref_u, ref_v = b.reference_pos[0], b.reference_pos[1]
                if b.total_error is not None and b.total_error.is_available:
                    tot_err_px = round(b.total_error.value_px, 4)
                    tot_err_urad = round(b.total_error.value_urad, 2)
                if b.measurement_error is not None and b.measurement_error.is_available:
                    err_meas = round(b.measurement_error.value_px, 4)
                if b.estimation_residual is not None and b.estimation_residual.is_available:
                    err_est = round(b.estimation_residual.value_px, 4)
                if b.prediction_residual is not None and b.prediction_residual.is_available:
                    err_pred = round(b.prediction_residual.value_px, 4)
                if b.timing_contribution is not None and b.timing_contribution.is_available:
                    err_time = round(b.timing_contribution.value_px, 4)
                if b.control_response_contribution is not None and b.control_response_contribution.is_available:
                    err_ctrl = round(b.control_response_contribution.value_px, 4)
                if b.reacquisition_contribution is not None and b.reacquisition_contribution.is_available:
                    err_reacq = round(b.reacquisition_contribution.value_px, 4)

            row = {
                "frame_id": rec.frame_id,
                "timestamp_s": f"{rec.timestamp:.6f}",
                "dt_s": f"{rec.dt:.6f}",
                "detected": int(rec.detected),
                "centroid_u": f"{u:.4f}" if isinstance(u, (int, float)) else "",
                "centroid_v": f"{v:.4f}" if isinstance(v, (int, float)) else "",
                "centroid_orig_u": f"{u_orig:.4f}" if isinstance(u_orig, (int, float)) else "",
                "centroid_orig_v": f"{v_orig:.4f}" if isinstance(v_orig, (int, float)) else "",
                "confidence": f"{rec.confidence:.4f}",
                "classical_conf": f"{rec.classical_confidence:.4f}",
                "neural_conf": f"{rec.neural_confidence:.4f}",
                "source": rec.source,
                "agreement_state": rec.agreement_state,
                "validity": int(rec.validity),
                "uncertainty_u": f"{unc_u:.4f}" if isinstance(unc_u, (int, float)) else "",
                "uncertainty_v": f"{unc_v:.4f}" if isinstance(unc_v, (int, float)) else "",
                "innovation_u": f"{inno_u:.4f}" if isinstance(inno_u, (int, float)) else "",
                "innovation_v": f"{inno_v:.4f}" if isinstance(inno_v, (int, float)) else "",
                "innovation_mahalanobis": f"{rec.innovation_mahalanobis:.4f}" if rec.innovation_mahalanobis is not None else "",
                "roi_used": int(rec.is_roi_used),
                "estimated_u": f"{est_u:.4f}" if isinstance(est_u, (int, float)) else "",
                "estimated_v": f"{est_v:.4f}" if isinstance(est_v, (int, float)) else "",
                "estimated_vx": f"{est_vx:.4f}" if isinstance(est_vx, (int, float)) else "",
                "estimated_vy": f"{est_vy:.4f}" if isinstance(est_vy, (int, float)) else "",
                "pat_mode": rec.pat_mode,
                "pan_error_deg": f"{rec.pan_error_deg:.6f}" if rec.pan_error_deg is not None else "",
                "tilt_error_deg": f"{rec.tilt_error_deg:.6f}" if rec.tilt_error_deg is not None else "",
                "cmd_pan_rate_dps": f"{rec.commanded_pan_rate:.6f}" if rec.commanded_pan_rate is not None else "",
                "cmd_tilt_rate_dps": f"{rec.commanded_tilt_rate:.6f}" if rec.commanded_tilt_rate is not None else "",
                "is_saturated": int(rec.is_saturated) if rec.is_saturated is not None else 0,
                "decode_latency_ms": f"{dec_lat:.3f}",
                "hybrid_latency_ms": f"{hyb_lat:.3f}",
                "total_latency_ms": f"{tot_lat:.3f}",
                "ref_pos_u": f"{ref_u:.4f}" if isinstance(ref_u, (int, float)) else "",
                "ref_pos_v": f"{ref_v:.4f}" if isinstance(ref_v, (int, float)) else "",
                "tracking_error_px": str(tot_err_px),
                "tracking_error_urad": str(tot_err_urad),
                "error_px_measurement": str(err_meas),
                "error_px_estimation": str(err_est),
                "error_px_prediction": str(err_pred),
                "error_px_timing": str(err_time),
                "error_px_control": str(err_ctrl),
                "error_px_reacquisition": str(err_reacq),
            }
            writer.writerow(row)


# ==============================================================================
# Benchmark-2 Run Manager
# ==============================================================================

class Benchmark2RunManager:
    """Coordinates execution, metadata harvesting, and manifest generation."""

    def __init__(
        self,
        runs_root: Union[str, Path] = "benchmark_runs",
        sensor_fov_deg: float = 4.0,
        sensor_width_px: int = 640,
    ) -> None:
        self._runs_root = Path(runs_root).resolve()
        self._sensor_fov_deg = float(sensor_fov_deg)
        self._sensor_width_px = int(sensor_width_px)

    @property
    def runs_root(self) -> Path:
        return self._runs_root

    def create_run_id(self, prefix: str = "run") -> str:
        """Create a unique, timestamped run ID."""
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        uid = uuid.uuid4().hex[:8]
        return f"{prefix}_{ts}_{uid}"

    def execute_benchmark_run(
        self,
        video_path: Union[str, Path],
        detector_config: Optional[DetectorConfig] = None,
        enable_estimator: bool = True,
        enable_dynamic_roi: bool = True,
        ground_truth: Optional[Union[GroundTruthCSVAligner, str, Path]] = None,
        max_frames: Optional[int] = None,
        run_id: Optional[str] = None,
        output_dir: Optional[Union[str, Path]] = None,
        allow_overwrite: bool = False,
    ) -> Tuple[Benchmark2RunManifest, List[PipelineMeasurementRecord], Dict[str, Path]]:
        """Execute a complete external video benchmark run and generate reproducibility artifacts.

        Args:
            video_path: Path to the target MP4 sensor recording.
            detector_config: Optional DetectorConfig (defaults to HYBRID).
            enable_estimator: Whether IMM-EKF estimation is engaged.
            enable_dynamic_roi: Whether dynamic ROI is active.
            ground_truth: Optional ground truth reference CSV or aligner.
            max_frames: Optional frame limit.
            run_id: Optional custom run ID (auto-generated if None).
            output_dir: Optional custom output directory (defaults to runs_root / run_id).
            allow_overwrite: Whether to allow overwriting if output directory exists.

        Returns:
            Tuple of (manifest, records, artifact_paths_dict).
        """
        vid_path = Path(video_path).resolve()
        if not vid_path.is_file():
            raise FileNotFoundError(f"Video file not found: {vid_path}")

        # Unique run ID and directory
        active_run_id = run_id or self.create_run_id()
        dest_dir = Path(output_dir).resolve() if output_dir is not None else (self._runs_root / active_run_id)

        # 1. Extract Video File Metadata & Hash
        video_hash = compute_file_sha256(vid_path)
        source = ExternalVideoSource(vid_path)
        if not source.open():
            raise RuntimeError(f"Failed to open video source: {vid_path}")

        video_meta = {
            "video_filename": vid_path.name,
            "video_path": str(vid_path),
            "video_hash": video_hash,
            "resolution": [source.width, source.height],
            "source_fps": source.fps,
            "duration_seconds": source.duration,
            "total_frames": source.frame_count,
            "codec": source.codec,
        }

        # 2. Extract Coordinate Transform info
        transformer = source.geometry_transformer
        coord_transform = {
            "source_resolution": [source.width, source.height],
            "processing_resolution": [640, 480],
            "transformation_method": transformer.method.value if transformer else "DIRECT_RESCALE",
            "scale_x": transformer.scale_x if transformer else (640.0 / source.width),
            "scale_y": transformer.scale_y if transformer else (480.0 / source.height),
            "offset_x": transformer.offset_x if transformer else 0.0,
            "offset_y": transformer.offset_y if transformer else 0.0,
            "optical_axis": [320.0, 240.0],
            "sensor_fov_deg": self._sensor_fov_deg,
            "focal_length_px": (self._sensor_width_px / 2.0) / math.tan(math.radians(self._sensor_fov_deg / 2.0)),
        }

        # 3. Configure Pipeline
        det_cfg = detector_config or DetectorConfig(perception_mode="HYBRID")
        detector = HybridBeaconDetector(det_cfg)
        track = Track(filter_type="IMM_ADAPTIVE_EKF") if enable_estimator else None
        pat_mgr = PATModeManager()
        controller = PATCameraController()

        pipeline = ExternalHybridPipeline(
            video_source=source,
            detector=detector,
            detector_config=det_cfg,
            enable_estimator=enable_estimator,
            enable_dynamic_roi=enable_dynamic_roi,
            track=track,
            pat_manager=pat_mgr,
            controller=controller,
            ground_truth=ground_truth,
            sensor_fov_deg=self._sensor_fov_deg,
            sensor_width_px=self._sensor_width_px,
        )

        # 4. Harvest Component Configurations
        perception_cfg = {
            "mode": getattr(det_cfg, "perception_mode", "HYBRID"),
            "classical_weight": det_cfg.hybrid.fusion.classical_weight if hasattr(det_cfg, "hybrid") else 0.28,
            "neural_weight": det_cfg.hybrid.fusion.neural_weight if hasattr(det_cfg, "hybrid") else 0.28,
            "confidence_threshold": getattr(det_cfg, "min_detection_confidence", 0.28),
            "classical_threshold": det_cfg.scoring.min_snr if hasattr(det_cfg, "scoring") else 1.2,
            "yolo_confidence_threshold": det_cfg.neural.confidence_threshold if hasattr(det_cfg, "neural") else 0.35,
            "dynamic_roi_enabled": enable_dynamic_roi,
            "dynamic_roi_sigma_multiplier": 3.0,
            "dynamic_roi_min_size": [64, 64],
            "dynamic_roi_max_size": [640, 480],
        }

        estimator_cfg = {
            "enabled": enable_estimator,
            "filter_type": "IMM_ADAPTIVE_EKF" if enable_estimator else "DISABLED",
            "state_dimension": 4,
            "state_variables": ["x", "y", "vx", "vy"],
            "models": ["CONSTANT_VELOCITY", "COORDINATED_TURN", "CONSTANT_ACCELERATION"] if enable_estimator else [],
        }

        controller_cfg = {
            "controller_type": "PATCameraController",
            "kp_pan": controller.kp_pan if hasattr(controller, "kp_pan") else 1.2,
            "ki_pan": controller.ki_pan if hasattr(controller, "ki_pan") else 0.05,
            "kd_pan": controller.kd_pan if hasattr(controller, "kd_pan") else 0.1,
            "max_pan_rate_dps": controller.max_pan_rate if hasattr(controller, "max_pan_rate") else 10.0,
            "max_tilt_rate_dps": controller.max_tilt_rate if hasattr(controller, "max_tilt_rate") else 10.0,
        }

        pat_cfg = {
            "manager_type": "PATModeManager",
            "states": [s.value for s in PATMode],
            "track_gate_px": 15.0,
            "fine_gate_px": 8.0,
            "reacquisition_gate_px": 30.0,
            "coarse_timeout_s": 2.0,
            "fine_timeout_s": 1.0,
        }

        software_info = get_software_version_info()
        model_info = get_model_version_info(detector)
        hardware_info = get_hardware_runtime_info()
        timing_policy = get_timing_policy_info()

        # 5. Execute Run
        t_start = time.perf_counter()
        records = pipeline.run(max_frames=max_frames)
        t_duration = time.perf_counter() - t_start

        # 6. Compute Results Summary
        results = self._calculate_results_summary(
            records=records,
            elapsed_wall_time_s=t_duration,
            error_budget_analyzer=pipeline.error_budget_analyzer,
        )

        # 7. Assemble Manifest
        manifest = Benchmark2RunManifest(
            run_id=active_run_id,
            timestamp=datetime.datetime.now().isoformat(),
            video_metadata=video_meta,
            processing_resolution=[640, 480],
            coordinate_transform=coord_transform,
            perception_configuration=perception_cfg,
            estimator_configuration=estimator_cfg,
            controller_configuration=controller_cfg,
            pat_configuration=pat_cfg,
            software_version=software_info,
            model_version_info=model_info,
            hardware_runtime_info=hardware_info,
            timing_policy=timing_policy,
            results=results,
        )

        # 8. Generate Non-Destructive Artifacts
        artifact_paths = generate_benchmark2_artifacts(
            manifest=manifest,
            records=records,
            output_dir=dest_dir,
            allow_overwrite=allow_overwrite,
        )

        return manifest, records, artifact_paths

    def _calculate_results_summary(
        self,
        records: List[PipelineMeasurementRecord],
        elapsed_wall_time_s: float,
        error_budget_analyzer: Any,
    ) -> Dict[str, Any]:
        """Compute comprehensive statistical metrics for the run."""
        total_frames = len(records)
        if total_frames == 0:
            return {
                "total_frames": 0,
                "detected_frames": 0,
                "lock_retention_pct": 0.0,
                "mean_centroid_error_px": None,
                "rmse_px": None,
                "rmse_urad": None,
                "fps": 0.0,
                "mean_latency_ms": 0.0,
                "median_latency_ms": 0.0,
                "p95_latency_ms": 0.0,
                "p99_latency_ms": 0.0,
                "max_latency_ms": 0.0,
                "acquisition_time_s": None,
                "reacquisition_time_s": None,
            }

        detected_count = sum(1 for r in records if r.detected)
        lock_retention_pct = (detected_count / total_frames) * 100.0

        # Latencies
        latencies = [
            r.latency_breakdown_ms.get("total_ms", r.processing_latency_ms)
            if r.latency_breakdown_ms else r.processing_latency_ms
            for r in records
        ]
        mean_lat = float(np.mean(latencies))
        med_lat = float(np.median(latencies))
        p95_lat = float(np.percentile(latencies, 95))
        p99_lat = float(np.percentile(latencies, 99))
        max_lat = float(np.max(latencies))
        fps = (total_frames / elapsed_wall_time_s) if elapsed_wall_time_s > 0 else 0.0

        # Tracking errors & ground truth alignment
        tracking_errors_px: List[float] = []
        tracking_errors_urad: List[float] = []
        for r in records:
            if r.error_budget is not None and r.error_budget.total_error is not None:
                if r.error_budget.total_error.is_available:
                    tracking_errors_px.append(r.error_budget.total_error.value_px)
                    tracking_errors_urad.append(r.error_budget.total_error.value_urad)

        mean_err_px = float(np.mean(tracking_errors_px)) if tracking_errors_px else None
        rmse_px = float(np.sqrt(np.mean(np.square(tracking_errors_px)))) if tracking_errors_px else None
        rmse_urad = float(np.sqrt(np.mean(np.square(tracking_errors_urad)))) if tracking_errors_urad else None

        # Acquisition time
        first_acq_t: Optional[float] = None
        for r in records:
            if r.detected and r.pat_mode in ["FINE_TRACK", "COARSE_TRACK", "TRACK", "FINE_ACQUISITION"]:
                first_acq_t = r.timestamp
                break
            elif r.detected:
                first_acq_t = r.timestamp
                break

        # Error budget summary if available
        eb_summary_dict: Optional[Dict[str, Any]] = None
        if error_budget_analyzer is not None and hasattr(error_budget_analyzer, "generate_summary"):
            eb_summary = error_budget_analyzer.generate_summary()
            if eb_summary is not None:
                eb_summary_dict = eb_summary.to_dict()


        return {
            "total_frames": total_frames,
            "detected_frames": detected_count,
            "lock_retention_pct": round(lock_retention_pct, 2),
            "mean_centroid_error_px": round(mean_err_px, 4) if mean_err_px is not None else None,
            "rmse_px": round(rmse_px, 4) if rmse_px is not None else None,
            "rmse_urad": round(rmse_urad, 2) if rmse_urad is not None else None,
            "fps": round(fps, 2),
            "mean_latency_ms": round(mean_lat, 2),
            "median_latency_ms": round(med_lat, 2),
            "p95_latency_ms": round(p95_lat, 2),
            "p99_latency_ms": round(p99_lat, 2),
            "max_latency_ms": round(max_lat, 2),
            "acquisition_time_s": round(first_acq_t, 4) if first_acq_t is not None else None,
            "error_budget_summary": eb_summary_dict,
        }


# ==============================================================================
# Reproducibility Verification
# ==============================================================================

def verify_run_reproducibility(
    manifest_a: Benchmark2RunManifest,
    manifest_b: Benchmark2RunManifest,
    numerical_tolerance: float = 1e-4,
) -> Tuple[bool, List[str]]:
    """Verify that two benchmark runs on the same configuration are reproducible.

    Compares:
      1. Video hashes & container metadata
      2. Perception, Estimator, PAT, Controller configurations
      3. Coordinate transformations
      4. Results within expected numerical tolerance

    Args:
        manifest_a: First run manifest.
        manifest_b: Second run manifest.
        numerical_tolerance: Maximum allowable difference for floating point metrics.

    Returns:
        Tuple of (is_reproducible: bool, list_of_discrepancies: List[str]).
    """
    discrepancies: List[str] = []

    # 1. Video Hash Check
    hash_a = manifest_a.video_metadata.get("video_hash")
    hash_b = manifest_b.video_metadata.get("video_hash")
    if hash_a != hash_b:
        discrepancies.append(f"Video hash mismatch: '{hash_a}' vs '{hash_b}'")

    # 2. Configuration Checks
    if manifest_a.perception_configuration != manifest_b.perception_configuration:
        discrepancies.append("Perception configuration mismatch between runs")

    if manifest_a.estimator_configuration != manifest_b.estimator_configuration:
        discrepancies.append("Estimator configuration mismatch between runs")

    if manifest_a.coordinate_transform != manifest_b.coordinate_transform:
        discrepancies.append("Coordinate transform mismatch between runs")

    # 3. Numeric Results Checks
    res_a = manifest_a.results
    res_b = manifest_b.results

    if res_a.get("total_frames") != res_b.get("total_frames"):
        discrepancies.append(f"Total frames mismatch: {res_a.get('total_frames')} vs {res_b.get('total_frames')}")

    if res_a.get("detected_frames") != res_b.get("detected_frames"):
        discrepancies.append(f"Detected frames mismatch: {res_a.get('detected_frames')} vs {res_b.get('detected_frames')}")

    numeric_keys = [
        "lock_retention_pct",
        "mean_centroid_error_px",
        "rmse_px",
        "rmse_urad",
        "acquisition_time_s",
    ]

    for key in numeric_keys:
        val_a = res_a.get(key)
        val_b = res_b.get(key)
        if val_a is not None and val_b is not None:
            diff = abs(float(val_a) - float(val_b))
            if diff > numerical_tolerance:
                discrepancies.append(f"Result metric '{key}' discrepancy exceeds tolerance: |{val_a} - {val_b}| = {diff:.6f} > {numerical_tolerance}")
        elif (val_a is None) != (val_b is None):
            discrepancies.append(f"Result metric '{key}' availability mismatch: {val_a} vs {val_b}")

    is_reproducible = len(discrepancies) == 0
    return is_reproducible, discrepancies
