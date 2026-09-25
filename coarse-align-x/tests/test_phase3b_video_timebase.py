"""
HORIZON Phase 3B: External Video Authoritative Timebase & Pipeline Flow Test Suite
==================================================================================
Validates:
  1. Source-correct timing: Video timestamp is authoritative (never UI or wall-clock).
  2. For 30 FPS, dt = 1/30s dynamically derived; container PTS preserved.
  3. Frame processing sequence:
       video frame -> processing -> HYBRID -> estimator -> PAT -> controller output -> then frame k+1.
  4. No duplicate processing, duplicate timestamps, silent duplication, or hidden skipping.
  5. Frame drops are explicitly detected, counted, and logged.
  6. Real-time metrics: source FPS, processing FPS, frame ID, timestamp, dt,
                        dropped frames, decode latency, processing latency.
  7. Virtual Camera timing and Benchmark-1 regression integrity unchanged.
"""

from __future__ import annotations

import math
from pathlib import Path
import numpy as np
import pytest

from sources.video_timebase import VideoFrameTiming, VideoTimebase
from sources.video_geometry import TransformationMethod, VideoGeometryTransformer
from sources.external_video_source import ExternalVideoSource
from sources.frame_packet import FramePacket
from simulator.perception.hybrid_detector import HybridBeaconDetector
from simulator.perception.config import HybridDetectorConfig
from tracking.association.track import Track
from pat.mode_manager import PATModeManager
from control.camera_controller import PATCameraController
from simulator.camera.camera import VirtualCamera
from simulator.camera.intrinsics import CameraIntrinsics
from simulator.core.config import AppConfig, SimulationConfig
from simulator.core.simulation import SimulationEngine


SAMPLE_VIDEO_PATH = Path("data/samples/isro_sample_beacon_test.mp4")


# ==============================================================================
# 1. Authoritative Timebase Derivation & Dynamic dt
# ==============================================================================
class TestVideoTimebaseDerivation:
    """Verify source-correct dynamic timing derivation."""

    def test_30fps_dynamic_dt(self) -> None:
        """A 30 FPS source dynamically derives dt ~ 1/30 s (never hard-coded)."""
        tb = VideoTimebase(source_fps=30.0, total_frames=100)
        assert math.isclose(tb.nominal_dt, 1.0 / 30.0, rel_tol=1e-6)

        # Step through consecutive frames without container PTS (fallback mode)
        for k in range(5):
            timing = tb.compute_frame_timing(raw_frame_id=k, container_pos_msec=None, decode_duration_ms=1.5)
            assert timing.frame_id == k
            expected_t = k * (1.0 / 30.0)
            assert math.isclose(timing.timestamp, expected_t, abs_tol=1e-7)
            assert math.isclose(timing.dt, 1.0 / 30.0, rel_tol=1e-6)
            assert not timing.is_dropped
            assert timing.cumulative_dropped_frames == 0

    def test_60fps_dynamic_dt(self) -> None:
        """A 60 FPS source dynamically derives dt ~ 1/60 s."""
        tb = VideoTimebase(source_fps=60.0, total_frames=200)
        assert math.isclose(tb.nominal_dt, 1.0 / 60.0, rel_tol=1e-6)

        timing0 = tb.compute_frame_timing(raw_frame_id=0, container_pos_msec=None)
        timing1 = tb.compute_frame_timing(raw_frame_id=1, container_pos_msec=None)
        assert math.isclose(timing1.dt, 1.0 / 60.0, rel_tol=1e-6)
        assert math.isclose(timing1.timestamp - timing0.timestamp, 1.0 / 60.0, rel_tol=1e-6)

    def test_preserve_container_presentation_timestamps(self) -> None:
        """When container PTS exists, timebase preserves it authoritatively."""
        tb = VideoTimebase(source_fps=30.0)
        container_pts_ms = [0.0, 33.3333, 66.6667, 100.0000, 133.3333]

        for k, pts in enumerate(container_pts_ms):
            timing = tb.compute_frame_timing(raw_frame_id=k, container_pos_msec=pts)
            expected_t = pts / 1000.0
            if k == 0:
                assert timing.timestamp == 0.0
                assert math.isclose(timing.dt, 1.0 / 30.0, rel_tol=1e-4)
            else:
                assert math.isclose(timing.timestamp, expected_t, abs_tol=1e-5)
                expected_dt = (pts - container_pts_ms[k - 1]) / 1000.0
                assert math.isclose(timing.dt, expected_dt, abs_tol=1e-5)

    def test_rejection_of_duplicate_timestamps(self) -> None:
        """Duplicate PTS values are rejected, guaranteeing dt > 0 strictly advancing."""
        tb = VideoTimebase(source_fps=30.0)
        # Frame 0 and Frame 1 have identical container timestamp 50.0 ms
        t0 = tb.compute_frame_timing(raw_frame_id=0, container_pos_msec=50.0)
        t1 = tb.compute_frame_timing(raw_frame_id=1, container_pos_msec=50.0)

        assert t1.timestamp > t0.timestamp
        assert t1.dt > 0.0
        assert math.isclose(t1.dt, 1.0 / 30.0, rel_tol=1e-4)


