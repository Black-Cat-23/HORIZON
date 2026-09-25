"""
HORIZON Circular Trajectory
===================================
Analytical circular kinematic motion with exact first and second derivatives.
"""

from __future__ import annotations

import math
from typing import Tuple
from simulator.trajectories.base import Trajectory


class CircularTrajectory(Trajectory):
    """Analytical circular trajectory with closed-form position, velocity, and acceleration.

    Kinematics:
        θ(t)  = ω * t + φ
        x(t)  = cx + R * cos(θ)
        y(t)  = cy + R * sin(θ)
        vx(t) = -R * ω * sin(θ)
        vy(t) =  R * ω * cos(θ)
        ax(t) = -R * ω² * cos(θ)
        ay(t) = -R * ω² * sin(θ)

    Parameters:
        center_x: Orbit center X.
        center_y: Orbit center Y.
        radius: Orbit radius (> 0).
        angular_velocity: Angular rate ω in rad/s.
        phase: Initial phase angle φ in radians.
        world_width: Maximum world X boundary.
        world_height: Maximum world Y boundary.
        target_size_px: Size of target in pixels for margin validation.
    """

    def __init__(
        self,
        center_x: float = 1000.0,
        center_y: float = 1000.0,
        radius: float = 300.0,
        angular_velocity: float = 1.0,
        phase: float = 0.0,
        world_width: float = 2000.0,
        world_height: float = 2000.0,
        target_size_px: float = 10.0,
    ) -> None:
        if radius <= 0:
            raise ValueError(f"Radius must be positive, got {radius}")

        margin = target_size_px / 2.0
        if (center_x - radius < margin) or (center_x + radius > world_width - margin):
            raise ValueError(
                f"Circular trajectory exceeds world X bounds [0, {world_width}]: "
                f"min={center_x - radius:.1f}, max={center_x + radius:.1f}"
            )
        if (center_y - radius < margin) or (center_y + radius > world_height - margin):
            raise ValueError(
                f"Circular trajectory exceeds world Y bounds [0, {world_height}]: "
                f"min={center_y - radius:.1f}, max={center_y + radius:.1f}"
            )

        self._cx = float(center_x)
        self._cy = float(center_y)
        self._r = float(radius)
        self._omega = float(angular_velocity)
        self._phase = float(phase)

    @property
    def radius(self) -> float:
        return self._r

    @property
    def angular_velocity(self) -> float:
        return self._omega

    def state_at(self, t: float) -> Tuple[float, float, float, float, float, float]:
        if t < 0:
            raise ValueError(f"Time t must be non-negative, got {t}")

        theta = self._omega * t + self._phase
        cos_t = math.cos(theta)
        sin_t = math.sin(theta)

        x = self._cx + self._r * cos_t
        y = self._cy + self._r * sin_t

        vx = -self._r * self._omega * sin_t
        vy = self._r * self._omega * cos_t

        ax = -self._r * (self._omega ** 2) * cos_t
        ay = -self._r * (self._omega ** 2) * sin_t

        return x, y, vx, vy, ax, ay

    def reset(self) -> None:
        pass
