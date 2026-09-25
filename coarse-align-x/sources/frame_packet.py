"""
HORIZON Generic Frame Packet Representation
============================================
Step 5 Common Frame Object contract for both Virtual Camera and External Video sources.
Strict Invariant: Zero modification to existing Virtual Camera math or internals.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Any
import numpy as np


@dataclass(frozen=True)
class FramePacket:
    """Unified, generic frame container for all HORIZON sensor sources.

    Attributes:
        frame: 2D uint8 grayscale frame (shape: H x W). None if frame read failed.
        frame_id: Monotonically increasing sequential frame index (0-based).
        timestamp: Simulation or video playback timestamp in seconds.
        width: Pixel width of the frame.
        height: Pixel height of the frame.
        source_type: Identifier of the sensor source ('VIRTUAL_CAMERA' | 'EXTERNAL_VIDEO').
        source_fps: Frame rate of the source in frames per second.
        valid: True if frame decoding and extraction succeeded, False on EOF or error.
        filename: Optional filename of the external video file (if applicable).
        duration: Optional total stream duration in seconds.
        codec: Optional fourcc or video codec descriptor string.
    """
    frame: Optional[np.ndarray]
    frame_id: int
    timestamp: float
    width: int
    height: int
    source_type: str
    source_fps: float
    valid: bool
    filename: Optional[str] = None
    duration: Optional[float] = None
    codec: Optional[str] = None
    geometry: Optional[Any] = None
    dt: float = 0.0
    decode_latency_ms: float = 0.0
    processing_latency_ms: float = 0.0
    dropped_frames: int = 0
    frame_available_t: float = 0.0
    decode_start_t: float = 0.0
    decode_end_t: float = 0.0

    def __post_init__(self) -> None:
        if self.valid and self.frame is not None:
            if not isinstance(self.frame, np.ndarray):
                raise TypeError(f"Frame must be a numpy.ndarray, got {type(self.frame)}")
            if self.frame.ndim != 2:
                raise ValueError(f"Frame must be 2D grayscale, got shape {self.frame.shape}")
            if self.frame.dtype != np.uint8:
                raise ValueError(f"Frame must have dtype uint8, got {self.frame.dtype}")