# ==============================================================================
# 2. Frame Drop Detection & Continuity Validation
# ==============================================================================
class TestFrameDropDetection:
    """Verify that gaps in frame sequence are detected, logged, and counted."""

    def test_consecutive_frames_zero_drops(self) -> None:
        """Consecutive frames produce 0 dropped frames."""
        tb = VideoTimebase(source_fps=30.0)
        for i in range(10):
            timing = tb.compute_frame_timing(raw_frame_id=i)
            assert not timing.is_dropped
            assert timing.cumulative_dropped_frames == 0

    def test_detect_single_gap_drop(self) -> None:
        """A gap from frame 3 to frame 6 must report 2 dropped frames."""
        tb = VideoTimebase(source_fps=30.0)
        tb.compute_frame_timing(raw_frame_id=0)
        tb.compute_frame_timing(raw_frame_id=1)
        tb.compute_frame_timing(raw_frame_id=2)
        timing_pre = tb.compute_frame_timing(raw_frame_id=3)
        assert timing_pre.cumulative_dropped_frames == 0

        # Jump from frame 3 to frame 6 (frames 4 and 5 were dropped by source)
        timing_gap = tb.compute_frame_timing(raw_frame_id=6)
        assert timing_gap.is_dropped is True
        assert timing_gap.dropped_count_step == 2
        assert timing_gap.cumulative_dropped_frames == 2
        assert tb.cumulative_dropped_frames == 2

    def test_multiple_gaps_accumulation(self) -> None:
        """Multiple drops accumulate accurately."""
        tb = VideoTimebase(source_fps=30.0)
        tb.compute_frame_timing(raw_frame_id=0)
        tb.compute_frame_timing(raw_frame_id=5)   # Dropped 4 (1,2,3,4)
        assert tb.cumulative_dropped_frames == 4
        tb.compute_frame_timing(raw_frame_id=6)   # Normal step
        assert tb.cumulative_dropped_frames == 4
        tb.compute_frame_timing(raw_frame_id=10)  # Dropped 3 (7,8,9)
        assert tb.cumulative_dropped_frames == 7


