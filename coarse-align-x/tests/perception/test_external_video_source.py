"""
External Video Source & Blind Mode Tests for HORIZON Perception Engines.
Phase 7 Upgrade: Testing 30 FPS timing, sequence handling, seek/pause, and deterministic replay.
"""

import tempfile
from pathlib import Path
import cv2
import numpy as np
import pytest

from benchmark.video import VideoFrameSource, HAS_OPENCV
from simulator.perception.video_source import FrameSource


@pytest.fixture
def sample_video_path(tmp_path):
    """Create a temporary 30 FPS test video (30 frames, 640x480)."""
    if not HAS_OPENCV:
        pytest.skip("OpenCV not available for video test.")
    
    vid_file = tmp_path / "test_30fps.mp4"
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(vid_file), fourcc, 30.0, (640, 480), False)

    for i in range(30):
        # Draw moving circle beacon
        frame = np.full((480, 640), 20, dtype=np.uint8)
        cx = int(100 + i * 15)
        cy = int(240)
        cv2.circle(frame, (cx, cy), 8, 240, -1)
        writer.write(frame)
    writer.release()
    return vid_file


def test_video_frame_source_30fps_timing(sample_video_path):
    """Verify VideoFrameSource preserves 30 FPS timing dt = 1/30s."""
    source = VideoFrameSource(sample_video_path, force_fps=30.0)
    assert isinstance(source, FrameSource)
    assert abs(source.fps - 30.0) < 0.1
    assert abs(source.dt - (1.0 / 30.0)) < 1e-4
    assert source.total_frames == 30
    assert source.blind_mode is True


def test_video_sequence_controls(sample_video_path):
    """Verify pause, resume, seek, and restart sequence controls."""
    source = VideoFrameSource(sample_video_path)

    # Read 5 frames
    for _ in range(5):
        f = source.read_frame()
        assert f is not None
    assert source.current_frame_idx == 5

    # Pause
    source.pause()
    assert source.is_paused
    f_paused = source.read_frame()
    # While paused, frame index does not advance
    assert source.current_frame_idx == 5

    # Resume
    source.resume()
    assert not source.is_paused

    # Seek to frame 15
    ok = source.seek(15)
    assert ok
    assert source.current_frame_idx == 15

    # Restart
    source.restart()
    assert source.current_frame_idx == 0


def test_deterministic_video_replay(sample_video_path):
    """Verify repeated playback produces bitwise identical frame arrays."""
    source = VideoFrameSource(sample_video_path)
    
    frames_run1 = [f for _, _, f in source]
    source.reset()
    frames_run2 = [f for _, _, f in source]

    assert len(frames_run1) == len(frames_run2)
    for f1, f2 in zip(frames_run1, frames_run2):
        assert np.array_equal(f1, f2)
