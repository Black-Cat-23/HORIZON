"""
HORIZON Motion Blur Engine
============================
Models optical motion blur as a function of actual image-plane velocity.

Mathematical model:
  blur_length_px = |v| * (exposure_ms / frame_interval_ms)

where:
  |v|              = image-plane speed (px/frame) = sqrt(v_u² + v_v²)
  exposure_ms      = sensor integration time
  frame_interval_ms= 1000 / camera_update_rate_hz

The blur direction is the unit vector of (v_u, v_v) in image pixel space.
A 1D linear kernel of length blur_length_px is applied via convolution.

If blur_length_px < 0.5 (sub-pixel motion): frame returned unchanged.
No arbitrary blur strength — every parameter is physically derived.

Coordinate convention: image pixels (u, v) in IMAGE coordinate system.
"""

from __future__ import annotations

import math
from typing import Tuple

import cv2
import numpy as np


class MotionBlurEngine:
    """Applies directional linear motion blur derived from image-plane velocity.

    Parameters:
        frame_interval_ms: Camera frame interval in milliseconds (1000/update_rate_hz).
                           Used as the denominator in blur_px calculation.
    """

    def __init__(self, frame_interval_ms: float = 1000.0 / 30.0) -> None:
        if frame_interval_ms <= 0:
            raise ValueError(
                f"frame_interval_ms must be positive, got {frame_interval_ms}"
            )
        self._frame_interval_ms = float(frame_interval_ms)

    @property
    def frame_interval_ms(self) -> float:
        return self._frame_interval_ms

    def compute_blur_length(
        self,
        vel_u_px_per_frame: float,
        vel_v_px_per_frame: float,
        exposure_ms: float,
    ) -> float:
        """Compute motion blur length in pixels.

        Formula: blur_px = |v| * (exposure_ms / frame_interval_ms)

        Args:
            vel_u_px_per_frame: Target horizontal image velocity (px/frame).
            vel_v_px_per_frame: Target vertical image velocity (px/frame).
            exposure_ms: Sensor exposure time in milliseconds.

        Returns:
            Blur length in pixels (>= 0). Returns 0.0 if exposure_ms <= 0.
        """
        if exposure_ms <= 0:
            return 0.0
        speed = math.sqrt(vel_u_px_per_frame ** 2 + vel_v_px_per_frame ** 2)
        blur_px = speed * (exposure_ms / self._frame_interval_ms)
        return float(blur_px)

    def apply_motion_blur(
        self,
        frame: np.ndarray,
        vx_px_s: float,
        vy_px_s: float,
        exposure_ms: float,
        frame_interval_ms: Optional[float] = None,
    ) -> np.ndarray:
        """Apply motion blur converting px/s velocity to px/frame.

        Args:
            frame: 2D uint8 camera frame.
            vx_px_s: Target horizontal image velocity (px/s).
            vy_px_s: Target vertical image velocity (px/s).
            exposure_ms: Sensor exposure time (ms).
            frame_interval_ms: Optional override for frame interval (ms).

        Returns:
            2D uint8 frame with motion blur applied.
        """
        interval = frame_interval_ms if frame_interval_ms is not None else self._frame_interval_ms
        vel_u_frame = vx_px_s * (interval / 1000.0)
        vel_v_frame = vy_px_s * (interval / 1000.0)
        blurred, _, _, _ = self.apply(frame, vel_u_frame, vel_v_frame, exposure_ms)
        return blurred

    def apply(
        self,
        frame: np.ndarray,
        vel_u_px_per_frame: float,
        vel_v_px_per_frame: float,
        exposure_ms: float,
    ) -> Tuple[np.ndarray, float, float, float]:
        """Apply directional motion blur to a camera frame.

        Args:
            frame: 2D uint8 camera frame (height × width).
            vel_u_px_per_frame: Target horizontal image velocity (px/frame).
            vel_v_px_per_frame: Target vertical image velocity (px/frame).
            exposure_ms: Sensor exposure time in milliseconds.

        Returns:
            Tuple of:
              - blurred_frame: 2D uint8 frame with motion blur applied.
              - blur_length_px: Actual blur length applied in pixels.
              - blur_dir_u: Normalized blur direction (horizontal component).
              - blur_dir_v: Normalized blur direction (vertical component).

        Notes:
            Returns input frame unchanged if blur_length_px < 0.5 px.
            Output is always uint8, same shape as input.
        """
        blur_px = self.compute_blur_length(vel_u_px_per_frame, vel_v_px_per_frame, exposure_ms)

        # Sub-pixel motion: no visible blur
        if blur_px < 0.5:
            return frame.copy(), 0.0, 0.0, 0.0

        # Compute direction unit vector
        speed = math.sqrt(vel_u_px_per_frame ** 2 + vel_v_px_per_frame ** 2)
        if speed < 1e-12:
            return frame.copy(), 0.0, 0.0, 0.0

        dir_u = vel_u_px_per_frame / speed
        dir_v = vel_v_px_per_frame / speed

        # Build linear motion blur kernel
        kernel_size = max(3, int(math.ceil(blur_px)))
        if kernel_size % 2 == 0:
            kernel_size += 1  # Keep odd for symmetry

        kernel = self._build_linear_kernel(kernel_size, dir_u, dir_v)

        # Apply kernel via filter2D (preserves uint8 range with clipping)
        blurred_f = cv2.filter2D(
            frame.astype(np.float32),
            ddepth=-1,
            kernel=kernel.astype(np.float32),
            borderType=cv2.BORDER_REFLECT,
        )
        blurred = np.clip(blurred_f, 0, 255).astype(np.uint8)

        return blurred, float(blur_px), float(dir_u), float(dir_v)

    @staticmethod
    def _build_linear_kernel(
        kernel_size: int, dir_u: float, dir_v: float
    ) -> np.ndarray:
        """Build a 2D directional motion blur kernel.

        Creates a kernel_size × kernel_size kernel with values along the
        motion direction (dir_u, dir_v), normalized to sum = 1.

        The line drawn from center in direction (dir_u, dir_v) using
        Bresenham-style discrete sampling.
        """
        kernel = np.zeros((kernel_size, kernel_size), dtype=np.float64)
        half = kernel_size // 2
        center = np.array([half, half], dtype=np.float64)

        count = 0
        for i in range(kernel_size):
            t = float(i - half)  # parameter along line
            row = center[1] + t * dir_v
            col = center[0] + t * dir_u
            r_i = int(round(row))
            c_i = int(round(col))
            if 0 <= r_i < kernel_size and 0 <= c_i < kernel_size:
                kernel[r_i, c_i] += 1.0
                count += 1

        if count == 0 or kernel.sum() == 0:
            # Fallback: identity kernel
            kernel[half, half] = 1.0

        kernel /= kernel.sum()
        return kernel

    def summary(self, vel_u: float, vel_v: float, exposure_ms: float) -> str:
        """Return human-readable summary of motion blur for given parameters."""
        blur_px = self.compute_blur_length(vel_u, vel_v, exposure_ms)
        active = blur_px >= 0.5
        return (
            f"MotionBlurEngine:\n"
            f"  frame_interval={self._frame_interval_ms:.3f} ms\n"
            f"  exposure={exposure_ms:.3f} ms\n"
            f"  velocity=({vel_u:.3f}, {vel_v:.3f}) px/frame\n"
            f"  blur_length={blur_px:.3f} px\n"
            f"  active={active}"
        )