# ==============================================================================
# 3. Sequential Pipeline Processing Flow (Frame k -> Frame k+1)
# ==============================================================================
class TestSequentialPipelineFlow:
    """Verify Frame k: video frame -> processing -> HYBRID -> estimator -> PAT -> controller."""

    def test_end_to_end_frame_sequence(self) -> None:
        """Execute full sequence for frame k and verify state advancement before k+1."""
        # Setup pipeline components
        geom_transformer = VideoGeometryTransformer(1280, 720, proc_width=640, proc_height=480)
        detector = HybridBeaconDetector()
        tracker = Track(track_id=1, filter_type="IMM_ADAPTIVE_EKF")
        pat_mgr = PATModeManager()
        controller = PATCameraController(controller_type="PID")
        timebase = VideoTimebase(source_fps=30.0)

        # Create two consecutive synthetic frames
        frame_k = np.zeros((720, 1280), dtype=np.uint8)
        frame_k[360, 640] = 255  # Beacon at center
        frame_k1 = np.zeros((720, 1280), dtype=np.uint8)
        frame_k1[362, 642] = 255  # Beacon moved 2 px

        # Process Frame k
        timing_k = timebase.compute_frame_timing(raw_frame_id=0)
        proc_k = geom_transformer.transform_frame(frame_k)
        det_k = detector.detect(proc_k, timestamp=timing_k.timestamp, collect_diagnostics=False)
        meas_orig_k = geom_transformer.processing_to_original(*det_k.centroid) if det_k.detected else None
        est_k = tracker.step(measurement=meas_orig_k, confidence=det_k.confidence, timestamp=timing_k.timestamp)
        pat_k = pat_mgr.process_step(
            dt=timing_k.dt,
            timestamp_s=timing_k.timestamp,
            detection_valid=det_k.detected,
            detection_confidence=det_k.confidence,
            mahalanobis_d2=est_k.mahalanobis_distance**2,
            covariance_trace=float(est_k.position_uncertainty**2),
            estimated_u_px=est_k.estimated_x,
            estimated_v_px=est_k.estimated_y,
            estimated_vx_px_s=est_k.estimated_vx,
            estimated_vy_px_s=est_k.estimated_vy,
            current_pan_deg=0.0,
            current_tilt_deg=0.0,
        )
        pan_k, tilt_k, _, _, _, _, _ = controller.compute_control_command(
            dt=timing_k.dt,
            pat_state=pat_k,
            search_pan_rate=0.0,
            search_tilt_rate=0.0,
            reacquire_pan_rate=0.0,
            reacquire_tilt_rate=0.0,
            estimated_vx_px_s=est_k.estimated_vx,
            estimated_vy_px_s=est_k.estimated_vy,
        )

        assert timing_k.frame_id == 0
        assert np.isfinite(pan_k) and np.isfinite(tilt_k)

        # Process Frame k+1 (strictly sequential)
        timing_k1 = timebase.compute_frame_timing(raw_frame_id=1)
        proc_k1 = geom_transformer.transform_frame(frame_k1)
        det_k1 = detector.detect(proc_k1, timestamp=timing_k1.timestamp, collect_diagnostics=False)
        meas_orig_k1 = geom_transformer.processing_to_original(*det_k1.centroid) if det_k1.detected else None
        est_k1 = tracker.step(measurement=meas_orig_k1, confidence=det_k1.confidence, timestamp=timing_k1.timestamp)
        pat_k1 = pat_mgr.process_step(
            dt=timing_k1.dt,
            timestamp_s=timing_k1.timestamp,
            detection_valid=det_k1.detected,
            detection_confidence=det_k1.confidence,
            mahalanobis_d2=est_k1.mahalanobis_distance**2,
            covariance_trace=float(est_k1.position_uncertainty**2),
            estimated_u_px=est_k1.estimated_x,
            estimated_v_px=est_k1.estimated_y,
            estimated_vx_px_s=est_k1.estimated_vx,
            estimated_vy_px_s=est_k1.estimated_vy,
            current_pan_deg=0.0,
            current_tilt_deg=0.0,
        )
        pan_k1, tilt_k1, _, _, _, _, _ = controller.compute_control_command(
            dt=timing_k1.dt,
            pat_state=pat_k1,
            search_pan_rate=0.0,
            search_tilt_rate=0.0,
            reacquire_pan_rate=0.0,
            reacquire_tilt_rate=0.0,
            estimated_vx_px_s=est_k1.estimated_vx,
            estimated_vy_px_s=est_k1.estimated_vy,
        )

        assert timing_k1.frame_id == 1
        assert timing_k1.timestamp > timing_k.timestamp
        assert math.isclose(timing_k1.dt, 1.0 / 30.0, rel_tol=1e-4)


# ==============================================================================
# 4. Performance Metrics Tracking
# ==============================================================================
class TestPerformanceMetricsTracking:
    """Verify tracking of FPS, dt, frame IDs, dropped frames, and latencies."""

    def test_latency_recording_and_fps_estimation(self) -> None:
        """Verify recording of decode & processing latencies and FPS throughput."""
        tb = VideoTimebase(source_fps=30.0)

        # Simulate 10 frames with 2.0ms decode and 5.0ms processing
        for i in range(10):
            tb.compute_frame_timing(raw_frame_id=i, decode_duration_ms=2.0)
            tb.record_processing_latency(latency_ms=5.0)

        assert math.isclose(tb.get_average_decode_latency_ms(), 2.0, abs_tol=1e-3)
        assert math.isclose(tb.get_average_processing_latency_ms(), 5.0, abs_tol=1e-3)
        assert tb.get_processing_fps() > 0.0

    def test_frame_packet_timebase_attributes(self) -> None:
        """Verify FramePacket dataclass exposes authoritative dt and latency telemetry."""
        packet = FramePacket(
            frame=np.zeros((480, 640), dtype=np.uint8),
            frame_id=5,
            timestamp=0.16667,
            width=640,
            height=480,
            source_type="EXTERNAL_VIDEO",
            source_fps=30.0,
            valid=True,
            dt=0.033333,
            decode_latency_ms=1.8,
            processing_latency_ms=4.2,
            dropped_frames=0,
        )
        assert packet.dt == 0.033333
        assert packet.decode_latency_ms == 1.8
        assert packet.processing_latency_ms == 4.2
        assert packet.dropped_frames == 0


