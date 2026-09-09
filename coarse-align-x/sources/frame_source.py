from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Tuple, Optional, Dict, Any
import numpy as np

@dataclass
class VideoMetadata:
    source_type: str  # "SYNTHETIC" or "VIDEO_FILE"
    file_path: Optional[str] = None
    native_width: Optional[int] = None
    native_height: Optional[int] = None
    fps: Optional[float] = None
    total_frames: Optional[int] = None
    duration_seconds: Optional[float] = None
    codec: Optional[str] = None
    normalized_width: int = 640
    normalized_height: int = 480

class FrameSource(ABC):
    """Abstract interface for all frame providers.

    Implementations must return frames that are ready for the detector pipeline:
    * shape (480, 640)
    * dtype uint8
    * single channel (grayscale)
    """

    @abstractmethod
    def open(self) -> bool:
        """Open the source (file, device, or simulation). Returns True on success."""
        pass

    @abstractmethod
    def read(self) -> Tuple[bool, Optional[np.ndarray], float, int, Dict[str, Any]]:
        """Read the next frame.
        Returns:
            success (bool), frame (np.ndarray or None), timestamp (seconds),
            frame_index (int), metadata (dict).
        """
        pass

    @abstractmethod
    def seek(self, frame_index: int) -> bool:
        """Seek to the given frame index (only for seekable sources)."""
        pass

    @abstractmethod
    def reset(self) -> None:
        """Reset the source back to the beginning without reopening."""
        pass

    @abstractmethod
    def close(self) -> None:
        """Close and release any resources."""
        pass

    @abstractmethod
    def get_metadata(self) -> VideoMetadata:
        """Return static metadata for the source."""
        pass

    @abstractmethod
    def is_open(self) -> bool:
        pass

    @abstractmethod
    def get_total_frames(self) -> int:
        """Return total number of frames, or -1 if unknown/live stream."""
        pass

    @abstractmethod
    def get_fps(self) -> float:
        """Return the native frames‑per‑second of the source."""
        pass

