"""
HORIZON Platform Motion Engine
=====================================
Models physical mobile platform motion (e.g., UAV, satellite, naval mast vibration)
creating continuous, stateful displacement of the camera observation frame.

Conforms strictly to official SIH26169 specifications:
  - Maximum per-frame displacement: ±20.0 pixels per frame.
  - Mandatory continuous model: Linear.
  - Optional models: Circular, Random (Ornstein-Uhlenbeck), Spiral, Figure-8.
  - Stateful telemetry:
      platform_offset_x, platform_offset_y
      platform_velocity_x, platform_velocity_y
  - Does NOT alter ground-truth target kinematics or camera gimbal angles.
"""

from __future__ import annotations

import math
from typing import Optional, Tuple
import cv2
import numpy as np

from simulator.disturbances.config import PlatformMotionConfig


class PlatformMotionEngine:
    """Stateful platform motion disturbance engine.

    Parameters:
        config: Validated PlatformMotionConfig.
        rng: Deterministic NumPy Generator child stream.
    """

    def __init__(self, config: PlatformMotionConfig, rng: np.random.Generator) -> None:
        self._config = config
        self._rng = rng

        # Continuous state
        self._offset_x: float = 0.0
        self._offset_y: float = 0.0
        self._vx: float = float(config.velocity_x)
        self._vy: float = float(config.velocity_y)

        # For random Ornstein-Uhlenbeck walk if selected
        self._ou_acc_x: float = 0.0
        self._ou_acc_y: float = 0.0

    @property
    def offset_x(self) -> float:
        return self._offset_x

    @property
    def offset_y(self) -> float:
        return self._offset_y

    @property
    def velocity_x(self) -> float:
        return self._vx

    @property
    def velocity_y(self) -> float:
        return self._vy

    def reset(self) -> None:
        """Reset platform motion states to initial conditions."""
        self._offset_x = 0.0
        self._offset_y = 0.0
        self._vx = float(self._config.velocity_x)
        self._vy = float(self._config.velocity_y)
        self._ou_acc_x = 0.0
        self._ou_acc_y = 0.0

    def step(
        self, frame: np.ndarray, dt: float, sim_time: float
    ) -> Tuple[np.ndarray, float, float, float, float]:
        """Advance platform motion state by dt and apply cumulative translation.

        Args:
            frame: Grayscale sensor frame (480×640).
            dt: Timestep duration in seconds.
            sim_time: Current simulation elapsed time in seconds.

        Returns:
            Tuple of (displaced_frame, offset_x, offset_y, vx, vy)
        """
        if not self._config.enabled or dt <= 0.0:
            return frame.copy(), self._offset_x, self._offset_y, self._vx, self._vy

        model = self._config.model.lower()
        max_step_x = min(float(self._config.max_dx_px_per_frame), 20.0)
        max_step_y = min(float(self._config.max_dy_px_per_frame), 20.0)
        bound_limit = float(self._config.boundary_limit_px)

        if model == "linear":
            # Continuous linear motion with bounce off boundary limit
            step_dx = self._vx * dt
            step_dy = self._vy * dt

            # Clamp per-frame step to official ±20 px limit
            step_dx = max(min(step_dx, max_step_x), -max_step_x)
            step_dy = max(min(step_dy, max_step_y), -max_step_y)

            self._offset_x += step_dx
            self._offset_y += step_dy

            # Boundary bounce to keep platform continuous
            if abs(self._offset_x) > bound_limit:
                self._vx = -self._vx
                self._offset_x = math.copysign(bound_limit, self._offset_x)
            if abs(self._offset_y) > bound_limit:
                self._vy = -self._vy
                self._offset_y = math.copysign(bound_limit, self._offset_y)

        elif model == "circular":
            # Circular platform drift: r * cos(w * t)
            omega = 1.0  # rad/s PROJECT DEFAULT
            radius = min(bound_limit, 50.0)
            target_ox = radius * math.cos(omega * sim_time)
            target_oy = radius * math.sin(omega * sim_time)

            step_dx = max(min(target_ox - self._offset_x, max_step_x), -max_step_x)
            step_dy = max(min(target_oy - self._offset_y, max_step_y), -max_step_y)
            self._offset_x += step_dx
            self._offset_y += step_dy
            self._vx = step_dx / dt if dt > 0 else 0.0
            self._vy = step_dy / dt if dt > 0 else 0.0

        elif model == "figure8":
            # Figure-8 platform sway
            omega = 0.8
            ax = min(bound_limit, 40.0)
            ay = min(bound_limit, 25.0)
            target_ox = ax * math.sin(omega * sim_time)
            target_oy = ay * math.sin(2.0 * omega * sim_time)

            step_dx = max(min(target_ox - self._offset_x, max_step_x), -max_step_x)
            step_dy = max(min(target_oy - self._offset_y, max_step_y), -max_step_y)
            self._offset_x += step_dx
            self._offset_y += step_dy
            self._vx = step_dx / dt if dt > 0 else 0.0
            self._vy = step_dy / dt if dt > 0 else 0.0

        elif model == "spiral":
            # Expanding/contracting spiral
            w = 1.5
            r = (math.sin(0.2 * sim_time) ** 2) * min(bound_limit, 40.0)
            target_ox = r * math.cos(w * sim_time)
            target_oy = r * math.sin(w * sim_time)

            step_dx = max(min(target_ox - self._offset_x, max_step_x), -max_step_x)
            step_dy = max(min(target_oy - self._offset_y, max_step_y), -max_step_y)
            self._offset_x += step_dx
            self._offset_y += step_dy
            self._vx = step_dx / dt if dt > 0 else 0.0
            self._vy = step_dy / dt if dt > 0 else 0.0

        elif model == "random":
            # Continuous random Ornstein-Uhlenbeck platform sway
            theta = 2.0
            sigma = 40.0
            self._ou_acc_x += -theta * self._ou_acc_x * dt + sigma * math.sqrt(dt) * float(self._rng.normal(0, 1))
            self._ou_acc_y += -theta * self._ou_acc_y * dt + sigma * math.sqrt(dt) * float(self._rng.normal(0, 1))

            step_dx = self._ou_acc_x * dt
            step_dy = self._ou_acc_y * dt
            step_dx = max(min(step_dx, max_step_x), -max_step_x)
            step_dy = max(min(step_dy, max_step_y), -max_step_y)

            self._offset_x += step_dx
            self._offset_y += step_dy
            self._vx = step_dx / dt if dt > 0 else 0.0
            self._vy = step_dy / dt if dt > 0 else 0.0

            if abs(self._offset_x) > bound_limit:
                self._offset_x = math.copysign(bound_limit, self._offset_x)
            if abs(self._offset_y) > bound_limit:
                self._offset_y = math.copysign(bound_limit, self._offset_y)

        # Displace observation frame according to platform offset
        h, w = frame.shape[:2]
        m = np.array([[1.0, 0.0, self._offset_x], [0.0, 1.0, self._offset_y]], dtype=np.float32)
        displaced = cv2.warpAffine(
            frame,
            m,
            (w, h),
            flags=cv2.INTER_LINEAR,
            borderMode=cv2.BORDER_CONSTANT,
            borderValue=0,
        )

        return displaced, self._offset_x, self._offset_y, self._vx, self._vy
