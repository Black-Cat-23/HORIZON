"""
HORIZON Sensor Frame — Immutable Observation Metadata
=======================================================
Every camera observation is wrapped in a SensorFrame that carries
full lineage metadata alongside the pixel data.

SensorFrame guarantees:
  1. Pixels are read-only (WRITEABLE=False)
  2. All metadata is frozen (dataclass fields immutable)
  3. clean_frame_id traces the lineage back to the original clean frame
  4. disturbance_flags is a compact string encoding which pipeline stages
     were active during this frame's production

This module defines:
  - SensorFrame: The primary observation container
  - SensorLineage: Monotonic counter for frame IDs
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Optional

import numpy as np


# ---------------------------------------------------------------------------
# Frame counter (monotonic, per-camera-instance)
# ---------------------------------------------------------------------------

class SensorLineage:
    """Monotonically increasing frame ID counter for a camera instance.

    The counter starts at 0 and increments once per captured observation.
    Separate clean and disturbed frame IDs allow lineage tracing.
    """

    def __init__(self) -> None:
        self._frame_id: int = -1
        self._clean_id: int = -1

    @property
    def frame_id(self) -> int:
        return self._frame_id

    @property
    def clean_id(self) -> int:
        return self._clean_id

    def next_clean(self) -> int:
        """Increment and return the next clean frame ID."""
        self._clean_id += 1
        self._frame_id += 1
        return self._frame_id

    def next_disturbed(self) -> int:
        """Increment and return the next disturbed frame ID."""
        self._frame_id += 1
        return self._frame_id

    def reset(self) -> None:
        """Reset all counters to -1 (pre-first-frame state)."""
        self._frame_id = -1
        self._clean_id = -1


# ---------------------------------------------------------------------------
# Immutable observation container
# ---------------------------------------------------------------------------

class SensorFrame:
    """Immutable camera observation with full lineage metadata.

    Pixel data is stored as a read-only NumPy array. All metadata fields
    are immutable after construction.

    Parameters:
        frame_id: Monotonically increasing frame counter (clean + disturbed).
        timestamp: Exact simulation timestamp in seconds.
        camera_pan_deg: Gimbal pan angle at capture time (degrees).
        camera_tilt_deg: Gimbal tilt angle at capture time (degrees).
        camera_pan_rate_deg_s: Actual pan rate at capture (degrees/second).
        camera_tilt_rate_deg_s: Actual tilt rate at capture (degrees/second).
        exposure_ms: Exposure time applied to this frame (milliseconds).
        gain_db: Electronic gain applied (dB).
        is_disturbed: True if disturbance pipeline was applied.
        clean_frame_id: Frame ID of the clean source this was derived from.
                        Equals frame_id if this is the clean frame.
        disturbance_flags: JSON-encoded dict of active disturbance stages.
        image_plane_vel_u: Target horizontal image velocity at capture (px/frame).
        image_plane_vel_v: Target vertical image velocity at capture (px/frame).
        pixels: 2D uint8 NumPy array (height × width). Stored read-only.
    """

    __slots__ = (
        "_frame_id", "_timestamp", "_camera_pan_deg", "_camera_tilt_deg",
        "_camera_pan_rate_deg_s", "_camera_tilt_rate_deg_s",
        "_exposure_ms", "_gain_db", "_is_disturbed", "_clean_frame_id",
        "_disturbance_flags", "_image_plane_vel_u", "_image_plane_vel_v",
        "_pixels",
    )

    def __init__(
        self,
        frame_id: int = 0,
        timestamp: float = 0.0,
        camera_pan_deg: float = 0.0,
        camera_tilt_deg: float = 0.0,
        camera_pan_rate_deg_s: float = 0.0,
        camera_tilt_rate_deg_s: float = 0.0,
        exposure_ms: float = 1.0,
        gain_db: float = 0.0,
        is_disturbed: bool = False,
        clean_frame_id: int = 0,
        disturbance_flags: str = "{}",
        image_plane_vel_u: float = 0.0,
        image_plane_vel_v: float = 0.0,
        pixels: Optional[np.ndarray] = None,
    ) -> None:
        self._frame_id = int(frame_id)
        self._timestamp = float(timestamp)
        self._camera_pan_deg = float(camera_pan_deg)
        self._camera_tilt_deg = float(camera_tilt_deg)
        self._camera_pan_rate_deg_s = float(camera_pan_rate_deg_s)
        self._camera_tilt_rate_deg_s = float(camera_tilt_rate_deg_s)
        self._exposure_ms = float(exposure_ms)
        self._gain_db = float(gain_db)
        self._is_disturbed = bool(is_disturbed)
        self._clean_frame_id = int(clean_frame_id)
        self._disturbance_flags = str(disturbance_flags)
        self._image_plane_vel_u = float(image_plane_vel_u)
        self._image_plane_vel_v = float(image_plane_vel_v)

        if pixels is None:
            pixels = np.zeros((480, 640), dtype=np.uint8)

        # Store read-only view
        arr = np.ascontiguousarray(pixels, dtype=np.uint8)
        arr.flags.writeable = False
        self._pixels = arr

    def with_disturbed_pixels(self, disturbed_pixels: np.ndarray, disturbance_flags: str = "{}") -> SensorFrame:
        """Return a new SensorFrame wrapping disturbed pixels while preserving lineage."""
        return SensorFrame(
            frame_id=self._frame_id,
            timestamp=self._timestamp,
            camera_pan_deg=self._camera_pan_deg,
            camera_tilt_deg=self._camera_tilt_deg,
            camera_pan_rate_deg_s=self._camera_pan_rate_deg_s,
            camera_tilt_rate_deg_s=self._camera_tilt_rate_deg_s,
            exposure_ms=self._exposure_ms,
            gain_db=self._gain_db,
            is_disturbed=True,
            clean_frame_id=self._clean_frame_id,
            disturbance_flags=disturbance_flags,
            image_plane_vel_u=self._image_plane_vel_u,
            image_plane_vel_v=self._image_plane_vel_v,
            pixels=disturbed_pixels,
        )

    # ------------------------------------------------------------------
    # Properties (all immutable)
    # ------------------------------------------------------------------

    @property
    def frame_id(self) -> int:
        """Monotonically increasing frame ID."""
        return self._frame_id

    @property
    def timestamp(self) -> float:
        """Exact simulation timestamp in seconds."""
        return self._timestamp

    @property
    def camera_pan_deg(self) -> float:
        return self._camera_pan_deg

    @property
    def camera_tilt_deg(self) -> float:
        return self._camera_tilt_deg

    @property
    def camera_pan_rate_deg_s(self) -> float:
        return self._camera_pan_rate_deg_s

    @property
    def camera_tilt_rate_deg_s(self) -> float:
        return self._camera_tilt_rate_deg_s

    @property
    def exposure_ms(self) -> float:
        return self._exposure_ms

    @property
    def gain_db(self) -> float:
        return self._gain_db

    @property
    def is_disturbed(self) -> bool:
        """True if disturbance pipeline was applied."""
        return self._is_disturbed

    @property
    def clean_frame_id(self) -> int:
        """Frame ID of the clean source this was derived from."""
        return self._clean_frame_id

    @property
    def disturbance_flags(self) -> str:
        """JSON-encoded dict of active disturbance stages."""
        return self._disturbance_flags

    @property
    def image_plane_vel_u(self) -> float:
        """Target horizontal image-plane velocity (px/frame) at capture time."""
        return self._image_plane_vel_u

    @property
    def image_plane_vel_v(self) -> float:
        """Target vertical image-plane velocity (px/frame) at capture time."""
        return self._image_plane_vel_v

    @property
    def pixels(self) -> np.ndarray:
        """Read-only 2D uint8 pixel array (height × width)."""
        return self._pixels

    @property
    def shape(self) -> tuple:
        return self._pixels.shape

    @property
    def image_plane_speed(self) -> float:
        """Target image-plane speed in px/frame."""
        import math
        return math.sqrt(self._image_plane_vel_u ** 2 + self._image_plane_vel_v ** 2)

    def get_disturbance_flags_dict(self) -> dict:
        """Parse disturbance_flags JSON string to dict."""
        try:
            return json.loads(self._disturbance_flags)
        except (json.JSONDecodeError, ValueError):
            return {}

    def summary(self) -> str:
        """Return human-readable sensor frame summary."""
        kind = "DISTURBED" if self._is_disturbed else "CLEAN"
        return (
            f"SensorFrame [{kind}]\n"
            f"  frame_id={self._frame_id}  clean_frame_id={self._clean_frame_id}\n"
            f"  timestamp={self._timestamp:.6f} s\n"
            f"  camera=({self._camera_pan_deg:.3f}°, {self._camera_tilt_deg:.3f}°)\n"
            f"  exposure={self._exposure_ms:.3f} ms  gain={self._gain_db:+.2f} dB\n"
            f"  image_vel=({self._image_plane_vel_u:.3f}, {self._image_plane_vel_v:.3f}) px/frame\n"
            f"  shape={self._pixels.shape}  writeable={self._pixels.flags.writeable}"
        )

    def __repr__(self) -> str:
        return (
            f"SensorFrame(id={self._frame_id}, t={self._timestamp:.4f}s, "
            f"{'disturbed' if self._is_disturbed else 'clean'}, "
            f"shape={self._pixels.shape})"
        )
