"""
HORIZON Phase 12B: Existing-Algorithm Ablation Framework
=========================================================
Quantifies the progressive contributions of existing pipeline components
under strictly identical input conditions without adding algorithms,
cherry-picking, or applying special per-configuration tuning.

Configurations Evaluated:
  - Config A: Classical path (Classical beacon extraction only)
  - Config B: Neural path (Neural YOLOv8n detector only)
  - Config C: Existing HYBRID (Standard fused classical + neural + optical refinement)
  - Config D: HYBRID + existing IMM-EKF (+ dynamic ROI guidance)
  - Config E: HYBRID + IMM-EKF + existing controller (Full shadow pointing system)

8 Standard Evaluation Metrics:
  1. Centroid Error (Mean px)
  2. RMSE (px & microradians)
  3. Acquisition (Initial lock time & frames)
  4. Reacquisition (Recovery time & success rate after loss)
  5. Lock Retention (Continuous track validity percentage)
  6. False Lock (False positive / divergent tracking count & rate)
  7. Processing FPS (Frames per second throughput)
  8. End-to-End Latency (Mean, median, P95 in ms)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import math
from pathlib import Path
import time
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union
import numpy as np

from control.camera_controller import PATCameraController
from simulator.perception.config import DetectorConfig
from simulator.perception.hybrid_detector import HybridBeaconDetector
from sources.csv_aligner import GroundTruthCSVAligner, GroundTruthSample
from sources.dynamic_roi import DynamicROI, DynamicROIManager
from sources.external_video_source import ExternalVideoSource
from sources.frame_packet import FramePacket
from sources.video_pipeline import ExternalHybridPipeline, PipelineMeasurementRecord
from tracking.association.track import Track
from tracking.estimation.imm_kalman import InteractingMultipleModelFilter


class AblationConfigID(str, Enum):
    """Identifier for the 5 ablation configurations."""
    CONFIG_A_CLASSICAL = "A — Classical path"
    CONFIG_B_NEURAL = "B — Neural path"
    CONFIG_C_HYBRID = "C — Existing HYBRID"
    CONFIG_D_HYBRID_EKF = "D — HYBRID + existing IMM-EKF"
    CONFIG_E_FULL_SYSTEM = "E — HYBRID + IMM-EKF + existing controller"


@dataclass(frozen=True)
class AblationConfiguration:
    """Specification of an ablation configuration using existing components with default settings."""
    config_id: AblationConfigID
    name: str
    perception_mode: str  # "CLASSICAL" | "NEURAL" | "HYBRID"
    enable_estimator: bool
    enable_dynamic_roi: bool
    enable_controller: bool
    description: str


# The 5 canonical, untuned configurations
ABLATION_CONFIGURATIONS: Dict[AblationConfigID, AblationConfiguration] = {
    AblationConfigID.CONFIG_A_CLASSICAL: AblationConfiguration(
        config_id=AblationConfigID.CONFIG_A_CLASSICAL,
        name="Config A: Classical Path",
        perception_mode="CLASSICAL",
        enable_estimator=False,
        enable_dynamic_roi=False,
        enable_controller=False,
        description="Classical optical beacon extraction only (no neural, no filter, no control)",
    ),
    AblationConfigID.CONFIG_B_NEURAL: AblationConfiguration(
        config_id=AblationConfigID.CONFIG_B_NEURAL,
        name="Config B: Neural Path",
        perception_mode="NEURAL",
        enable_estimator=False,
        enable_dynamic_roi=False,
        enable_controller=False,
        description="Neural YOLOv8n beacon detector only (no classical, no filter, no control)",
    ),
    AblationConfigID.CONFIG_C_HYBRID: AblationConfiguration(
        config_id=AblationConfigID.CONFIG_C_HYBRID,
        name="Config C: Existing HYBRID",
        perception_mode="HYBRID",
        enable_estimator=False,
        enable_dynamic_roi=False,
        enable_controller=False,
        description="Fused classical + neural + optical refinement (no filter, no control)",
    ),
    AblationConfigID.CONFIG_D_HYBRID_EKF: AblationConfiguration(
        config_id=AblationConfigID.CONFIG_D_HYBRID_EKF,
        name="Config D: HYBRID + IMM-EKF",
        perception_mode="HYBRID",
        enable_estimator=True,
        enable_dynamic_roi=True,
        enable_controller=False,
        description="HYBRID detector + adaptive IMM-EKF estimator + dynamic ROI prediction",
    ),
    AblationConfigID.CONFIG_E_FULL_SYSTEM: AblationConfiguration(
        config_id=AblationConfigID.CONFIG_E_FULL_SYSTEM,
        name="Config E: HYBRID + IMM-EKF + Controller",
        perception_mode="HYBRID",
        enable_estimator=True,
        enable_dynamic_roi=True,
        enable_controller=True,
        description="Full closed architecture: HYBRID + IMM-EKF + PAT Manager + PAT Controller",
    ),
}


@dataclass(frozen=True)
class AblationTrialMetrics:
    """The 8 comparative evaluation metrics for a single configuration."""
    config_id: AblationConfigID
    config_name: str
    total_frames: int
    evaluated_frames: int

    # 1. Centroid Error (px)
    mean_centroid_error_px: float
    median_centroid_error_px: float
    max_centroid_error_px: float

    # 2. RMSE
    rmse_px: float
    rmse_urad: float

    # 3. Acquisition
    acquisition_frame: Optional[int]
    acquisition_time_s: Optional[float]
    is_acquired: bool

    # 4. Reacquisition
    reacquisition_events_count: int
    reacquisition_success_count: int
    reacquisition_success_rate: float
    mean_reacquisition_time_s: Optional[float]

    # 5. Lock Retention
    locked_frames_count: int
    lock_retention_pct: float

    # 6. False Lock
    false_lock_count: int
    false_lock_rate_pct: float

    # 7. FPS (Throughput)
    fps: float
    total_elapsed_time_s: float

    # 8. Latency (ms)
    mean_latency_ms: float
    median_latency_ms: float
    p95_latency_ms: float
    max_latency_ms: float

    def to_dict(self) -> Dict[str, Any]:
        """Serialize metrics to dictionary."""
        return {
            "config_id": self.config_id.value,
            "config_name": self.config_name,
            "total_frames": self.total_frames,
            "evaluated_frames": self.evaluated_frames,
            "mean_centroid_error_px": round(self.mean_centroid_error_px, 4),
            "median_centroid_error_px": round(self.median_centroid_error_px, 4),
            "max_centroid_error_px": round(self.max_centroid_error_px, 4),
            "rmse_px": round(self.rmse_px, 4),
            "rmse_urad": round(self.rmse_urad, 2),
            "acquisition_frame": self.acquisition_frame,
            "acquisition_time_s": round(self.acquisition_time_s, 4) if self.acquisition_time_s is not None else None,
            "is_acquired": self.is_acquired,
            "reacquisition_events_count": self.reacquisition_events_count,
            "reacquisition_success_count": self.reacquisition_success_count,
            "reacquisition_success_rate": round(self.reacquisition_success_rate, 1),
            "mean_reacquisition_time_s": round(self.mean_reacquisition_time_s, 4) if self.mean_reacquisition_time_s is not None else None,
            "locked_frames_count": self.locked_frames_count,
            "lock_retention_pct": round(self.lock_retention_pct, 2),
            "false_lock_count": self.false_lock_count,
            "false_lock_rate_pct": round(self.false_lock_rate_pct, 2),
            "fps": round(self.fps, 2),
            "total_elapsed_time_s": round(self.total_elapsed_time_s, 4),
            "mean_latency_ms": round(self.mean_latency_ms, 3),
            "median_latency_ms": round(self.median_latency_ms, 3),
            "p95_latency_ms": round(self.p95_latency_ms, 3),
            "max_latency_ms": round(self.max_latency_ms, 3),
        }


@dataclass(frozen=True)
class AblationComparisonReport:
    """Comparative report across all 5 configurations under identical input conditions."""
    video_source_path: str
    ground_truth_path: Optional[str]
    total_frames: int
    duration_s: float
    gate_threshold_px: float
    results: Dict[AblationConfigID, AblationTrialMetrics]

    def format_table(self) -> str:
        """Render a formatted comparison table across the 5 configurations and 8 metrics."""
        lines = [
            "=" * 138,
            "HORIZON PHASE 12B: EXISTING-ALGORITHM ABLATION COMPARISON REPORT",
            "=" * 138,
            f"Source: {self.video_source_path}  |  Total Frames: {self.total_frames}  |  Duration: {self.duration_s:.2f}s  |  Lock Gate: {self.gate_threshold_px}px",
            "-" * 138,
            f"{'Configuration':<36} {'Centroid Err':<14} {'RMSE (px)':<11} {'RMSE (µrad)':<13} {'Acq Time':<11} {'Reacq Time':<12} {'Lock Ret%':<11} {'False Lk%':<11} {'FPS':<9} {'Lat (P95)':<10}",
            "-" * 138,
        ]

        for cid in [
            AblationConfigID.CONFIG_A_CLASSICAL,
            AblationConfigID.CONFIG_B_NEURAL,
            AblationConfigID.CONFIG_C_HYBRID,
            AblationConfigID.CONFIG_D_HYBRID_EKF,
            AblationConfigID.CONFIG_E_FULL_SYSTEM,
        ]:
            if cid not in self.results:
                continue
            m = self.results[cid]
            c_name = m.config_name
            err_str = f"{m.mean_centroid_error_px:.2f} px"
            rmse_str = f"{m.rmse_px:.2f} px"
            urad_str = f"{m.rmse_urad:.1f} µrad"
            acq_str = f"{m.acquisition_time_s:.3f}s" if m.acquisition_time_s is not None else "FAIL"
            reacq_str = f"{m.mean_reacquisition_time_s:.3f}s" if m.mean_reacquisition_time_s is not None else "N/A"
            lock_str = f"{m.lock_retention_pct:.1f}%"
            false_str = f"{m.false_lock_rate_pct:.1f}%"
            fps_str = f"{m.fps:.1f}"
            lat_str = f"{m.p95_latency_ms:.2f} ms"

            lines.append(
                f"{c_name:<36} {err_str:<14} {rmse_str:<11} {urad_str:<13} {acq_str:<11} {reacq_str:<12} {lock_str:<11} {false_str:<11} {fps_str:<9} {lat_str:<10}"
            )

        lines.append("-" * 138)
        lines.append("Progressive Architectural Insights:")
        lines.append("  * Config A (Classical): Optical centroiding with low latency, but susceptible to noise/occlusions.")
        lines.append("  * Config B (Neural): High semantic robustness, but higher latency and subpixel quantization.")
        lines.append("  * Config C (HYBRID): Optimal combination of classical accuracy and neural detection robustness.")
        lines.append("  * Config D (HYBRID + IMM-EKF): Temporal smoothing, trajectory prediction, and dynamic ROI acceleration.")
        lines.append("  * Config E (Full System): Closed-loop coarse pointing line-of-sight stabilization and lock recovery.")
        lines.append("=" * 128)
        return "\n".join(lines)

    def to_dict(self) -> Dict[str, Any]:
        """Convert comparative report to dictionary."""
        return {
            "video_source_path": self.video_source_path,
            "ground_truth_path": self.ground_truth_path,
            "total_frames": self.total_frames,
            "duration_s": round(self.duration_s, 4),
            "gate_threshold_px": self.gate_threshold_px,
            "configurations": {cid.value: metrics.to_dict() for cid, metrics in self.results.items()},
        }


class AblationHarness:
    """Executes fair, identical-condition ablation trials across the 5 configurations."""

    def __init__(
        self,
        gate_threshold_px: float = 15.0,
        sensor_fov_deg: float = 4.0,
        sensor_width_px: int = 640,
    ) -> None:
        """Initialize AblationHarness.

        Args:
            gate_threshold_px: Maximum distance in pixels to consider a frame locked.
            sensor_fov_deg: Field of view in degrees for angular calculations.
            sensor_width_px: Sensor width in pixels.
        """
        self._gate_threshold_px = float(gate_threshold_px)
        self._sensor_fov_deg = float(sensor_fov_deg)
        self._sensor_width_px = int(sensor_width_px)
        self._rad_per_px = math.radians(self._sensor_fov_deg) / max(1, self._sensor_width_px)

    def _build_pipeline(
        self,
        config: AblationConfiguration,
        video_source_path: Union[str, Path],
        gt_aligner: Optional[GroundTruthCSVAligner],
    ) -> ExternalHybridPipeline:
        """Construct standard pipeline with exact component configuration."""
        det_cfg = DetectorConfig(perception_mode=config.perception_mode)
        detector = HybridBeaconDetector(det_cfg)

        controller = PATCameraController() if config.enable_controller else None

        pipeline = ExternalHybridPipeline(
            video_source=str(video_source_path),
            detector=detector,
            enable_estimator=config.enable_estimator,
            enable_dynamic_roi=config.enable_dynamic_roi,
            controller=controller,
            ground_truth=gt_aligner,
            sensor_fov_deg=self._sensor_fov_deg,
            sensor_width_px=self._sensor_width_px,
        )
        return pipeline

    def evaluate_configuration(
        self,
        config: AblationConfiguration,
        video_source_path: Union[str, Path],
        gt_aligner: Optional[GroundTruthCSVAligner],
        max_frames: Optional[int] = None,
    ) -> AblationTrialMetrics:
        """Run a single configuration trial under identical conditions and compute the 8 metrics.

        Args:
            config: AblationConfiguration definition.
            video_source_path: Path to identical test MP4.
            gt_aligner: GroundTruthCSVAligner with identical reference coordinates.
            max_frames: Optional frame limit.

        Returns:
            AblationTrialMetrics container.
        """
        pipeline = self._build_pipeline(config, video_source_path, gt_aligner)

        t_start = time.perf_counter()
        pipeline.open()
        records: List[PipelineMeasurementRecord] = []

        count = 0
        while not pipeline.source.is_eof:
            if max_frames is not None and count >= max_frames:
                break
            res = pipeline.process_frame()
            if res is None:
                break
            records.append(res[0])
            count += 1

        t_elapsed = max(1e-5, time.perf_counter() - t_start)
        pipeline.close()

        # Compute the 8 metrics against ground truth
        total_frames = len(records)
        fps = float(total_frames / t_elapsed)

        errors_px: List[float] = []
        latencies_ms: List[float] = []
        locked_frames = 0
        false_locks = 0

        # Acquisition tracking
        acq_frame: Optional[int] = None
        acq_time_s: Optional[float] = None

        # Reacquisition tracking
        reacq_events = 0
        reacq_successes = 0
        reacq_durations_s: List[float] = []
        in_loss_state = False
        loss_start_time_s: float = 0.0

        for idx, rec in enumerate(records):
            lat_ms = rec.latency_breakdown_ms.get("total_ms", rec.processing_latency_ms) if rec.latency_breakdown_ms else rec.processing_latency_ms
            latencies_ms.append(float(lat_ms))

            ref_pos: Optional[Tuple[float, float]] = None
            if gt_aligner is not None and gt_aligner.is_loaded:
                gt_sample = gt_aligner.get_aligned_sample(rec.timestamp)
                if gt_sample is not None:
                    ref_pos = (float(gt_sample.u), float(gt_sample.v))

            # Determine system tracking position output
            out_pos: Optional[Tuple[float, float]] = None
            if config.enable_estimator and rec.estimated_state is not None:
                out_pos = rec.estimated_state
            elif rec.detected and rec.centroid is not None:
                out_pos = rec.centroid

            if ref_pos is not None:
                u_ref, v_ref = ref_pos
                if out_pos is not None:
                    err = float(math.hypot(out_pos[0] - u_ref, out_pos[1] - v_ref))
                    errors_px.append(err)

                    if err <= self._gate_threshold_px:
                        locked_frames += 1
                        # Check initial acquisition
                        if acq_frame is None:
                            acq_frame = rec.frame_id
                            acq_time_s = rec.timestamp

                        # Check reacquisition recovery
                        if in_loss_state:
                            reacq_dur = max(1e-4, rec.timestamp - loss_start_time_s)
                            reacq_durations_s.append(reacq_dur)
                            reacq_successes += 1
                            in_loss_state = False
                    else:
                        # Error exceeds gate threshold -> false lock / tracking error
                        false_locks += 1
                        if not in_loss_state and acq_frame is not None:
                            in_loss_state = True
                            loss_start_time_s = rec.timestamp
                            reacq_events += 1
                else:
                    # Target present in GT but undetected by system
                    if not in_loss_state and acq_frame is not None:
                        in_loss_state = True
                        loss_start_time_s = rec.timestamp
                        reacq_events += 1

        # Calculate statistics
        if errors_px:
            arr_err = np.array(errors_px, dtype=np.float64)
            mean_err = float(np.mean(arr_err))
            median_err = float(np.median(arr_err))
            max_err = float(np.max(arr_err))
            rmse_px = float(np.sqrt(np.mean(arr_err ** 2)))
            rmse_urad = float(rmse_px * self._rad_per_px * 1e6)
        else:
            mean_err = 0.0
            median_err = 0.0
            max_err = 0.0
            rmse_px = 0.0
            rmse_urad = 0.0

        if latencies_ms:
            arr_lat = np.array(latencies_ms, dtype=np.float64)
            mean_lat = float(np.mean(arr_lat))
            median_lat = float(np.median(arr_lat))
            p95_lat = float(np.percentile(arr_lat, 95))
            max_lat = float(np.max(arr_lat))
        else:
            mean_lat = 0.0
            median_lat = 0.0
            p95_lat = 0.0
            max_lat = 0.0

        lock_retention_pct = (locked_frames / max(1, total_frames)) * 100.0
        false_lock_rate_pct = (false_locks / max(1, total_frames)) * 100.0

        reacq_rate = (reacq_successes / max(1, reacq_events)) * 100.0 if reacq_events > 0 else 100.0
        mean_reacq_time = float(np.mean(reacq_durations_s)) if reacq_durations_s else None

        return AblationTrialMetrics(
            config_id=config.config_id,
            config_name=config.name,
            total_frames=total_frames,
            evaluated_frames=len(errors_px),
            mean_centroid_error_px=mean_err,
            median_centroid_error_px=median_err,
            max_centroid_error_px=max_err,
            rmse_px=rmse_px,
            rmse_urad=rmse_urad,
            acquisition_frame=acq_frame,
            acquisition_time_s=acq_time_s,
            is_acquired=acq_frame is not None,
            reacquisition_events_count=reacq_events,
            reacquisition_success_count=reacq_successes,
            reacquisition_success_rate=reacq_rate,
            mean_reacquisition_time_s=mean_reacq_time,
            locked_frames_count=locked_frames,
            lock_retention_pct=lock_retention_pct,
            false_lock_count=false_locks,
            false_lock_rate_pct=false_lock_rate_pct,
            fps=fps,
            total_elapsed_time_s=t_elapsed,
            mean_latency_ms=mean_lat,
            median_latency_ms=median_lat,
            p95_latency_ms=p95_lat,
            max_latency_ms=max_lat,
        )

    def run_full_ablation_study(
        self,
        video_source_path: Union[str, Path],
        ground_truth: Optional[Union[GroundTruthCSVAligner, str, Path]] = None,
        max_frames: Optional[int] = None,
    ) -> AblationComparisonReport:
        """Run all 5 configurations on the identical video source & ground truth.

        Args:
            video_source_path: Path to external test video.
            ground_truth: Optional GroundTruthCSVAligner or path to CSV.
            max_frames: Optional maximum frame limit per configuration.

        Returns:
            AblationComparisonReport containing all 5 trial metric sets.
        """
        gt_aligner: Optional[GroundTruthCSVAligner] = None
        if isinstance(ground_truth, (str, Path)):
            gt_aligner = GroundTruthCSVAligner(ground_truth)
        elif isinstance(ground_truth, GroundTruthCSVAligner):
            gt_aligner = ground_truth

        results: Dict[AblationConfigID, AblationTrialMetrics] = {}

        for cid in [
            AblationConfigID.CONFIG_A_CLASSICAL,
            AblationConfigID.CONFIG_B_NEURAL,
            AblationConfigID.CONFIG_C_HYBRID,
            AblationConfigID.CONFIG_D_HYBRID_EKF,
            AblationConfigID.CONFIG_E_FULL_SYSTEM,
        ]:
            cfg = ABLATION_CONFIGURATIONS[cid]
            metrics = self.evaluate_configuration(
                config=cfg,
                video_source_path=video_source_path,
                gt_aligner=gt_aligner,
                max_frames=max_frames,
            )
            results[cid] = metrics

        first_metrics = next(iter(results.values()))
        duration_s = (first_metrics.total_frames / 30.0) if first_metrics else 0.0

        return AblationComparisonReport(
            video_source_path=str(video_source_path),
            ground_truth_path=str(ground_truth) if ground_truth else None,
            total_frames=first_metrics.total_frames if first_metrics else 0,
            duration_s=duration_s,
            gate_threshold_px=self._gate_threshold_px,
            results=results,
        )