# ==============================================================================
# 5. ExternalVideoSource Timebase Integration
# ==============================================================================
class TestExternalVideoSourceTimebaseIntegration:
    """Verify ExternalVideoSource uses VideoTimebase for real MP4 playback."""

    def test_real_video_playback_authoritative_timing(self) -> None:
        """Read 10 frames from real sample MP4 and verify authoritative timing & dt."""
        if not SAMPLE_VIDEO_PATH.exists():
            pytest.skip(f"Sample video not found: {SAMPLE_VIDEO_PATH}")

        source = ExternalVideoSource(SAMPLE_VIDEO_PATH)
        assert source.open() is True
        assert source.timebase is not None

        prev_timestamp = -1.0
        for i in range(10):
            packet = source.read_frame()
            assert packet.valid is True
            assert packet.frame_id == i
            assert packet.timestamp > prev_timestamp
            assert packet.dt > 0.0
            # For 30 FPS video, dt should be approx 0.0333s
            assert math.isclose(packet.dt, 1.0 / source.fps, rel_tol=0.1)
            assert packet.decode_latency_ms >= 0.0
            assert packet.dropped_frames == 0
            prev_timestamp = packet.timestamp

        source.close()
        assert source.timebase is None

    def test_reset_and_seek_timebase_resynchronization(self) -> None:
        """Verify stream reset and seek cleanly resynchronize the timebase."""
        if not SAMPLE_VIDEO_PATH.exists():
            pytest.skip(f"Sample video not found: {SAMPLE_VIDEO_PATH}")

        source = ExternalVideoSource(SAMPLE_VIDEO_PATH)
        assert source.open() is True

        # Read 5 frames
        for _ in range(5):
            source.read_frame()
        assert source.frame_id == 5

        # Reset stream
        source.reset()
        assert source.frame_id == 0
        assert source.timebase.current_frame_id == 0
        assert source.timebase.cumulative_dropped_frames == 0

        # Seek to frame 15
        assert source.seek(15) is True
        assert source.frame_id == 15
        assert source.timebase.current_frame_id == 15

        source.close()


# ==============================================================================
# 6. Benchmark-1 Virtual Camera Regression Integrity
# ==============================================================================
class TestBenchmark1RegressionIntegrity:
    """Verify that Virtual Camera, projection, and simulation clock are 100% untouched."""

    def test_virtual_camera_clock_unchanged(self) -> None:
        """Virtual camera optical projection and intrinsics remain bitwise identical."""
        intrinsics = CameraIntrinsics(width=640, height=480, fov_horizontal_deg=4.0, fov_vertical_deg=3.0)
        camera = VirtualCamera(intrinsics=intrinsics, update_rate_hz=30.0)

        theta_x, theta_y, u, v, in_fov = camera.project_target(1000.0, 1000.0)
        assert in_fov is True
        assert abs(theta_x) < 1e-6
        assert abs(theta_y) < 1e-6
        assert abs(u - 320.0) < 1e-4
        assert abs(v - 240.0) < 1e-4

    def test_simulation_clock_step_regression(self) -> None:
        """SimulationEngine advances simulation clock deterministically independent of video."""
        cfg = AppConfig(simulation=SimulationConfig(duration_seconds=0.1, frequency_hz=30.0, seed=42))
        engine = SimulationEngine(cfg)
        engine.initialize()

        engine.step()
        assert math.isclose(engine.clock.current_time, 1.0 / 30.0, rel_tol=1e-6)
        assert math.isclose(engine.clock.dt, 1.0 / 30.0, rel_tol=1e-6)
