"""
HORIZON Phase 16B: Final External Video Benchmark Harness
=========================================================
Executes the unified, end-to-end External Video pipeline across evaluator-style MP4s.

Telemetry Dimensions Collected for Every Video:
  INPUT:
    - filename, resolution, source FPS, duration, total frames, codec
  PERCEPTION:
    - centroid, confidence, measurement quality (SNR, circularity, flux, contrast), uncertainty
  ESTIMATION:
    - state, velocity, covariance, innovation, innovation Mahalanobis distance, model probabilities
  PAT:
    - acquisition, track, degraded, reacquire mode states, timeouts, and transitions
  CONTROL:
    - pan error (deg), tilt error (deg), commanded rates (deg/s), saturation flags
  PERFORMANCE:
    - centroiding error, RMSE (px & urad) where valid reference exists, acquisition time,
      reacquisition time, lock retention %, FPS throughput, latency breakdown (mean, median, P95, P99, max)
  FAILURES:
    - frame_id, timestamp, failure reason, recovery behavior

Official-Reference Rule Invariant:
  - If ISRO / official reference coordinates are provided, they are parsed and utilized directly.
  - Zero substitution of HORIZON's own estimate as ground truth.
  - If no reference is provided, metrics requiring reference data are marked strictly as UNAVAILABLE.
  - Zero fabricated reference data.

No Special Cases Invariant:
  - Zero video-specific code, zero trajectory-specific code, zero noise-specific code,
    zero frame-number-specific code, zero seed-specific code.
  - Every MP4 executes through the identical pipeline architecture.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import datetime
import json
import logging
import math
from pathlib import Path
import time
from typing import Any, Dict, List, Optional, Tuple, Union
import numpy as np

from simulator.perception.config import DetectorConfig
from sources.csv_aligner import GroundTruthCSVAligner
from sources.error_budget import ErrorBudgetSummary
from sources.failure_forensics import FailureEvent
from sources.run_manifest import (
    HORIZON_VERSION,
    Benchmark2RunManager,
    Benchmark2RunManifest,
    generate_benchmark2_artifacts,
)
from sources.video_pipeline import ExternalHybridPipeline, PipelineMeasurementRecord

logger = logging.getLogger(__name__)


# ==============================================================================
# Final Benchmark Data Structures
# ==============================================================================

@dataclass
class VideoBenchmarkResult:
    """Consolidated benchmark evaluation result for a single external MP4 sensor recording."""
    # Input
    filename: str
    video_path: str
    video_hash: str
    resolution: Tuple[int, int]
    source_fps: float
    duration_s: float
    total_frames: int
    codec: str

    # Reference Status
    has_official_reference: bool
    reference_source: Optional[str]

    # Performance Metrics
    processed_frames: int
    detected_frames: int
    lock_retention_pct: float
    mean_centroid_error_px: Optional[float]
    rmse_px: Optional[float]
    rmse_urad: Optional[float]
    acquisition_time_s: Optional[float]
    reacquisition_time_s: Optional[float]
    throughput_fps: float

    # Latency Percentiles (ms)
    latency_mean_ms: float
    latency_median_ms: float
    latency_p95_ms: float
    latency_p99_ms: float
    latency_max_ms: float

    # Failures & Forensics
    failure_count: int
    failure_events: List[Dict[str, Any]] = field(default_factory=list)

    # Generated Artifacts
    artifact_paths: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "input": {
                "filename": self.filename,
                "video_path": self.video_path,
                "video_hash": self.video_hash,
                "resolution": list(self.resolution),
                "source_fps": self.source_fps,
                "duration_s": self.duration_s,
                "total_frames": self.total_frames,
                "codec": self.codec,
            },
            "reference": {
                "has_official_reference": self.has_official_reference,
                "reference_source": self.reference_source or "NONE (Metrics requiring reference marked UNAVAILABLE)",
            },
            "performance": {
                "processed_frames": self.processed_frames,
                "detected_frames": self.detected_frames,
                "lock_retention_pct": round(self.lock_retention_pct, 2),
                "mean_centroid_error_px": round(self.mean_centroid_error_px, 4) if self.mean_centroid_error_px is not None else "UNAVAILABLE (No official reference provided)",
                "rmse_px": round(self.rmse_px, 4) if self.rmse_px is not None else "UNAVAILABLE (No official reference provided)",
                "rmse_urad": round(self.rmse_urad, 2) if self.rmse_urad is not None else "UNAVAILABLE (No official reference provided)",
                "acquisition_time_s": round(self.acquisition_time_s, 4) if self.acquisition_time_s is not None else None,
                "reacquisition_time_s": round(self.reacquisition_time_s, 4) if self.reacquisition_time_s is not None else None,
                "throughput_fps": round(self.throughput_fps, 2),
            },
            "latency_ms": {
                "mean": round(self.latency_mean_ms, 2),
                "median": round(self.latency_median_ms, 2),
                "p95": round(self.latency_p95_ms, 2),
                "p99": round(self.latency_p99_ms, 2),
                "max": round(self.latency_max_ms, 2),
            },
            "failures": {
                "failure_count": self.failure_count,
                "events": self.failure_events,
            },
            "artifacts": self.artifact_paths,
        }


@dataclass
class FinalExternalBenchmarkReport:
    """Comprehensive evaluation report across all evaluated external video streams."""
    timestamp: str
    total_videos_evaluated: int
    results: List[VideoBenchmarkResult] = field(default_factory=list)

    def format_overview_table(self) -> str:
        """Render a formatted overview table across all evaluated MP4 sensor recordings."""
        lines = [
            "=" * 132,
            "HORIZON PHASE 16B: FINAL EXTERNAL VIDEO BENCHMARK EVALUATION REPORT",
            "=" * 132,
            f"Evaluation Time: {self.timestamp}  |  Total Video Streams: {self.total_videos_evaluated}  |  Software: HORIZON v{HORIZON_VERSION}",
            "Official Reference Rule: Reference coordinates used where legitimately provided; zero fabrication or self-substitution.",
            "-" * 132,
            "Video Filename            Resolution   FPS   Frames   Lock Ret%   RMSE (px)      RMSE (µrad)    FPS      Lat(P95)   Failures  Status",
            "-" * 132,
        ]

        for res in self.results:
            res_str = f"{res.resolution[0]}x{res.resolution[1]}"
            rmse_px_str = f"{res.rmse_px:.3f} px" if res.rmse_px is not None else "UNAVAILABLE*"
            rmse_urad_str = f"{res.rmse_urad:.1f} µrad" if res.rmse_urad is not None else "UNAVAILABLE*"
            status = "VERIFIED" if res.lock_retention_pct >= 90.0 else ("DEGRADED" if res.lock_retention_pct >= 50.0 else "FAILURE")

            line = (
                f"{res.filename:<24} "
                f"{res_str:<12} "
                f"{res.source_fps:<5.1f} "
                f"{res.total_frames:<8} "
                f"{res.lock_retention_pct:>6.1f}%     "
                f"{rmse_px_str:<14} "
                f"{rmse_urad_str:<14} "
                f"{res.throughput_fps:>6.1f}   "
                f"{res.latency_p95_ms:>6.2f} ms   "
                f"{res.failure_count:<9} "
                f"{status}"
            )
            lines.append(line)

        lines.extend([
            "-" * 132,
            "* UNAVAILABLE: Official reference trajectory not provided for this stream. No ground-truth was fabricated.",
            "=" * 132,
        ])
        return "\n".join(lines)


# ==============================================================================
# Final External Video Benchmark Evaluator
# ==============================================================================

class FinalExternalVideoBenchmark:
    """Executes the standard, un-branched HORIZON pipeline across external MP4 recordings."""

    def __init__(
        self,
        runs_output_dir: Union[str, Path] = "benchmark_runs",
        sensor_fov_deg: float = 4.0,
        sensor_width_px: int = 640,
    ) -> None:
        self._runs_output_dir = Path(runs_output_dir).resolve()
        self._sensor_fov_deg = float(sensor_fov_deg)
        self._sensor_width_px = int(sensor_width_px)
        self._run_manager = Benchmark2RunManager(
            runs_root=self._runs_output_dir,
            sensor_fov_deg=self._sensor_fov_deg,
            sensor_width_px=self._sensor_width_px,
        )

    def evaluate_video(
        self,
        video_path: Union[str, Path],
        ground_truth_path: Optional[Union[str, Path]] = None,
        max_frames: Optional[int] = None,
        run_id: Optional[str] = None,
        allow_overwrite: bool = True,
    ) -> VideoBenchmarkResult:
        """Run standard pipeline on a single external MP4 video without special branching.

        Args:
            video_path: Path to external MP4 file.
            ground_truth_path: Optional path to official reference CSV.
            max_frames: Optional frame limit.
            run_id: Optional run ID.
            allow_overwrite: Whether to allow overwriting output artifacts.

        Returns:
            VideoBenchmarkResult containing complete multi-dimensional metrics.
        """
        vid_p = Path(video_path).resolve()
        if not vid_p.is_file():
            raise FileNotFoundError(f"External MP4 file not found: {vid_p}")

        # Check for matching official reference CSV if not explicitly passed
        gt_file: Optional[Path] = None
        if ground_truth_path is not None:
            candidate_gt = Path(ground_truth_path).resolve()
            if candidate_gt.is_file():
                gt_file = candidate_gt
        else:
            # Check default pairing conventions: <name>_gt.csv or <name>_reference.csv
            possible_gts = [
                vid_p.with_name(f"{vid_p.stem}_gt.csv"),
                vid_p.with_name(f"{vid_p.stem}_reference.csv"),
                vid_p.with_suffix(".csv"),
            ]
            for p in possible_gts:
                if p.is_file():
                    gt_file = p
                    break

        has_ref = gt_file is not None

        # Execute using standard Benchmark2RunManager
        manifest, records, paths = self._run_manager.execute_benchmark_run(
            video_path=vid_p,
            detector_config=DetectorConfig(perception_mode="HYBRID"),
            enable_estimator=True,
            enable_dynamic_roi=True,
            ground_truth=gt_file if has_ref else None,
            max_frames=max_frames,
            run_id=run_id,
            allow_overwrite=allow_overwrite,
        )

        res_dict = manifest.results
        failures_summary = []
        # Harvest forensic failures if recorded
        for r in records:
            if hasattr(r, "forensic_event") and r.forensic_event is not None:
                failures_summary.append({
                    "frame_id": r.frame_id,
                    "timestamp": r.timestamp,
                    "failure_reason": r.forensic_event.category.value if hasattr(r.forensic_event, "category") else "UNKNOWN",
                    "recovery_behavior": r.forensic_event.recovery_strategy if hasattr(r.forensic_event, "recovery_strategy") else "DEFAULT_REACQUIRE",
                })

        return VideoBenchmarkResult(
            filename=vid_p.name,
            video_path=str(vid_p),
            video_hash=manifest.video_metadata.get("video_hash", "UNKNOWN"),
            resolution=tuple(manifest.video_metadata.get("resolution", (640, 480))),
            source_fps=manifest.video_metadata.get("source_fps", 30.0),
            duration_s=manifest.video_metadata.get("duration_seconds", 0.0),
            total_frames=manifest.video_metadata.get("total_frames", len(records)),
            codec=manifest.video_metadata.get("codec", "UNKNOWN"),
            has_official_reference=has_ref,
            reference_source=str(gt_file) if gt_file else None,
            processed_frames=res_dict.get("total_frames", len(records)),
            detected_frames=res_dict.get("detected_frames", 0),
            lock_retention_pct=res_dict.get("lock_retention_pct", 0.0),
            mean_centroid_error_px=res_dict.get("mean_centroid_error_px") if has_ref else None,
            rmse_px=res_dict.get("rmse_px") if has_ref else None,
            rmse_urad=res_dict.get("rmse_urad") if has_ref else None,
            acquisition_time_s=res_dict.get("acquisition_time_s"),
            reacquisition_time_s=res_dict.get("reacquisition_time_s"),
            throughput_fps=res_dict.get("fps", 0.0),
            latency_mean_ms=res_dict.get("mean_latency_ms", 0.0),
            latency_median_ms=res_dict.get("median_latency_ms", 0.0),
            latency_p95_ms=res_dict.get("p95_latency_ms", 0.0),
            latency_p99_ms=res_dict.get("p99_latency_ms", 0.0),
            latency_max_ms=res_dict.get("max_latency_ms", 0.0),
            failure_count=len(failures_summary),
            failure_events=failures_summary,
            artifact_paths={k: str(v) for k, v in paths.items()},
        )

    def evaluate_all_videos(
        self,
        video_paths: List[Union[str, Path]],
        ground_truth_map: Optional[Dict[str, Union[str, Path]]] = None,
        max_frames_per_video: Optional[int] = None,
    ) -> FinalExternalBenchmarkReport:
        """Run benchmark evaluation across a batch of external MP4 videos.

        Args:
            video_paths: List of paths to target MP4 videos.
            ground_truth_map: Optional mapping of video filename/path to reference CSV path.
            max_frames_per_video: Optional frame limit per video.

        Returns:
            FinalExternalBenchmarkReport summarizing results.
        """
        gt_map = ground_truth_map or {}
        results: List[VideoBenchmarkResult] = []

        for v_path in video_paths:
            p = Path(v_path)
            gt_p = gt_map.get(p.name) or gt_map.get(str(p))
            res = self.evaluate_video(
                video_path=p,
                ground_truth_path=gt_p,
                max_frames=max_frames_per_video,
            )
            results.append(res)

        return FinalExternalBenchmarkReport(
            timestamp=datetime.datetime.now().isoformat(),
            total_videos_evaluated=len(results),
            results=results,
        )
