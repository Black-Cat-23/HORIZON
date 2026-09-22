"""
HORIZON Spiral Trajectory (Optional Interface)
=====================================================
Archimedean spiral trajectory for search patterns.
"""

from __future__ import annotations

import math
from typing import Tuple
from simulator.trajectories.base import Trajectory


class SpiralTrajectory(Trajectory):
    """Archimedean spiral kinematic trajectory.

    Kinematics:
        r(t) = r0 + expansion_rate * t
        θ(t) = ω * t + φ
        x(t) = cx + r(t) * cos(θ)
        y(t) = cy + r(t) * sin(θ)
    """

    def __init__(
        self,
        center_x: float = 1000.0,
        center_y: float = 1000.0,
        initial_radius: float = 50.0,
        expansion_rate: float = 20.0,
        angular_velocity: float = 1.5,
        phase: float = 0.0,
    ) -> None:
        self._cx = float(center_x)
        self._cy = float(center_y)
        self._r0 = float(initial_radius)
        self._dr = float(expansion_rate)
        self._omega = float(angular_velocity)
        self._phase = float(phase)

    def state_at(self, t: float) -> Tuple[float, float, float, float, float, float]:
        if t < 0:
            raise ValueError(f"Time t must be non-negative, got {t}")

        r = self._r0 + self._dr * t
        theta = self._omega * t + self._phase
        cos_t = math.cos(theta)
        sin_t = math.sin(theta)

        x = self._cx + r * cos_t
        y = self._cy + r * sin_t

        vx = self._dr * cos_t - r * self._omega * sin_t
        vy = self._dr * sin_t + r * self._omega * cos_t

        ax = -2.0 * self._dr * self._omega * sin_t - r * (self._omega ** 2) * cos_t
        ay = 2.0 * self._dr * self._omega * cos_t - r * (self._omega ** 2) * sin_t

        return x, y, vx, vy, ax, ay

    def reset(self) -> None:
        pass
