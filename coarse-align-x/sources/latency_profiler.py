"""
HORIZON Phase 9B: End-to-End Sensor-to-Command Latency Profiler
================================================================
Direct monotonic latency profiling across the complete coarse pointing chain:
  Video Timestamp / Frame Available
  ↓
  Decode (start/end)
  ↓
  Preprocessing (start/end)
  ↓
  HYBRID Perception (start/end)
  ↓
  IMM-EKF Estimation (start/end)
  ↓
  PAT Mode Manager (start/end)
  ↓
  Existing Controller (start/end)
  ↓
  Coarse Pointing Command Available

Strict Invariants:
  - Latency is measured directly using high-resolution monotonic clocks (time.perf_counter()).
  - Zero estimation of latency from FPS.
  - Zero modification to underlying algorithms to artificially improve metrics.
  - Precise metrics calculated: mean, median, P95, P99, and maximum for every stage.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import logging
from typing import Any, Dict, List, Optional
import numpy as np

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class FrameLatencyRecord:
    """Complete timestamp and duration record for a single sensor-to-command frame."""

    frame_id: int
    video_timestamp: float
    frame_available_t: float
    decode_start_t: float
    decode_end_t: float
    preprocessing_start_t: float
    preprocessing_end_t: float
    hybrid_start_t: float
    hybrid_end_t: float
    imm_ekf_start_t: float
    imm_ekf_end_t: float
    pat_start_t: float
    pat_end_t: float
    controller_start_t: float
    controller_end_t: float
    command_available_t: float

    # Stage durations in milliseconds (directly measured)
    decode_ms: float
    preprocessing_ms: float
    hybrid_ms: float
    estimation_ms: float
    pat_ms: float
    controller_ms: float
    total_ms: float

    def to_dict(self) -> Dict[str, Any]:
        """Convert record to dictionary of millisecond durations and raw timestamps."""
        return {
            "frame_id": self.frame_id,
            "video_timestamp": round(self.video_timestamp, 6),
            "timestamps": {
                "frame_available": round(self.frame_available_t, 6),
                "decode_start": round(self.decode_start_t, 6),
                "decode_end": round(self.decode_end_t, 6),
                "preprocessing_start": round(self.preprocessing_start_t, 6),
                "preprocessing_end": round(self.preprocessing_end_t, 6),
                "hybrid_start": round(self.hybrid_start_t, 6),
                "hybrid_end": round(self.hybrid_end_t, 6),
                "imm_ekf_start": round(self.imm_ekf_start_t, 6),
                "imm_ekf_end": round(self.imm_ekf_end_t, 6),
                "pat_start": round(self.pat_start_t, 6),
                "pat_end": round(self.pat_end_t, 6),
                "controller_start": round(self.controller_start_t, 6),
                "controller_end": round(self.controller_end_t, 6),
                "command_available": round(self.command_available_t, 6),
            },
            "durations_ms": {
                "decode": round(self.decode_ms, 3),
                "preprocessing": round(self.preprocessing_ms, 3),
                "hybrid": round(self.hybrid_ms, 3),
                "estimation": round(self.estimation_ms, 3),
                "pat": round(self.pat_ms, 3),
                "controller": round(self.controller_ms, 3),
                "total": round(self.total_ms, 3),
            },
        }


@dataclass(frozen=True)
class StageLatencyStats:
    """Statistical summary metrics for a specific pipeline stage."""

    stage_name: str
    sample_count: int
    mean_ms: float
    median_ms: float
    p95_ms: float
    p99_ms: float
    max_ms: float
    min_ms: float = 0.0
    std_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "stage_name": self.stage_name,
            "sample_count": self.sample_count,
            "mean": round(self.mean_ms, 3),
            "median": round(self.median_ms, 3),
            "p95": round(self.p95_ms, 3),
            "p99": round(self.p99_ms, 3),
            "maximum": round(self.max_ms, 3),
            "minimum": round(self.min_ms, 3),
            "std": round(self.std_ms, 3),
        }


@dataclass(frozen=True)
class EndToEndLatencyReport:
    """Comprehensive statistical report covering all 7 pipeline stages."""

    sample_count: int
    decode: StageLatencyStats
    preprocessing: StageLatencyStats
    hybrid: StageLatencyStats
    estimation: StageLatencyStats
    pat: StageLatencyStats
    controller: StageLatencyStats
    total: StageLatencyStats

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sample_count": self.sample_count,
            "decode": self.decode.to_dict(),
            "preprocessing": self.preprocessing.to_dict(),
            "hybrid": self.hybrid.to_dict(),
            "estimation": self.estimation.to_dict(),
            "pat": self.pat.to_dict(),
            "controller": self.controller.to_dict(),
            "total": self.total.to_dict(),
        }

    def summary_table(self) -> str:
        """Render a formatted ASCII/Markdown table of the latency metrics."""
        stages = [
            self.decode,
            self.preprocessing,
            self.hybrid,
            self.estimation,
            self.pat,
            self.controller,
            self.total,
        ]
        headers = ["Stage", "Mean (ms)", "Median (ms)", "P95 (ms)", "P99 (ms)", "Max (ms)"]
        rows = [
            f"| {s.stage_name:<14} | {s.mean_ms:>9.3f} | {s.median_ms:>11.3f} | {s.p95_ms:>8.3f} | {s.p99_ms:>8.3f} | {s.max_ms:>8.3f} |"
            for s in stages
        ]
        sep = "|----------------|-----------|-------------|----------|----------|----------|"
        header_str = f"| {headers[0]:<14} | {headers[1]:<9} | {headers[2]:<11} | {headers[3]:<8} | {headers[4]:<8} | {headers[5]:<8} |"
        return "\n".join([header_str, sep] + rows)


class LatencyProfiler:
    """Accumulates and computes statistical percentiles for real pipeline latencies."""

    def __init__(self) -> None:
        self._records: List[FrameLatencyRecord] = []

    @property
    def records(self) -> List[FrameLatencyRecord]:
        return list(self._records)

    @property
    def sample_count(self) -> int:
        return len(self._records)

    def reset(self) -> None:
        """Clear all recorded latency profiles."""
        self._records.clear()

    def record_frame(
        self,
        frame_id: int,
        video_timestamp: float,
        frame_available_t: float,
        decode_start_t: float,
        decode_end_t: float,
        preprocessing_start_t: float,
        preprocessing_end_t: float,
        hybrid_start_t: float,
        hybrid_end_t: float,
        imm_ekf_start_t: float,
        imm_ekf_end_t: float,
        pat_start_t: float,
        pat_end_t: float,
        controller_start_t: float,
        controller_end_t: float,
        command_available_t: float,
    ) -> FrameLatencyRecord:
        """Record and calculate stage durations directly from high-resolution monotonic timestamps.

        All durations are converted to milliseconds.
        """
        decode_ms = max(0.0, (decode_end_t - decode_start_t) * 1000.0)
        preprocessing_ms = max(0.0, (preprocessing_end_t - preprocessing_start_t) * 1000.0)
        hybrid_ms = max(0.0, (hybrid_end_t - hybrid_start_t) * 1000.0)
        estimation_ms = max(0.0, (imm_ekf_end_t - imm_ekf_start_t) * 1000.0)
        pat_ms = max(0.0, (pat_end_t - pat_start_t) * 1000.0)
        controller_ms = max(0.0, (controller_end_t - controller_start_t) * 1000.0)
        # Total latency is measured from the moment frame decode initiates to command availability
        total_ms = max(0.0, (command_available_t - decode_start_t) * 1000.0)

        record = FrameLatencyRecord(
            frame_id=frame_id,
            video_timestamp=video_timestamp,
            frame_available_t=frame_available_t,
            decode_start_t=decode_start_t,
            decode_end_t=decode_end_t,
            preprocessing_start_t=preprocessing_start_t,
            preprocessing_end_t=preprocessing_end_t,
            hybrid_start_t=hybrid_start_t,
            hybrid_end_t=hybrid_end_t,
            imm_ekf_start_t=imm_ekf_start_t,
            imm_ekf_end_t=imm_ekf_end_t,
            pat_start_t=pat_start_t,
            pat_end_t=pat_end_t,
            controller_start_t=controller_start_t,
            controller_end_t=controller_end_t,
            command_available_t=command_available_t,
            decode_ms=decode_ms,
            preprocessing_ms=preprocessing_ms,
            hybrid_ms=hybrid_ms,
            estimation_ms=estimation_ms,
            pat_ms=pat_ms,
            controller_ms=controller_ms,
            total_ms=total_ms,
        )
        self._records.append(record)
        return record

    def _compute_stats(self, values: np.ndarray, stage_name: str) -> StageLatencyStats:
        """Compute statistical summary (mean, median, P95, P99, max) directly from an array."""
        if len(values) == 0:
            return StageLatencyStats(
                stage_name=stage_name,
                sample_count=0,
                mean_ms=0.0,
                median_ms=0.0,
                p95_ms=0.0,
                p99_ms=0.0,
                max_ms=0.0,
                min_ms=0.0,
                std_ms=0.0,
            )

        mean_val = float(np.mean(values))
        median_val = float(np.median(values))
        p95_val = float(np.percentile(values, 95.0))
        p99_val = float(np.percentile(values, 99.0))
        max_val = float(np.max(values))
        min_val = float(np.min(values))
        std_val = float(np.std(values))

        return StageLatencyStats(
            stage_name=stage_name,
            sample_count=len(values),
            mean_ms=mean_val,
            median_ms=median_val,
            p95_ms=p95_val,
            p99_ms=p99_val,
            max_ms=max_val,
            min_ms=min_val,
            std_ms=std_val,
        )

    def generate_report(self) -> EndToEndLatencyReport:
        """Generate statistical metrics report across all 7 pipeline stages."""
        if not self._records:
            empty_stat = lambda name: self._compute_stats(np.array([]), name)
            return EndToEndLatencyReport(
                sample_count=0,
                decode=empty_stat("decode"),
                preprocessing=empty_stat("preprocessing"),
                hybrid=empty_stat("HYBRID"),
                estimation=empty_stat("estimation"),
                pat=empty_stat("PAT"),
                controller=empty_stat("controller"),
                total=empty_stat("total"),
            )

        decode_arr = np.array([r.decode_ms for r in self._records], dtype=np.float64)
        prep_arr = np.array([r.preprocessing_ms for r in self._records], dtype=np.float64)
        hybrid_arr = np.array([r.hybrid_ms for r in self._records], dtype=np.float64)
        est_arr = np.array([r.estimation_ms for r in self._records], dtype=np.float64)
        pat_arr = np.array([r.pat_ms for r in self._records], dtype=np.float64)
        ctrl_arr = np.array([r.controller_ms for r in self._records], dtype=np.float64)
        total_arr = np.array([r.total_ms for r in self._records], dtype=np.float64)

        return EndToEndLatencyReport(
            sample_count=len(self._records),
            decode=self._compute_stats(decode_arr, "decode"),
            preprocessing=self._compute_stats(prep_arr, "preprocessing"),
            hybrid=self._compute_stats(hybrid_arr, "HYBRID"),
            estimation=self._compute_stats(est_arr, "estimation"),
            pat=self._compute_stats(pat_arr, "PAT"),
            controller=self._compute_stats(ctrl_arr, "controller"),
            total=self._compute_stats(total_arr, "total"),
        )
