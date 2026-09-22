import cv2
import numpy as np
from typing import Tuple, Dict, Any, Optional
import os
import logging
from .frame_source import FrameSource, VideoMetadata

logger = logging.getLogger(__name__)

class VideoFrameSource(FrameSource):
    """OpenCV based video frame source.

    Provides frames normalized to 640x480 uint8 grayscale as required by the
    detector pipeline. All native video metadata is stored in ``VideoMetadata``.
    """

    def __init__(self, video_path: str, playback_speed: float = 1.0):
        if not os.path.isfile(video_path):
            raise FileNotFoundError(f"Video file not found: {video_path}")
        self.video_path = video_path
        self.playback_speed = playback_speed
        self.cap: Optional[cv2.VideoCapture] = None
        self._opened = False
        self._frame_index = 0
        self._metadata: Optional[VideoMetadata] = None

    # ---------------------------------------------------------------------
    # Helper methods
    # ---------------------------------------------------------------------
    def _extract_metadata(self) -> VideoMetadata:
        width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = self.cap.get(cv2.CAP_PROP_FPS)
        if fps <= 0:
            logger.warning("FPS metadata missing or zero; defaulting to 30.0")
            fps = 30.0
        total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        codec_int = int(self.cap.get(cv2.CAP_PROP_FOURCC))
        codec = (
            chr((codec_int & 0xFF))
            + chr(((codec_int >> 8) & 0xFF))
            + chr(((codec_int >> 16) & 0xFF))
            + chr(((codec_int >> 24) & 0xFF))
        )
        duration = total_frames / fps if fps > 0 else None
        return VideoMetadata(
            source_type="VIDEO_FILE",
            file_path=self.video_path,
            native_width=width,
            native_height=height,
            fps=fps,
            total_frames=total_frames,
            duration_seconds=duration,
            codec=codec,
            normalized_width=640,
            normalized_height=480,
        )

    def _normalize_frame(self, frame: np.ndarray) -> np.ndarray:
        # 1. Convert to grayscale if needed
        if len(frame.shape) == 3:
            if frame.shape[2] == 3:
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                logger.debug("Converted BGR to grayscale")
            elif frame.shape[2] == 4:
                frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2GRAY)
                logger.debug("Converted BGRA to grayscale")
            else:
                raise ValueError(f"Unsupported channel count: {frame.shape[2]}")
        # 2. Resize to 640x480 if necessary
        if frame.shape[0] != 480 or frame.shape[1] != 640:
            sx = 640 / frame.shape[1]
            sy = 480 / frame.shape[0]
            interpolation = cv2.INTER_AREA if sx < 1.0 else cv2.INTER_LINEAR
            frame = cv2.resize(frame, (640, 480), interpolation=interpolation)
            logger.debug(f"Resized frame to 640x480 (sx={sx:.3f}, sy={sy:.3f})")
        # 3. Ensure dtype uint8
        if frame.dtype != np.uint8:
            frame = np.clip(frame, 0, 255).astype(np.uint8)
            logger.debug("Converted frame dtype to uint8")
        # 4. Sanity check
        if frame.shape != (480, 640):
            raise RuntimeError(f"Normalized frame has unexpected shape {frame.shape}")
        return frame

    # ---------------------------------------------------------------------
    # FrameSource interface
    # ---------------------------------------------------------------------
    def open(self) -> bool:
        self.cap = cv2.VideoCapture(self.video_path)
        if not self.cap.isOpened():
            logger.error(f"Failed to open video file: {self.video_path}")
            return False
        self._metadata = self._extract_metadata()
        self._opened = True
        self._frame_index = 0
        logger.info(
            f"Opened video {self.video_path} ({self._metadata.native_width}x{self._metadata.native_height} @ {self._metadata.fps:.2f} FPS)"
        )
        return True

    def read(self) -> Tuple[bool, Optional[np.ndarray], float, int, Dict[str, Any]]:
        if not self._opened or self.cap is None:
            raise RuntimeError("VideoFrameSource not opened")
        ret, frame = self.cap.read()
        if not ret:
            # End of video or read error
            return False, None, 0.0, self._frame_index, {}
        native_fps = self._metadata.fps if self._metadata and self._metadata.fps else 30.0
        timestamp = self._frame_index / native_fps
        norm_frame = self._normalize_frame(frame)
        metadata = {
            "native_width": self._metadata.native_width,
            "native_height": self._metadata.native_height,
            "codec": self._metadata.codec,
            "scale_x": 640 / self._metadata.native_width,
            "scale_y": 480 / self._metadata.native_height,
        }
        current_index = self._frame_index
        self._frame_index += 1
        return True, norm_frame, timestamp, current_index, metadata

    def seek(self, frame_index: int) -> bool:
        if not self._opened or self.cap is None:
            raise RuntimeError("VideoFrameSource not opened")
        success = self.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
        if not success:
            logger.error(f"Failed to seek to frame {frame_index}")
            return False
        self._frame_index = frame_index
        logger.info(f"Seeked to frame {frame_index}")
        return True

    def reset(self) -> None:
        if self.cap:
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
        self._frame_index = 0
        logger.debug("VideoFrameSource reset to start")

    def close(self) -> None:
        if self.cap:
            self.cap.release()
        self._opened = False
        logger.info("VideoFrameSource closed")

    def get_metadata(self) -> VideoMetadata:
        if not self._metadata:
            raise RuntimeError("Metadata not available; open the source first")
        return self._metadata

    def is_open(self) -> bool:
        return self._opened

    def get_total_frames(self) -> int:
        if self._metadata and self._metadata.total_frames is not None:
            return self._metadata.total_frames
        return -1

    def get_fps(self) -> float:
        if self._metadata and self._metadata.fps is not None:
            return self._metadata.fps
        return 0.0

