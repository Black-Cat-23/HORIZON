"""
Archimedean Spiral Search Strategy.
HORIZON Phase 6
"""

from typing import Tuple, List
import math
from .base import SearchStrategy


class SpiralSearchStrategy(SearchStrategy):
    """
    Archimedean spiral search strategy around acquisition center or last known target estimate.
    Generates actual camera rate commands:
    r(theta) = r0 + k * theta
    pan = center_pan + r * cos(theta)
    tilt = center_tilt + r * sin(theta)
    """

    def __init__(
        self,
        initial_radius_deg: float = 0.2,
        radius_step_deg: float = 0.4,
        angular_rate_rad_s: float = 1.5,
        max_radius_deg: float = 4.0,
    ):
        self.initial_radius_deg = initial_radius_deg
        self.radius_step_deg = radius_step_deg
        self.angular_rate_rad_s = angular_rate_rad_s
        self.max_radius_deg = max_radius_deg

        self.center_pan_deg = 0.0
        self.center_tilt_deg = 0.0

        self._theta = 0.0
        self._completed = False

    def reset(self, center_pan_deg: float = 0.0, center_tilt_deg: float = 0.0) -> None:
        self.center_pan_deg = center_pan_deg
        self.center_tilt_deg = center_tilt_deg
        self._theta = 0.0
        self._completed = False

    def is_complete(self) -> bool:
        return self._completed

    def _get_radius_deg(self, theta: float) -> float:
        # r = r0 + (dr / (2*pi)) * theta
        return self.initial_radius_deg + (self.radius_step_deg / (2.0 * math.pi)) * theta

    def next_command(self, dt: float, current_pan_deg: float, current_tilt_deg: float) -> Tuple[float, float]:
        if self._completed or dt <= 0.0:
            return (0.0, 0.0)

        # Advance theta angle
        self._theta += self.angular_rate_rad_s * dt
        r = self._get_radius_deg(self._theta)

        if r > self.max_radius_deg:
            self._completed = True
            return (0.0, 0.0)

        # Desired position on spiral
        target_pan = self.center_pan_deg + r * math.cos(self._theta)
        target_tilt = self.center_tilt_deg + r * math.sin(self._theta)

        # Calculate proportional rate commands to move toward target_pan, target_tilt
        error_pan = target_pan - current_pan_deg
        error_tilt = target_tilt - current_tilt_deg

        # Rate command = position error / dt (clamped by controller saturation later)
        pan_rate = error_pan / dt
        tilt_rate = error_tilt / dt

        return (pan_rate, tilt_rate)

    def get_trajectory_history(self) -> List[Tuple[float, float]]:
        pts = []
        theta = 0.0
        d_theta = 0.1
        while True:
            r = self._get_radius_deg(theta)
            if r > self.max_radius_deg:
                break
            px = self.center_pan_deg + r * math.cos(theta)
            py = self.center_tilt_deg + r * math.sin(theta)
            pts.append((px, py))
            theta += d_theta
        return pts
