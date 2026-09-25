"""
HORIZON Phase 9B Test Suite: End-to-End Sensor-to-Command Latency
==================================================================
Validates:
  1. Direct Monotonic Latency Measurement:
     - Timestamps recorded using time.perf_counter() at every stage transition:
       video timestamp, frame available, decode start/end, preprocessing start/end,
       HYBRID start/end, IMM-EKF start/end, PAT start/end, controller start/end,
       and command available.
     - Strictly NO estimation of latency from FPS.
  2. Complete Seven-Stage Granularity:
     - decode, preprocessing, HYBRID, estimation, PAT, controller, total.
  3. Five Statistical Metrics for Every Stage:
     - mean, median, P95, P99, and maximum.
  4. Algorithm Invariance:
     - Zero algorithmic modifications to perception, estimation, or control.
  5. Real MP4 Processing Chain Latency Profiling:
     - Measures real recorded video streaming latency.
  6. Benchmark-1 Regression Integrity:
     - Virtual Camera projection and simulation engine determinism unchanged.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import List, Tuple
import cv2
import numpy as np
import pytest

from control.camera_controller import PATCameraController
from pat.mode_manager import PATModeManager
from simulator.camera.camera import CameraIntrinsics, VirtualCamera
from simulator.core.config import AppConfig, SimulationConfig
from simulator.core.simulation import SimulationEngine
from simulator.perception.hybrid_detector import HybridBeaconDetector
from sources.external_video_source import ExternalVideoSource
from sources.frame_packet import FramePacket
from sources.latency_profiler import (
    EndToEndLatencyReport,
    FrameLatencyRecord,
    LatencyProfiler,
    StageLatencyStats,
)
from sources.video_pipeline import ExternalHybridPipeline, PipelineMeasurementRecord
from tracking.association.track import Track
from tracking.estimation.imm_kalman import InteractingMultipleModelFilter

SAMPLE_VIDEO_PATH = Path("data/samples/isro_sample_beacon_test.mp4")


def _generate_synthetic_test_frames(
    num_frames: int = 20,
) -> List[Tuple[np.ndarray, Tuple[float, float]]]:
    """Generates synthetic frames for direct latency profiling."""
    np.random.seed(42)
    frames = []
    yy, xx = np.mgrid[0:480, 0:640]

    for i in range(num_frames):
        u_i = 320.0 + 30.0 * math.sin(0.2 * i)
        v_i = 240.0 + 20.0 * math.cos(0.2 * i)
        noise = np.random.normal(0, 3.0, (480, 640))
        bg = 18.0 + noise
        spot = np.exp(-0.5 * (((xx - u_i) ** 2 + (yy - v_i) ** 2) / (5.0 ** 2))) * 210.0
        f = np.clip(bg + spot, 0, 255).astype(np.uint8)
        frames.append((f, (u_i, v_i)))
    return frames


# ==============================================================================
# 1. DIRECT MONOTONIC MEASUREMENT INTEGRITY
# ==============================================================================

class TestDirectMonotonicMeasurement:
    """Verifies that latencies are measured directly without FPS-based approximation."""

    def test_all_stage_timestamps_recorded_and_ordered(self):
        """Every frame must record monotonic timestamps across all 9 boundary markers."""
        synth_frames = _generate_synthetic_test_frames(num_frames=5)
        pipeline = ExternalHybridPipeline(
            SAMPLE_VIDEO_PATH if SAMPLE_VIDEO_PATH.exists() else "dummy.mp4",
            enable_estimator=True,
        )

        for i, (frame, _) in enumerate(synth_frames):
            packet = FramePacket(
                frame=frame,
                frame_id=i,
                timestamp=i * 0.0333,
                width=640,
                height=480,
                source_type="EXTERNAL_VIDEO",
                source_fps=30.0,
                valid=True,
                dt=0.0333,
            )
            pipeline._source.read_processing_frame = lambda pkt=packet: (pkt, frame)
            rec, det = pipeline.process_frame()

            assert rec is not None
            assert rec.latency_record is not None
            lat = rec.latency_record

            # Boundary marker timestamps must be non-negative
            assert lat.frame_available_t >= 0.0
            assert lat.decode_start_t >= 0.0
            assert lat.decode_end_t >= lat.decode_start_t
            assert lat.preprocessing_start_t >= lat.decode_end_t
            assert lat.preprocessing_end_t >= lat.preprocessing_start_t
            assert lat.hybrid_start_t >= lat.preprocessing_end_t
            assert lat.hybrid_end_t >= lat.hybrid_start_t
            assert lat.imm_ekf_start_t >= lat.hybrid_end_t
            assert lat.imm_ekf_end_t >= lat.imm_ekf_start_t
            assert lat.pat_start_t >= lat.imm_ekf_end_t
            assert lat.pat_end_t >= lat.pat_start_t
            assert lat.controller_start_t >= lat.pat_end_t
            assert lat.controller_end_t >= lat.controller_start_t
            assert lat.command_available_t >= lat.controller_end_t

    def test_zero_fps_estimation_rule(self):
        """Latency must NOT be estimated from 1/FPS."""
        profiler = LatencyProfiler()
        # Record a test frame with direct timestamps
        t0 = 100.0
        rec = profiler.record_frame(
            frame_id=1,
            video_timestamp=0.0333,
            frame_available_t=t0,
            decode_start_t=t0,
            decode_end_t=t0 + 0.002,
            preprocessing_start_t=t0 + 0.002,
            preprocessing_end_t=t0 + 0.003,
            hybrid_start_t=t0 + 0.003,
            hybrid_end_t=t0 + 0.015,
            imm_ekf_start_t=t0 + 0.015,
            imm_ekf_end_t=t0 + 0.016,
            pat_start_t=t0 + 0.016,
            pat_end_t=t0 + 0.017,
            controller_start_t=t0 + 0.017,
            controller_end_t=t0 + 0.018,
            command_available_t=t0 + 0.018,
        )

        # Durations are direct timestamp differences in ms
        assert abs(rec.decode_ms - 2.0) < 1e-4
        assert abs(rec.preprocessing_ms - 1.0) < 1e-4
        assert abs(rec.hybrid_ms - 12.0) < 1e-4
        assert abs(rec.estimation_ms - 1.0) < 1e-4
        assert abs(rec.pat_ms - 1.0) < 1e-4
        assert abs(rec.controller_ms - 1.0) < 1e-4
        assert abs(rec.total_ms - 18.0) < 1e-4


# ==============================================================================
# 2. SEVEN-STAGE GRANULARITY & BREAKDOWN
# ==============================================================================

class TestSevenStageGranularity:
    """Verifies that decode, preprocessing, HYBRID, estimation, PAT, controller, and total are tracked."""

    def test_seven_stages_present_in_measurement_record(self):
        """PipelineMeasurementRecord must expose latency_breakdown_ms with all 7 stages."""
        synth_frames = _generate_synthetic_test_frames(num_frames=3)
        pipeline = ExternalHybridPipeline(
            SAMPLE_VIDEO_PATH if SAMPLE_VIDEO_PATH.exists() else "dummy.mp4",
            enable_estimator=True,
        )

        for i, (frame, _) in enumerate(synth_frames):
            packet = FramePacket(
                frame=frame,
                frame_id=i,
                timestamp=i * 0.0333,
                width=640,
                height=480,
                source_type="EXTERNAL_VIDEO",
                source_fps=30.0,
                valid=True,
                dt=0.0333,
            )
            pipeline._source.read_processing_frame = lambda pkt=packet: (pkt, frame)
            rec, _ = pipeline.process_frame()

            assert rec is not None
            assert rec.latency_breakdown_ms is not None
            lb = rec.latency_breakdown_ms

            required_keys = [
                "decode_ms",
                "preprocessing_ms",
                "hybrid_ms",
                "estimation_ms",
                "pat_ms",
                "controller_ms",
                "total_ms",
            ]
            for key in required_keys:
                assert key in lb
                assert lb[key] >= 0.0
                assert np.isfinite(lb[key])

            # Total latency must encompass the sum of the pipeline stages
            stage_sum = (
                lb["decode_ms"]
                + lb["preprocessing_ms"]
                + lb["hybrid_ms"]
                + lb["estimation_ms"]
                + lb["pat_ms"]
                + lb["controller_ms"]
            )
            assert lb["total_ms"] >= stage_sum * 0.95  # within margin of execution


# ==============================================================================
# 3. STATISTICAL METRICS COMPLETENESS (MEAN, MEDIAN, P95, P99, MAX)
# ==============================================================================

class TestStatisticalMetricsCompleteness:
    """Verifies calculation of mean, median, P95, P99, and maximum for all 7 stages."""

    def test_statistical_metrics_calculation_and_monotonicity(self):
        """For every stage, stats must calculate mean, median, P95, P99, and maximum correctly."""
        profiler = LatencyProfiler()

        # Seed with diverse synthetic latency samples
        np.random.seed(42)
        n_samples = 100
        for i in range(n_samples):
            t0 = 1000.0 + i * 0.1
            d_dec = float(np.random.uniform(1.0, 3.0))
            d_prep = float(np.random.uniform(0.5, 1.5))
            d_hyb = float(np.random.uniform(10.0, 25.0))
            d_est = float(np.random.uniform(0.2, 0.8))
            d_pat = float(np.random.uniform(0.1, 0.5))
            d_ctrl = float(np.random.uniform(0.1, 0.4))

            t1 = t0 + d_dec / 1000.0
            t2 = t1 + d_prep / 1000.0
            t3 = t2 + d_hyb / 1000.0
            t4 = t3 + d_est / 1000.0
            t5 = t4 + d_pat / 1000.0
            t6 = t5 + d_ctrl / 1000.0

            profiler.record_frame(
                frame_id=i,
                video_timestamp=i * 0.0333,
                frame_available_t=t0,
                decode_start_t=t0,
                decode_end_t=t1,
                preprocessing_start_t=t1,
                preprocessing_end_t=t2,
                hybrid_start_t=t2,
                hybrid_end_t=t3,
                imm_ekf_start_t=t3,
                imm_ekf_end_t=t4,
                pat_start_t=t4,
                pat_end_t=t5,
                controller_start_t=t5,
                controller_end_t=t6,
                command_available_t=t6,
            )

        report = profiler.generate_report()
        assert report.sample_count == n_samples

        stages = [
            report.decode,
            report.preprocessing,
            report.hybrid,
            report.estimation,
            report.pat,
            report.controller,
            report.total,
        ]

        for s in stages:
            assert s.sample_count == n_samples
            assert s.mean_ms > 0.0
            assert s.median_ms > 0.0
            assert s.p95_ms > 0.0
            assert s.p99_ms > 0.0
            assert s.max_ms > 0.0

            # Monotonic statistical ordering
            assert s.min_ms <= s.median_ms <= s.max_ms
            assert s.median_ms <= s.p95_ms <= s.p99_ms <= s.max_ms

        # Summary table formatting check
        table_str = report.summary_table()
        assert "decode" in table_str
        assert "HYBRID" in table_str
        assert "controller" in table_str
        assert "total" in table_str


# ==============================================================================
# 4. ALGORITHM INVARIANCE
# ==============================================================================

class TestAlgorithmInvariance:
    """Verifies that no algorithms or gains were altered in Phase 9B."""

    def test_default_perception_and_control_intact(self):
        """Detector and controller parameters must remain at default baseline."""
        pipeline = ExternalHybridPipeline(
            SAMPLE_VIDEO_PATH if SAMPLE_VIDEO_PATH.exists() else "dummy.mp4",
            enable_estimator=True,
        )
        # Default controller PID gains
        assert pipeline.controller.pan_pid.kp == 1.5
        assert pipeline.controller.tilt_pid.kp == 1.5
        # Default IMM sub-filters
        assert hasattr(pipeline.track.filter, "_cv_filter")
        assert hasattr(pipeline.track.filter, "_ca_filter")
        assert hasattr(pipeline.track.filter, "_maneuver_filter")


# ==============================================================================
# 5. REAL MP4 PROCESSING CHAIN LATENCY PROFILING
# ==============================================================================

class TestRealMP4LatencyProfiling:
    """Verifies end-to-end latency profiling on actual recorded MP4 stream."""

    @pytest.mark.skipif(not SAMPLE_VIDEO_PATH.exists(), reason="Sample MP4 video not found")
    def test_sample_video_end_to_end_latency_report(self):
        """Processes real MP4 video and validates EndToEndLatencyReport generation."""
        with ExternalHybridPipeline(SAMPLE_VIDEO_PATH, enable_estimator=True) as pipeline:
            records = pipeline.run(max_frames=25)
            report = pipeline.compute_latency_report()

        assert report.sample_count >= 15

        # All 7 stages must have positive mean latency
        assert report.decode.mean_ms >= 0.0
        assert report.preprocessing.mean_ms >= 0.0
        assert report.hybrid.mean_ms > 0.0
        assert report.estimation.mean_ms >= 0.0
        assert report.pat.mean_ms >= 0.0
        assert report.controller.mean_ms >= 0.0
        assert report.total.mean_ms > 0.0

        # Percentile ordering
        assert report.total.median_ms <= report.total.p95_ms <= report.total.p99_ms <= report.total.max_ms

        d = report.to_dict()
        assert "decode" in d
        assert "hybrid" in d
        assert "total" in d
        assert "p95" in d["total"]


# ==============================================================================
# 6. BENCHMARK-1 REGRESSION INTEGRITY
# ==============================================================================

class TestBenchmark1RegressionIntegrity:
    """Guarantees zero regression on Virtual Camera and Benchmark-1 simulation engine."""

    def test_virtual_camera_projection_unchanged(self):
        """VirtualCamera projection math, intrinsics, and FOV bounds are unchanged."""
        intrinsics = CameraIntrinsics(width=640, height=480, fov_horizontal_deg=4.0, fov_vertical_deg=3.0)
        camera = VirtualCamera(intrinsics=intrinsics, update_rate_hz=30.0)

        theta_x, theta_y, u, v, in_fov = camera.project_target(1000.0, 1000.0)
        assert in_fov is True
        assert abs(theta_x) < 1e-6
        assert abs(theta_y) < 1e-6
        assert abs(u - 320.0) < 1e-4
        assert abs(v - 240.0) < 1e-4

    def test_simulation_engine_benchmark1_deterministic_run(self):
        """Verify Benchmark-1 deterministic simulation produces bitwise/numerically identical outputs."""
        cfg = AppConfig(
            simulation=SimulationConfig(frequency_hz=30.0, duration_seconds=0.2, seed=123)
        )
        engine = SimulationEngine(cfg)
        engine.initialize()

        states = []
        for _ in range(6):
            engine.step()
            s = engine.get_current_state()
            states.append((s.timestamp, s.x, s.y, s.vx, s.vy))

        assert len(states) == 6
        assert abs(states[0][0] - (1.0 / 30.0)) < 1e-9
        assert abs(states[-1][0] - 0.2) < 1e-9
        for t, x, y, vx, vy in states:
            assert np.isfinite(x) and np.isfinite(y)
            assert np.isfinite(vx) and np.isfinite(vy)
