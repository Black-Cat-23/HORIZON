"""
HORIZON Figure-of-8 Trajectory
======================================
Analytical Lissajous / Lemniscate figure-8 kinematic motion with exact derivatives.
"""

from __future__ import annotations

import math
from typing import Tuple
from simulator.trajectories.base import Trajectory


class FigureEightTrajectory(Trajectory):
    """Analytical Figure-of-8 trajectory (Lissajous curve with 1:2 frequency ratio).

    Mathematical formulation:
        x(t)  = cx + A * sin(ω * t + φ)
        y(t)  = cy + B * sin(2 * ω * t + φ)

    Analytical derivatives:
        vx(t) = A * ω * cos(ω * t + φ)
        vy(t) = 2 * B * ω * cos(2 * ω * t + φ)

        ax(t) = -A * ω² * sin(ω * t + φ)
        ay(t) = -4 * B * ω² * sin(2 * ω * t + φ)

    Parameters:
        center_x: Pattern center X.
        center_y: Pattern center Y.
        amplitude_x: Horizontal amplitude A (> 0).
        amplitude_y: Vertical amplitude B (> 0).
        angular_velocity: Base frequency ω in rad/s.
        phase: Phase angle φ in radians.
        world_width: Maximum world X boundary.
        world_height: Maximum world Y boundary.
        target_size_px: Size of target in pixels for margin validation.
    """

    def __init__(
        self,
        center_x: float = 1000.0,
        center_y: float = 1000.0,
        amplitude_x: float = 400.0,
        amplitude_y: float = 300.0,
        angular_velocity: float = 0.8,
        phase: float = 0.0,
        world_width: float = 2000.0,
        world_height: float = 2000.0,
        target_size_px: float = 10.0,
    ) -> None:
        if amplitude_x <= 0:
            raise ValueError(f"amplitude_x must be positive, got {amplitude_x}")
        if amplitude_y <= 0:
            raise ValueError(f"amplitude_y must be positive, got {amplitude_y}")

        margin = target_size_px / 2.0
        if (center_x - amplitude_x < margin) or (center_x + amplitude_x > world_width - margin):
            raise ValueError(
                f"Figure-8 trajectory exceeds world X bounds [0, {world_width}]: "
                f"min={center_x - amplitude_x:.1f}, max={center_x + amplitude_x:.1f}"
            )
        if (center_y - amplitude_y < margin) or (center_y + amplitude_y > world_height - margin):
            raise ValueError(
                f"Figure-8 trajectory exceeds world Y bounds [0, {world_height}]: "
                f"min={center_y - amplitude_y:.1f}, max={center_y + amplitude_y:.1f}"
            )

        self._cx = float(center_x)
        self._cy = float(center_y)
        self._ax = float(amplitude_x)
        self._ay = float(amplitude_y)
        self._omega = float(angular_velocity)
        self._phase = float(phase)

    def state_at(self, t: float) -> Tuple[float, float, float, float, float, float]:
        if t < 0:
            raise ValueError(f"Time t must be non-negative, got {t}")

        t1 = self._omega * t + self._phase
        t2 = 2.0 * self._omega * t + self._phase

        sin_t1 = math.sin(t1)
        cos_t1 = math.cos(t1)
        sin_t2 = math.sin(t2)
        cos_t2 = math.cos(t2)

        x = self._cx + self._ax * sin_t1
        y = self._cy + self._ay * sin_t2

        vx = self._ax * self._omega * cos_t1
        vy = 2.0 * self._ay * self._omega * cos_t2

        ax = -self._ax * (self._omega ** 2) * sin_t1
        ay = -4.0 * self._ay * (self._omega ** 2) * sin_t2

        return x, y, vx, vy, ax, ay

    def reset(self) -> None:
        pass
