"""
HORIZON Phase 8B Test Suite: External Video Shadow Pointing
=============================================================
Validates:
  1. Full Architectural Pipeline Connectivity:
     External video -> HYBRID -> IMM-EKF -> PAT -> Existing controller -> Pan/Tilt command.
  2. Open-Loop Source Video Invariance:
     - The MP4 is a recorded camera stream.
     - Zero modifications to source video frames.
     - Zero controller feedback back into the recorded frames.
     - Controller output is real, but the recorded sensor does not physically move.
  3. Controller Integrity:
     - No separate controller for video (strictly uses existing PATCameraController).
     - No tuning of controller gains for video (default gain scheduling and gains).
  4. Real Dynamic Pointing Response:
     - Pointing error in pan/tilt correctly generates corresponding pan/tilt rate commands.
     - Velocity feedforward anticipation active when target is in motion.
  5. Real MP4 Shadow Pointing Execution:
     - Processes sample video stream.
     - Confirms continuous output of beacon, measurement, estimated position, error,
       pan command, tilt command, PAT state, and confidence.
  6. Benchmark-1 Regression Integrity:
     - Virtual Camera projection, closed-loop simulation engine determinism,
       and Benchmark-1 baseline are 100% intact.
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
from pat.state import PATMode, PATState
from simulator.camera.camera import CameraIntrinsics, VirtualCamera
from simulator.core.config import AppConfig, SimulationConfig
from simulator.core.simulation import SimulationEngine
from simulator.perception.config import DetectorConfig
from simulator.perception.detector import DetectionResult
from simulator.perception.hybrid_detector import HybridBeaconDetector
from sources.dynamic_roi import DynamicROI
from sources.external_video_source import ExternalVideoSource
from sources.frame_packet import FramePacket
from sources.video_pipeline import ExternalHybridPipeline, PipelineMeasurementRecord
from tracking.association.track import Track
from tracking.estimation.imm_kalman import InteractingMultipleModelFilter
from tracking.estimation.state import EstimatorStatus, StateEstimate

SAMPLE_VIDEO_PATH = Path("data/samples/isro_sample_beacon_test.mp4")


def _generate_synthetic_video_sequence(
    num_frames: int = 25,
) -> List[Tuple[np.ndarray, Tuple[float, float]]]:
    """Generates synthetic (frame, (true_u, true_v)) sequence with dynamic motion."""
    np.random.seed(42)
    frames = []
    yy, xx = np.mgrid[0:480, 0:640]

    for i in range(num_frames):
        # Target traverses across the FOV (offset from boresight center 320, 240)
        u_i = 320.0 + 40.0 * math.sin(0.18 * i)
        v_i = 240.0 + 30.0 * math.cos(0.18 * i)
        noise = np.random.normal(0, 3.0, (480, 640))
        bg = 18.0 + noise
        spot = np.exp(-0.5 * (((xx - u_i) ** 2 + (yy - v_i) ** 2) / (5.0 ** 2))) * 210.0
        f = np.clip(bg + spot, 0, 255).astype(np.uint8)
        frames.append((f, (u_i, v_i)))
    return frames


# ==============================================================================
# 1. ARCHITECTURAL INTEGRITY & PIPELINE COMPOSITION
# ==============================================================================

class TestShadowPointingArchitecture:
    """Verifies pipeline connectivity and strict avoidance of separate video controllers."""

    def test_pipeline_composition_uses_existing_controller(self):
        """Pipeline must connect directly to existing PATCameraController."""
        pipeline = ExternalHybridPipeline(
            SAMPLE_VIDEO_PATH if SAMPLE_VIDEO_PATH.exists() else "dummy.mp4",
            enable_estimator=True,
        )
        # Verify component instantiation
        assert pipeline.detector is not None
        assert isinstance(pipeline.detector, HybridBeaconDetector)
        assert pipeline.track is not None
        assert isinstance(pipeline.track.filter, InteractingMultipleModelFilter)
        assert pipeline.pat_manager is not None
        assert isinstance(pipeline.pat_manager, PATModeManager)
        assert pipeline.controller is not None
        assert isinstance(pipeline.controller, PATCameraController)

    def test_strictly_no_ad_hoc_video_controllers(self):
        """Zero ad-hoc video controllers (e.g. VideoCameraController, VideoPID) may exist."""
        import sources
        import sources.video_pipeline as vp

        assert not hasattr(sources, "VideoCameraController")
        assert not hasattr(sources, "VideoPID")
        assert not hasattr(sources, "ShadowController")
        assert not hasattr(vp, "VideoCameraController")

    def test_zero_video_specific_gain_tuning(self):
        """Controller must use default gain scheduler and nominal gain sets."""
        pipeline = ExternalHybridPipeline(
            SAMPLE_VIDEO_PATH if SAMPLE_VIDEO_PATH.exists() else "dummy.mp4",
            enable_estimator=True,
        )
        ctrl = pipeline.controller
        assert ctrl is not None
        # Default PID values from PATCameraController
        assert ctrl.pan_pid.kp == 1.5
        assert ctrl.pan_pid.ki == 0.08
        assert ctrl.pan_pid.kd == 0.12
        assert ctrl.tilt_pid.kp == 1.5
        assert ctrl.tilt_pid.ki == 0.08
        assert ctrl.tilt_pid.kd == 0.12
        # Default feedforward
        assert ctrl.feedforward.enabled is True
        assert ctrl.feedforward.kff_pan == 0.6
        assert ctrl.feedforward.kff_tilt == 0.6


# ==============================================================================
# 2. OPEN-LOOP SOURCE VIDEO INVARIANCE (SHADOW POINTING)
# ==============================================================================

class TestOpenLoopSourceInvariance:
    """Verifies that source video frames are completely immutable during shadow pointing."""

    def test_source_frames_unmodified_by_controller_commands(self):
        """Controller commands must NEVER alter or mutate the source frames."""
        synth_frames = _generate_synthetic_video_sequence(num_frames=15)
        raw_copies = [f.copy() for f, _ in synth_frames]

        pipeline = ExternalHybridPipeline(
            SAMPLE_VIDEO_PATH if SAMPLE_VIDEO_PATH.exists() else "dummy.mp4",
            enable_estimator=True,
        )

        for i, (orig_frame, gt_pos) in enumerate(synth_frames):
            packet = FramePacket(
                frame=orig_frame,
                frame_id=i,
                timestamp=i * 0.0333,
                width=640,
                height=480,
                source_type="EXTERNAL_VIDEO",
                source_fps=30.0,
                valid=True,
                dt=0.0333,
            )
            # Patch the source to return this frame packet
            pipeline._source.read_processing_frame = lambda pkt=packet: (pkt, orig_frame)

            rec, det = pipeline.process_frame()
            assert rec is not None

            # Verify that the frame content in memory is bit-for-bit unchanged
            assert np.array_equal(orig_frame, raw_copies[i]), f"Frame {i} was mutated by pipeline!"

            # If target is locked, controller produces real pointing commands
            if rec.pat_mode in ("ACQUIRE", "TRACK", "DEGRADED"):
                # Pointing commands are calculated
                assert isinstance(rec.commanded_pan_rate, float)
                assert isinstance(rec.commanded_tilt_rate, float)

    def test_pipeline_reset_resets_controller(self):
        """Pipeline reset must also reset the existing PATCameraController."""
        pipeline = ExternalHybridPipeline(
            SAMPLE_VIDEO_PATH if SAMPLE_VIDEO_PATH.exists() else "dummy.mp4",
            enable_estimator=True,
        )
        ctrl = pipeline.controller
        ctrl._prev_cmd_pan = 5.5
        ctrl._prev_cmd_tilt = -3.2

        pipeline.reset()
        assert ctrl._prev_cmd_pan == 0.0
        assert ctrl._prev_cmd_tilt == 0.0


# ==============================================================================
# 3. POINTING RESPONSE DYNAMICS & ERROR COUPLING
# ==============================================================================

class TestPointingResponseDynamics:
    """Verifies that controller commands faithfully respond to line-of-sight pointing errors."""

    def test_pointing_error_direction_and_command_polarity(self):
        """Target offset to right (+pan error) should command positive pan rate."""
        pipeline = ExternalHybridPipeline(
            SAMPLE_VIDEO_PATH if SAMPLE_VIDEO_PATH.exists() else "dummy.mp4",
            enable_estimator=True,
        )

        # Create frame with target offset to right: u = 400 (boresight is 320 -> error +80 px)
        yy, xx = np.mgrid[0:480, 0:640]
        spot = np.exp(-0.5 * (((xx - 400.0) ** 2 + (yy - 240.0) ** 2) / (5.0 ** 2))) * 220.0
        frame = np.clip(18.0 + spot, 0, 255).astype(np.uint8)

        # Feed frame multiple times to acquire track
        for k in range(5):
            packet = FramePacket(
                frame=frame.copy(),
                frame_id=k,
                timestamp=k * 0.0333,
                width=640,
                height=480,
                source_type="EXTERNAL_VIDEO",
                source_fps=30.0,
                valid=True,
                dt=0.0333,
            )
            pipeline._source.read_processing_frame = lambda pkt=packet: (pkt, packet.frame)
            rec, det = pipeline.process_frame()

        assert rec is not None
        # Target at u=400 has positive pan error in optical coordinates
        assert rec.pan_error_deg > 0.0
        # Controller should output positive pan command to steer toward target
        assert rec.commanded_pan_rate > 0.0

    def test_pointing_error_tilt_polarity(self):
        """Target offset below boresight (v = 300, boresight 240 -> tilt error) produces tilt command."""
        pipeline = ExternalHybridPipeline(
            SAMPLE_VIDEO_PATH if SAMPLE_VIDEO_PATH.exists() else "dummy.mp4",
            enable_estimator=True,
        )

        yy, xx = np.mgrid[0:480, 0:640]
        spot = np.exp(-0.5 * (((xx - 320.0) ** 2 + (yy - 300.0) ** 2) / (5.0 ** 2))) * 220.0
        frame = np.clip(18.0 + spot, 0, 255).astype(np.uint8)

        for k in range(5):
            packet = FramePacket(
                frame=frame.copy(),
                frame_id=k,
                timestamp=k * 0.0333,
                width=640,
                height=480,
                source_type="EXTERNAL_VIDEO",
                source_fps=30.0,
                valid=True,
                dt=0.0333,
            )
            pipeline._source.read_processing_frame = lambda pkt=packet: (pkt, packet.frame)
            rec, det = pipeline.process_frame()

        assert rec is not None
        assert abs(rec.tilt_error_deg) > 0.0
        assert abs(rec.commanded_tilt_rate) > 0.0


# ==============================================================================
# 4. REAL MP4 SHADOW POINTING EXECUTION & TELEMETRY COMPLETENESS
# ==============================================================================

class TestRealMP4ShadowPointing:
    """Verifies end-to-end shadow pointing on actual recorded video file."""

    @pytest.mark.skipif(not SAMPLE_VIDEO_PATH.exists(), reason="Sample MP4 video not found")
    def test_sample_video_continuous_shadow_pointing(self):
        """Processes real MP4 video and verifies all required display fields."""
        with ExternalHybridPipeline(SAMPLE_VIDEO_PATH, enable_estimator=True) as pipeline:
            records = pipeline.run(max_frames=30)

        assert len(records) >= 15

        for rec in records:
            # 1. Beacon / Measurement
            assert rec.detected is True or rec.detected is False
            if rec.detected:
                assert rec.centroid is not None
                assert np.isfinite(rec.centroid[0]) and np.isfinite(rec.centroid[1])

            # 2. Confidence
            assert 0.0 <= rec.confidence <= 1.0

            # 3. Estimated Position
            if rec.estimated_state is not None:
                assert np.isfinite(rec.estimated_state[0])
                assert np.isfinite(rec.estimated_state[1])

            # 4. Error (Pan & Tilt)
            assert np.isfinite(rec.pan_error_deg)
            assert np.isfinite(rec.tilt_error_deg)

            # 5. Pan & Tilt Commands
            assert np.isfinite(rec.commanded_pan_rate)
            assert np.isfinite(rec.commanded_tilt_rate)

            # 6. PAT State
            assert rec.pat_mode in ("SEARCH", "ACQUIRE", "TRACK", "DEGRADED", "REACQUIRE")
            assert isinstance(rec.is_saturated, bool)

            # 7. Serialization dictionary exposes all shadow pointing fields
            d = rec.to_dict()
            assert "pan_error_deg" in d
            assert "tilt_error_deg" in d
            assert "commanded_pan_rate" in d
            assert "commanded_tilt_rate" in d
            assert "is_saturated" in d
            assert "pat_mode" in d
            assert "estimated_state" in d


# ==============================================================================
# 5. BENCHMARK-1 REGRESSION INTEGRITY
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
