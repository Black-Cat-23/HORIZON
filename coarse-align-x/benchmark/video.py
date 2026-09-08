"""
External Video Interface (Phase 7 Perception Upgrade)
=====================================================
FrameSource adapter for reading external MP4/AVI/MKV video files into the perception pipeline.

Features:
  1. Strict Blind Mode: Zero ground-truth leakage or dependency.
  2. 30 FPS / Native FPS Timing: Preserves real-world dt = 1.0 / FPS.
  3. Video Sequence Controls: load, frame indexing, pause, resume, seek, restart, and EOF detection.
  4. Separate Timing: Measures video decoding latency independently from perception/inference latency.
  5. Deterministic Replay: Guarantees bitwise-identical frame sequence reproduction across replays.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from pathlib import Path
import time
from typing import Iterator, Optional, Tuple, Any
import numpy as np

logger = logging.getLogger(__name__)

try:
    import cv2
    HAS_OPENCV = True
except ImportError:
    HAS_OPENCV = False
    logger.warning("OpenCV (cv2) not available. VideoFrameSource will require fallback.")


class FrameSource(ABC):
    """Abstract Base Class for video and sensor frame sources."""

    @abstractmethod
    def read_frame(self) -> Optional[np.ndarray]:
        """Read next sensor frame as 2D uint8 grayscale array."""
        pass

    @abstractmethod
    def reset(self) -> None:
        """Reset stream to initial frame."""
        pass

    @abstractmethod
    def close(self) -> None:
        """Release underlying resources."""
        pass


class VideoFrameSource(FrameSource):
    """Frame source reading video files (MP4/AVI/MKV) frame by frame in Blind Mode."""

    def __init__(
        self,
        video_path: str | Path,
        force_fps: Optional[float] = None,
        target_size: Optional[Tuple[int, int]] = (640, 480),  # (width, height)
    ) -> None:
        self.video_path = Path(video_path)
        if not self.video_path.exists():
            raise FileNotFoundError(f"Video file not found: {self.video_path}")

        if not HAS_OPENCV:
            raise RuntimeError("OpenCV is required for VideoFrameSource.")

        self._cap = cv2.VideoCapture(str(self.video_path))
        if not self._cap.isOpened():
            raise RuntimeError(f"Failed to open video file: {self.video_path}")

        self.native_width = int(self._cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.native_height = int(self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        detected_fps = float(self._cap.get(cv2.CAP_PROP_FPS))
        if detected_fps <= 0.0 or np.isnan(detected_fps):
            detected_fps = 30.0
        self.fps = float(force_fps) if force_fps is not None else detected_fps
        self.dt = 1.0 / self.fps if self.fps > 0 else 0.033333

        self.total_frames = int(self._cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.target_size = target_size
        self.width = target_size[0] if target_size else self.native_width
        self.height = target_size[1] if target_size else self.native_height

        self.current_frame_idx = 0
        self._is_paused = False
        self._last_frame: Optional[np.ndarray] = None
        self._last_decode_time_ms: float = 0.0
        self.blind_mode = True  # Strict blind mode: no synthetic GT access

    @property
    def is_paused(self) -> bool:
        return self._is_paused

    @property
    def is_eof(self) -> bool:
        if self._cap is None or not self._cap.isOpened():
            return True
        return self.current_frame_idx >= self.total_frames

    @property
    def current_timestamp_s(self) -> float:
        return self.current_frame_idx * self.dt

    @property
    def last_decode_time_ms(self) -> float:
        return self._last_decode_time_ms

    def pause(self) -> None:
        """Pause playback stream."""
        self._is_paused = True

    def resume(self) -> None:
        """Resume playback stream."""
        self._is_paused = False

    def restart(self) -> None:
        """Restart stream from frame 0."""
        self.reset()
        self._is_paused = False

    def seek(self, frame_idx: int) -> bool:
        """Seek to specific frame index."""
        if self._cap is None or not self._cap.isOpened():
            return False
        target = max(0, min(frame_idx, max(0, self.total_frames - 1)))
        success = bool(self._cap.set(cv2.CAP_PROP_POS_FRAMES, target))
        if success:
            self.current_frame_idx = target
            self._last_frame = None
        return success

    def seek_time(self, timestamp_s: float) -> bool:
        """Seek to timestamp in seconds."""
        frame_idx = int(round(timestamp_s * self.fps))
        return self.seek(frame_idx)

    def read_frame_timed(self) -> Tuple[Optional[np.ndarray], float]:
        """Read next frame and return (frame, decode_latency_ms)."""
        t0 = time.perf_counter()
        frame = self.read_frame()
        t1 = time.perf_counter()
        self._last_decode_time_ms = (t1 - t0) * 1000.0
        return frame, self._last_decode_time_ms

    def read_frame(self) -> Optional[np.ndarray]:
        """Read next frame as a grayscale uint8 array."""
        if self._cap is None or not self._cap.isOpened():
            return None

        if self._is_paused:
            return self._last_frame

        ret, frame = self._cap.read()
        if not ret or frame is None:
            return None

        self.current_frame_idx += 1

        # Convert to Grayscale uint8 for perception engine
        if len(frame.shape) == 3 and frame.shape[2] == 3:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        elif len(frame.shape) == 3 and frame.shape[2] == 4:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGRA2GRAY)
        else:
            gray = frame

        # Resize if target size requested (e.g. 640x480)
        if self.target_size is not None:
            tw, th = self.target_size
            if gray.shape[1] != tw or gray.shape[0] != th:
                gray = cv2.resize(gray, (tw, th), interpolation=cv2.INTER_AREA)

        self._last_frame = gray
        return gray

    def reset(self) -> None:
        """Reset video stream to the beginning."""
        if self._cap and self._cap.isOpened():
            self._cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            self.current_frame_idx = 0
            self._last_frame = None

    def close(self) -> None:
        """Release video capture resources."""
        cap = getattr(self, "_cap", None)
        if cap is not None and cap.isOpened():
            cap.release()
            self._cap = None

    def __iter__(self) -> Iterator[Tuple[int, float, np.ndarray]]:
        """Iterate over all frames: yields (frame_idx, timestamp_s, frame_ndarray)."""
        self.reset()
        while True:
            t = self.current_timestamp_s
            idx = self.current_frame_idx
            frame = self.read_frame()
            if frame is None:
                break
            yield (idx, t, frame)

    def __del__(self) -> None:
        self.close()
