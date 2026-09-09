"""
Integration tests for VideoFrameSource external MP4 video interface.
"""

import pytest
from benchmark.video import VideoFrameSource, HAS_OPENCV


def test_video_frame_source_nonexistent_file():
    with pytest.raises(FileNotFoundError):
        VideoFrameSource("non_existent_video_path.mp4")
