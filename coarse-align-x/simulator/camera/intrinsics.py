"""
HORIZON Camera Intrinsics Model
======================================
Formal mathematical model for pinhole optical camera intrinsics,
tangent projection, inverse projection, and FOV boundary verification.

Conventions:
  - Coordinate origin: center of optical axis (0, 0)
  - Image plane origin: top-left (0, 0)
  - +X angle (pan offset): target moves to the right (+u)
  - +Y angle (tilt offset): target moves downward (+v)
"""

from __future__ import annotations

import math
from typing import Tuple


class CameraIntrinsics:
    """Pinhole camera intrinsic model with analytical projection.

    Parameters:
        width: Sensor width in pixels (e.g., 640).
        height: Sensor height in pixels (e.g., 480).
        fov_horizontal_deg: Horizontal Field-of-View in degrees (e.g., 4.0).
        fov_vertical_deg: Vertical Field-of-View in degrees (e.g., 3.0).
    """

    def __init__(
        self,
        width: int = 640,
        height: int = 480,
        fov_horizontal_deg: float = 4.0,
        fov_vertical_deg: float = 3.0,
    ) -> None:
        if width <= 0 or height <= 0:
            raise ValueError(f"Sensor dimensions must be positive: {width}x{height}")
        if fov_horizontal_deg <= 0 or fov_vertical_deg <= 0:
            raise ValueError(
                f"FOV must be positive: {fov_horizontal_deg}°x{fov_vertical_deg}°"
            )

        self._width = int(width)
        self._height = int(height)
        self._fov_x_deg = float(fov_horizontal_deg)
        self._fov_y_deg = float(fov_vertical_deg)

        self._fov_x_rad = math.radians(self._fov_x_deg)
        self._fov_y_rad = math.radians(self._fov_y_deg)

        self._half_fov_x_rad = self._fov_x_rad / 2.0
        self._half_fov_y_rad = self._fov_y_rad / 2.0

        # Principal point (exact center of sensor)
        self._cx = float(self._width) / 2.0
        self._cy = float(self._height) / 2.0

        # Exact analytical focal lengths derived from FOV
        self._fx = (float(self._width) / 2.0) / math.tan(self._half_fov_x_rad)
        self._fy = (float(self._height) / 2.0) / math.tan(self._half_fov_y_rad)

    @property
    def width(self) -> int:
        return self._width

    @property
    def height(self) -> int:
        return self._height

    @property
    def fov_x_deg(self) -> float:
        return self._fov_x_deg

    @property
    def fov_y_deg(self) -> float:
        return self._fov_y_deg

    @property
    def fov_x_rad(self) -> float:
        return self._fov_x_rad

    @property
    def fov_y_rad(self) -> float:
        return self._fov_y_rad

    @property
    def half_fov_x_rad(self) -> float:
        return self._half_fov_x_rad

    @property
    def half_fov_y_rad(self) -> float:
        return self._half_fov_y_rad

    @property
    def fx(self) -> float:
        return self._fx

    @property
    def fy(self) -> float:
        return self._fy

    @property
    def cx(self) -> float:
        return self._cx

    @property
    def cy(self) -> float:
        return self._cy

    def project(self, theta_x_rad: float, theta_y_rad: float) -> Tuple[float, float]:
        """Project angular offsets (relative to camera boresight) to pixel coordinates (u, v).

        Formula:
            u = cx + fx * tan(theta_x)
            v = cy + fy * tan(theta_y)
        """
        u = self._cx + self._fx * math.tan(theta_x_rad)
        v = self._cy + self._fy * math.tan(theta_y_rad)
        return u, v

    def unproject(self, u: float, v: float) -> Tuple[float, float]:
        """Inverse projection from pixel coordinates (u, v) to angular offsets (theta_x, theta_y) in radians.

        Formula:
            theta_x = arctan((u - cx) / fx)
            theta_y = arctan((v - cy) / fy)
        """
        theta_x = math.atan((u - self._cx) / self._fx)
        theta_y = math.atan((v - self._cy) / self._fy)
        return theta_x, theta_y

    def is_in_fov(
        self, theta_x_rad: float, theta_y_rad: float, tol_rad: float = 1e-12
    ) -> bool:
        """Check if target angular location is within optical field of view.

        Returns True if:
            -half_fov_x <= theta_x <= +half_fov_x and
            -half_fov_y <= theta_y <= +half_fov_y
        """
        within_x = abs(theta_x_rad) <= (self._half_fov_x_rad + tol_rad)
        within_y = abs(theta_y_rad) <= (self._half_fov_y_rad + tol_rad)
        return within_x and within_y

    def is_pixel_in_sensor(self, u: float, v: float, tol_px: float = 1e-9) -> bool:
        """Check if projected pixel coordinate falls within active sensor array [0, W] x [0, H]."""
        return (-tol_px <= u <= self._width + tol_px) and (-tol_px <= v <= self._height + tol_px)
