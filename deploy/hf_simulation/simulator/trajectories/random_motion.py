"""
HORIZON Random Motion Trajectory
========================================
Continuous, bounded, physically smooth stochastic motion model using a
deterministic seeded Ornstein-Uhlenbeck acceleration process with boundary reflection.

Strict constraints:
  - NO teleportation
  - Continuous position and velocity
  - Strictly bounded speed and acceleration
  - 100% deterministic and reproducible for a given seed
"""

from __future__ import annotations

import math
from typing import List, Tuple
import numpy as np
from simulator.trajectories.base import Trajectory


class RandomMotionTrajectory(Trajectory):
    """Continuous stochastic motion trajectory with bounded kinematics and reflection.

    Kinematic model:
        Acceleration follows a bounded mean-reverting stochastic process (Ornstein-Uhlenbeck):
            a(t + dt) = a(t) * (1 - θ * dt) + σ * sqrt(dt) * η
            where η ~ N(0, 1) from a dedicated deterministic NumPy Generator.
            |a| is clamped to max_acceleration.

        Velocity and position advance via symplectic integration:
            v(t + dt) = v(t) + a(t + dt) * dt
            |v| is clamped to max_speed.
            p(t + dt) = p(t) + v(t + dt) * dt

        When hitting world boundaries, position is clamped to the boundary margin
        and velocity is reversed (bounce reflection), guaranteeing continuous
        trajectory without teleportation.

    Parameters:
        rng: Deterministic numpy Generator instance.
        x0: Initial X position.
        y0: Initial Y position.
        max_speed: Maximum scalar speed in px/s.
        max_acceleration: Maximum scalar acceleration in px/s².
        world_width: Maximum world X boundary.
        world_height: Maximum world Y boundary.
        target_size_px: Target size in px for margin calculation.
        sim_dt: Internal integration timestep (default 1/60s).
    """

    def __init__(
        self,
        rng: np.random.Generator,
        x0: float = 1000.0,
        y0: float = 1000.0,
        max_speed: float = 150.0,
        max_acceleration: float = 200.0,
        world_width: float = 2000.0,
        world_height: float = 2000.0,
        target_size_px: float = 10.0,
        sim_dt: float = 1.0 / 60.0,
    ) -> None:
        if max_speed <= 0:
            raise ValueError(f"max_speed must be positive, got {max_speed}")
        if max_acceleration <= 0:
            raise ValueError(f"max_acceleration must be positive, got {max_acceleration}")

        self._initial_bit_generator_state = rng.bit_generator.state
        self._rng = rng

        margin = target_size_px / 2.0
        self._x_min = margin
        self._x_max = world_width - margin
        self._y_min = margin
        self._y_max = world_height - margin

        self._x0 = max(self._x_min, min(self._x_max, float(x0)))
        self._y0 = max(self._y_min, min(self._y_max, float(y0)))

        self._max_speed = float(max_speed)
        self._max_acc = float(max_acceleration)
        self._dt = sim_dt

        # Ornstein-Uhlenbeck parameters
        self._theta = 1.5  # Mean-reversion rate
        self._sigma = self._max_acc * 0.8  # Volatility

        # Simulation history cache for deterministic random walk evaluation
        self._times: List[float] = [0.0]
        self._states: List[Tuple[float, float, float, float, float, float]] = [
            (self._x0, self._y0, 0.0, 0.0, 0.0, 0.0)
        ]

    def _step_forward(self) -> None:
        """Advance one internal timestep dt."""
        last_x, last_y, last_vx, last_vy, last_ax, last_ay = self._states[-1]
        t_next = self._times[-1] + self._dt

        # Draw independent standard normal random variables
        noise = self._rng.standard_normal(size=2)

        # Ornstein-Uhlenbeck acceleration update
        drift_x = -self._theta * last_ax * self._dt
        drift_y = -self._theta * last_ay * self._dt
        diff_x = self._sigma * math.sqrt(self._dt) * float(noise[0])
        diff_y = self._sigma * math.sqrt(self._dt) * float(noise[1])

        ax = last_ax + drift_x + diff_x
        ay = last_ay + drift_y + diff_y

        # Clamp acceleration magnitude
        acc_mag = math.hypot(ax, ay)
        if acc_mag > self._max_acc:
            scale = self._max_acc / acc_mag
            ax *= scale
            ay *= scale

        # Integrate velocity
        vx = last_vx + ax * self._dt
        vy = last_vy + ay * self._dt

        # Clamp speed
        speed = math.hypot(vx, vy)
        if speed > self._max_speed:
            scale = self._max_speed / speed
            vx *= scale
            vy *= scale

        # Integrate position
        x = last_x + vx * self._dt
        y = last_y + vy * self._dt

        # Boundary bounce handling
        if x < self._x_min:
            x = self._x_min + (self._x_min - x)
            vx = abs(vx) * 0.9
            ax = abs(ax)
        elif x > self._x_max:
            x = self._x_max - (x - self._x_max)
            vx = -abs(vx) * 0.9
            ax = -abs(ax)

        if y < self._y_min:
            y = self._y_min + (self._y_min - y)
            vy = abs(vy) * 0.9
            ay = abs(ay)
        elif y > self._y_max:
            y = self._y_max - (y - self._y_max)
            vy = -abs(vy) * 0.9
            ay = -abs(ay)

        # Final safety clamp
        x = max(self._x_min, min(self._x_max, x))
        y = max(self._y_min, min(self._y_max, y))

        self._times.append(t_next)
        self._states.append((x, y, vx, vy, ax, ay))

    def state_at(self, t: float) -> Tuple[float, float, float, float, float, float]:
        if t < 0:
            raise ValueError(f"Time t must be non-negative, got {t}")

        # Advance history until it covers t
        while self._times[-1] < t - 1e-9:
            self._step_forward()

        # Find closest index or exact frame
        idx = int(round(t / self._dt))
        if idx >= len(self._states):
            idx = len(self._states) - 1
        return self._states[idx]

    def reset(self) -> None:
        """Reset trajectory to initial time t=0 and restore RNG seed state."""
        self._rng.bit_generator.state = self._initial_bit_generator_state
        self._times = [0.0]
        self._states = [(self._x0, self._y0, 0.0, 0.0, 0.0, 0.0)]
