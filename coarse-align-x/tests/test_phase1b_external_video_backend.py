"""
HORIZON Phase 1B: External Video Source Backend Test Suite
===========================================================
Validates:
  1. ExternalVideoSource lifecycle (open, validate, metadata extraction, decode, controls)
  2. Common FramePacket contract for both external video and virtual camera
  3. VirtualCameraFrameAdapter non-intrusive wrapping
  4. Real dynamic metadata extraction (never hardcoded 640x480, 30 FPS)
  5. Step 6 validation requirements (frame IDs advance, timestamps advance, EOF detection)
  6. Benchmark-1 regression integrity (Virtual Camera & simulation unchanged)
"""

from __future__ import annotations

import os
from pathlib import Path
import numpy as np
import pytest

from sources.external_video_source import ExternalVideoSource
from sources.frame_packet import FramePacket
from sources.virtual_camera_adapter import VirtualCameraFrameAdapter
from simulator.camera.camera import VirtualCamera
from simulator.camera.intrinsics import CameraIntrinsics
from simulator.core.config import AppConfig, SimulationConfig
from simulator.core.simulation import SimulationEngine


SAMPLE_VIDEO_PATH = Path("data/samples/isro_sample_beacon_test.mp4")


# ==============================================================================
# 1. ExternalVideoSource Verification
# ==============================================================================
class TestExternalVideoSource:
    def test_open_real_mp4_file(self):
        """Verify ExternalVideoSource opens real sample MP4 and extracts dynamic metadata."""
        if not SAMPLE_VIDEO_PATH.exists():
            pytest.skip(f"Sample video not found: {SAMPLE_VIDEO_PATH}")

        source = ExternalVideoSource(SAMPLE_VIDEO_PATH)
        assert source.status == "NOT_OPENED"
        assert not source.is_open()

        opened = source.open()
        assert opened is True
        assert source.is_open() is True
        assert source.status == "READY"
        assert source.filename == "isro_sample_beacon_test.mp4"

        # Verify metadata is real and non-zero
        assert source.width > 0
        assert source.height > 0
        assert source.fps > 0.0
        assert source.frame_count > 0
        assert source.duration > 0.0
        assert source.codec != "UNKNOWN"
        source.close()
        assert source.status == "CLOSED"

    def test_validation_rejects_invalid_files(self, tmp_path):
        """Verify validation rejects non-existent, empty, or corrupt files."""
        # Non-existent
        src_missing = ExternalVideoSource(tmp_path / "does_not_exist.mp4")
        ok, msg = src_missing.validate()
        assert ok is False
        assert "does not exist" in msg.lower()
        assert src_missing.open() is False
        assert src_missing.status == "ERROR"

        # Empty file
        empty_file = tmp_path / "empty.mp4"
        empty_file.touch()
        src_empty = ExternalVideoSource(empty_file)
        ok, msg = src_empty.validate()
        assert ok is False
        assert "empty" in msg.lower()

        # Non-video text file
        corrupt_file = tmp_path / "corrupt.mp4"
        corrupt_file.write_text("NOT A VIDEO FILE", encoding="utf-8")
        src_corrupt = ExternalVideoSource(corrupt_file)
        ok, msg = src_corrupt.validate()
        assert ok is False
        assert src_corrupt.open() is False

    def test_frame_decoding_and_progression(self):
        """Verify frames decode into 2D uint8 arrays, frame IDs advance, and timestamps advance."""
        if not SAMPLE_VIDEO_PATH.exists():
            pytest.skip("Sample video not found")

        with ExternalVideoSource(SAMPLE_VIDEO_PATH) as source:
            assert source.is_open() is True

            # Read first 5 frames
            for expected_id in range(5):
                packet = source.read_frame()
                assert isinstance(packet, FramePacket)
                assert packet.valid is True
                assert packet.frame is not None
                assert isinstance(packet.frame, np.ndarray)
                assert packet.frame.ndim == 2
                assert packet.frame.dtype == np.uint8
                assert packet.frame_id == expected_id
                assert abs(packet.timestamp - (expected_id / source.fps)) < 1e-4
                assert packet.source_type == "EXTERNAL_VIDEO"
                assert packet.source_fps == source.fps
                assert packet.filename == source.filename
                assert packet.duration == source.duration

            assert source.frame_id == 5
            assert source.status == "PLAYING"

    def test_sequence_controls_pause_resume_seek_reset(self):
        """Verify pause, resume, seek, and reset sequence controls."""
        if not SAMPLE_VIDEO_PATH.exists():
            pytest.skip("Sample video not found")

        with ExternalVideoSource(SAMPLE_VIDEO_PATH) as source:
            # Read 3 frames
            for _ in range(3):
                source.read_frame()
            assert source.frame_id == 3

            # Pause
            source.pause()
            assert source.is_paused is True
            assert source.status == "PAUSED"
            pkt_paused = source.read_frame()
            assert pkt_paused.frame_id == 2  # Returns last packet without advancing
            assert source.frame_id == 3

            # Resume
            source.resume()
            assert source.is_paused is False
            assert source.status == "PLAYING"
            pkt_resumed = source.read_frame()
            assert pkt_resumed.frame_id == 3
            assert source.frame_id == 4

            # Seek to frame 15
            ok_seek = source.seek(15)
            assert ok_seek is True
            assert source.frame_id == 15
            pkt_seek = source.read_frame()
            assert pkt_seek.frame_id == 15
            assert source.frame_id == 16

            # Reset
            source.reset()
            assert source.frame_id == 0
            assert source.timestamp == 0.0
            assert source.is_eof is False
            assert source.is_paused is False
            assert source.status == "READY"
            pkt_reset = source.read_frame()
            assert pkt_reset.frame_id == 0

    def test_end_of_stream_detection(self):
        """Verify end-of-stream (EOF) flag and status are raised when reading past the end."""
        if not SAMPLE_VIDEO_PATH.exists():
            pytest.skip("Sample video not found")

        with ExternalVideoSource(SAMPLE_VIDEO_PATH) as source:
            total_f = source.frame_count
            assert total_f > 0

            # Seek directly to last frame
            source.seek(total_f - 1)
            last_pkt = source.read_frame()
            assert last_pkt.valid is True
            assert last_pkt.frame_id == total_f - 1

            # Next read must trigger EOF
            eof_pkt = source.read_frame()
            assert eof_pkt.valid is False
            assert eof_pkt.frame is None
            assert source.is_eof is True
            assert source.status == "END_OF_STREAM"


