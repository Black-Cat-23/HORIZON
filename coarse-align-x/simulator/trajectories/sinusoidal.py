"""
HORIZON Sinusoidal Trajectory (Optional Interface)
=========================================================
Independent 2D sinusoidal kinematic motion.
"""

from __future__ import annotations

import math
from typing import Tuple
from simulator.trajectories.base import Trajectory


class SinusoidalTrajectory(Trajectory):
    """Independent 2D harmonic oscillator trajectory.

    Kinematics:
        x(t)  = cx + Ax * sin(2π * fx * t + φx)
        y(t)  = cy + Ay * sin(2π * fy * t + φy)
    """

    def __init__(
        self,
        center_x: float = 1000.0,
        center_y: float = 1000.0,
        amplitude_x: float = 400.0,
        amplitude_y: float = 300.0,
        frequency_x: float = 0.5,
        frequency_y: float = 0.7,
        phase_x: float = 0.0,
        phase_y: float = 0.0,
    ) -> None:
        self._cx = float(center_x)
        self._cy = float(center_y)
        self._ax = float(amplitude_x)
        self._ay = float(amplitude_y)
        self._wx = 2.0 * math.pi * float(frequency_x)
        self._wy = 2.0 * math.pi * float(frequency_y)
        self._px = float(phase_x)
        self._py = float(phase_y)

    def state_at(self, t: float) -> Tuple[float, float, float, float, float, float]:
        if t < 0:
            raise ValueError(f"Time t must be non-negative, got {t}")

        tx = self._wx * t + self._px
        ty = self._wy * t + self._py

        x = self._cx + self._ax * math.sin(tx)
        y = self._cy + self._ay * math.sin(ty)

        vx = self._ax * self._wx * math.cos(tx)
        vy = self._ay * self._wy * math.cos(ty)

        ax = -self._ax * (self._wx ** 2) * math.sin(tx)
        ay = -self._ay * (self._wy ** 2) * math.sin(ty)

        return x, y, vx, vy, ax, ay

    def reset(self) -> None:
        pass
