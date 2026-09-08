"""
External Video Interface (Benchmark-2)
======================================
FrameSource adapter for reading external MP4 video files into PAT detection pipeline.
Ground-Truth Policy: When ground-truth is unavailable, ground-truth dependent metrics (RMSE, tracking error) are omitted.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Iterator, Optional, Tuple, Any
import numpy as np

logger = logging.getLogger(__name__)

try:
    import cv2
    HAS_OPENCV = True
except ImportError:
    HAS_OPENCV = False
    logger.warning("OpenCV (cv2) not available. VideoFrameSource will require numpy fallback.")


class VideoFrameSource:
    """Frame source reading video files (MP4/AVI/MKV) frame by frame."""

    def __init__(self, video_path: str | Path) -> None:
        self.video_path = Path(video_path)
        if not self.video_path.exists():
            raise FileNotFoundError(f"Video file not found: {self.video_path}")
        
        if not HAS_OPENCV:
            raise RuntimeError("OpenCV is required for VideoFrameSource.")

        self._cap = cv2.VideoCapture(str(self.video_path))
        if not self._cap.isOpened():
            raise RuntimeError(f"Failed to open video file: {self.video_path}")

        self.width = int(self._cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.height = int(self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self.fps = float(self._cap.get(cv2.CAP_PROP_FPS)) or 30.0
        self.total_frames = int(self._cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.current_frame_idx = 0

    def read_frame(self) -> Optional[np.ndarray]:
        """Read next frame as a grayscale uint8 array."""
        if not self._cap.isOpened():
            return None
        ret, frame = self._cap.read()
        if not ret or frame is None:
            return None
        self.current_frame_idx += 1
        
        # Convert BGR to Grayscale for perception engine
        if len(frame.shape) == 3 and frame.shape[2] == 3:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        else:
            gray = frame
        return gray

    def reset(self) -> None:
        """Reset video stream to the beginning."""
        if self._cap:
            self._cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            self.current_frame_idx = 0

    def close(self) -> None:
        """Release video capture resources."""
        cap = getattr(self, "_cap", None)
        if cap is not None and cap.isOpened():
            cap.release()

    def __iter__(self) -> Iterator[Tuple[int, np.ndarray]]:
        self.reset()
        while True:
            frame = self.read_frame()
            if frame is None:
                break
            yield (self.current_frame_idx, frame)

    def __del__(self) -> None:
        self.close()
