"""
HORIZON Straight Line Trajectory
========================================
Analytical straight-line kinematic motion with deterministic boundary handling
(BOUNCE and CLAMP modes).
"""

from __future__ import annotations

import math
from typing import Tuple
from simulator.trajectories.base import Trajectory


class StraightLineTrajectory(Trajectory):
    """Analytical straight-line trajectory with deterministic boundary handling.

    Parameters:
        x0: Initial X position.
        y0: Initial Y position.
        vx0: Initial X velocity in px/s.
        vy0: Initial Y velocity in px/s.
        world_width: World width (default 2000).
        world_height: World height (default 2000).
        target_size_px: Size of target for margin calculation (margin = size/2).
        boundary_mode: "bounce" or "clamp".
    """

    def __init__(
        self,
        x0: float,
        y0: float,
        vx0: float,
        vy0: float,
        world_width: float = 2000.0,
        world_height: float = 2000.0,
        target_size_px: float = 10.0,
        boundary_mode: str = "bounce",
    ) -> None:
        if boundary_mode not in {"bounce", "clamp"}:
            raise ValueError(f"Unknown boundary_mode: {boundary_mode}")

        half_size = target_size_px / 2.0
        self._x_min = half_size
        self._x_max = world_width - half_size
        self._y_min = half_size
        self._y_max = world_height - half_size

        if self._x_max <= self._x_min or self._y_max <= self._y_min:
            raise ValueError("World bounds smaller than target size.")

        # Ensure initial position is within bounds
        self._x0 = max(self._x_min, min(self._x_max, float(x0)))
        self._y0 = max(self._y_min, min(self._y_max, float(y0)))
        self._vx0 = float(vx0)
        self._vy0 = float(vy0)
        self._boundary_mode = boundary_mode

    @staticmethod
    def _reflect_1d(
        p0: float, v0: float, t: float, p_min: float, p_max: float
    ) -> Tuple[float, float]:
        """Closed-form analytical 1D reflection between [p_min, p_max]."""
        if v0 == 0.0:
            return p0, 0.0

        span = p_max - p_min
        unbounded = p0 + v0 * t
        u = (unbounded - p_min) / span
        n = math.floor(u)
        frac = u - n

        if n % 2 == 0:
            # Moving in original direction
            pos = p_min + frac * span
            vel = v0
        else:
            # Reflected
            pos = p_min + (1.0 - frac) * span
            vel = -v0

        return pos, vel

    @staticmethod
    def _clamp_1d(
        p0: float, v0: float, t: float, p_min: float, p_max: float
    ) -> Tuple[float, float]:
        """Closed-form analytical 1D motion clamped at bounds."""
        unbounded = p0 + v0 * t
        if unbounded <= p_min:
            return p_min, 0.0
        elif unbounded >= p_max:
            return p_max, 0.0
        else:
            return unbounded, v0

    def state_at(self, t: float) -> Tuple[float, float, float, float, float, float]:
        if t < 0:
            raise ValueError(f"Time t must be non-negative, got {t}")

        if self._boundary_mode == "bounce":
            x, vx = self._reflect_1d(self._x0, self._vx0, t, self._x_min, self._x_max)
            y, vy = self._reflect_1d(self._y0, self._vy0, t, self._y_min, self._y_max)
        else:
            x, vx = self._clamp_1d(self._x0, self._vx0, t, self._x_min, self._x_max)
            y, vy = self._clamp_1d(self._y0, self._vy0, t, self._y_min, self._y_max)

        ax = 0.0
        ay = 0.0
        return x, y, vx, vy, ax, ay

    def reset(self) -> None:
        pass