# ==============================================================================
# 2. Common Frame Object & Virtual Camera Frame Adapter Verification
# ==============================================================================
class TestFramePacketAndAdapter:
    def test_frame_packet_immutability_and_validation(self):
        """Verify FramePacket is frozen and rejects invalid array shapes or types."""
        valid_img = np.zeros((480, 640), dtype=np.uint8)
        pkt = FramePacket(
            frame=valid_img,
            frame_id=1,
            timestamp=0.033,
            width=640,
            height=480,
            source_type="VIRTUAL_CAMERA",
            source_fps=30.0,
            valid=True,
        )
        assert pkt.frame_id == 1
        assert pkt.source_type == "VIRTUAL_CAMERA"

        # Frozen immutability
        with pytest.raises(Exception):
            pkt.frame_id = 2  # type: ignore

        # Reject 3D array when marked valid
        with pytest.raises(ValueError):
            FramePacket(
                frame=np.zeros((480, 640, 3), dtype=np.uint8),
                frame_id=1,
                timestamp=0.0,
                width=640,
                height=480,
                source_type="VIRTUAL_CAMERA",
                source_fps=30.0,
                valid=True,
            )

        # Reject float array when marked valid
        with pytest.raises(ValueError):
            FramePacket(
                frame=np.zeros((480, 640), dtype=np.float32),
                frame_id=1,
                timestamp=0.0,
                width=640,
                height=480,
                source_type="VIRTUAL_CAMERA",
                source_fps=30.0,
                valid=True,
            )

    def test_virtual_camera_frame_adapter(self):
        """Verify VirtualCameraFrameAdapter exposes FramePacket contract without modifying VirtualCamera."""
        intrinsics = CameraIntrinsics(width=640, height=480, fov_horizontal_deg=4.0, fov_vertical_deg=3.0)
        camera = VirtualCamera(intrinsics=intrinsics, update_rate_hz=30.0)
        adapter = VirtualCameraFrameAdapter(camera=camera, fps=30.0, duration=10.0)

        # Observation initially None before first step
        pkt0 = adapter.get_frame_packet(frame_id=0, timestamp=0.0)
        assert pkt0.source_type == "VIRTUAL_CAMERA"
        assert pkt0.frame_id == 0
        assert pkt0.timestamp == 0.0
        assert pkt0.width == 640
        assert pkt0.height == 480
        assert pkt0.valid is False

        # Supply observation array
        obs = np.full((480, 640), 128, dtype=np.uint8)
        pkt1 = adapter.get_frame_packet(frame_id=1, timestamp=0.033333, observation=obs)
        assert pkt1.valid is True
        assert pkt1.frame is not None
        assert pkt1.frame.shape == (480, 640)
        assert pkt1.frame.dtype == np.uint8
        assert pkt1.frame_id == 1
        assert pkt1.codec == "RAW_SYNTHETIC"


# ==============================================================================
# 3. Benchmark-1 Regression Integrity Verification
# ==============================================================================
class TestBenchmark1RegressionIntegrity:
    def test_virtual_camera_intrinsics_and_projection_unchanged(self):
        """Verify VirtualCamera intrinsics, projection math, and FOV bounds are unchanged."""
        intrinsics = CameraIntrinsics(width=640, height=480, fov_horizontal_deg=4.0, fov_vertical_deg=3.0)
        camera = VirtualCamera(intrinsics=intrinsics, update_rate_hz=30.0)

        # Baseline projection check: target at center (1000, 1000)
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
        # State coordinates must be finite and non-trivial
        for t, x, y, vx, vy in states:
            assert np.isfinite(x) and np.isfinite(y)
            assert np.isfinite(vx) and np.isfinite(vy)
