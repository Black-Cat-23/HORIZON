"""
HORIZON Virtual Camera Frame Adapter (SIH26169 Phase 1B)
=========================================================
Non-intrusive adapter wrapping the protected Virtual Camera to emit
the common FramePacket interface contract without modifying VirtualCamera internals.
"""

from __future__ import annotations

from typing import Optional
import numpy as np

from simulator.camera.camera import VirtualCamera
from sources.frame_packet import FramePacket


class VirtualCameraFrameAdapter:
    """Adapts a VirtualCamera instance to output standardized FramePacket instances.

    Guarantees:
      - Does not alter VirtualCamera projection, kinematics, or rendering.
      - Maps observation frames, frame_id, and timestamps directly to FramePacket.
    """

    def __init__(self, camera: VirtualCamera, fps: float = 30.0, duration: Optional[float] = None) -> None:
        self._camera = camera
        self._fps = float(fps)
        self._duration = duration

    @property
    def camera(self) -> VirtualCamera:
        return self._camera

    @property
    def fps(self) -> float:
        return self._fps

    def get_frame_packet(
        self,
        frame_id: int,
        timestamp: float,
        observation: Optional[np.ndarray] = None,
    ) -> FramePacket:
        """Extract a standardized FramePacket from the current camera state.

        Parameters:
            frame_id: Monotonic simulation frame index.
            timestamp: Simulation time in seconds.
            observation: Optional explicit observation array; if None, reads from camera.last_observation.

        Returns:
            Standardized FramePacket with source_type='VIRTUAL_CAMERA'.
        """
        obs = observation if observation is not None else self._camera.last_observation
        is_valid = obs is not None and isinstance(obs, np.ndarray) and obs.ndim == 2

        width = obs.shape[1] if (obs is not None and obs.ndim >= 2) else self._camera.intrinsics.width
        height = obs.shape[0] if (obs is not None and obs.ndim >= 2) else self._camera.intrinsics.height

        return FramePacket(
            frame=obs if is_valid else None,
            frame_id=int(frame_id),
            timestamp=float(timestamp),
            width=int(width),
            height=int(height),
            source_type="VIRTUAL_CAMERA",
            source_fps=self._fps,
            valid=is_valid,
            filename=None,
            duration=self._duration,
            codec="RAW_SYNTHETIC",
        )
