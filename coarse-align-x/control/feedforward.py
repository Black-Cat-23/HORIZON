"""
Target Velocity Feed-Forward & S-Curve Jerk-Limited Controller.
HORIZON Phase 6 & SOTA Part E Upgrade
"""

from __future__ import annotations

import math
from typing import Tuple
import numpy as np


class VelocityFeedForward:
    """
    Velocity feed-forward term calculating rate additions from estimated target angular velocity.
    Disabled by default until explicitly enabled/validated.
    """

    def __init__(self, kff_pan: float = 1.0, kff_tilt: float = 1.0, enabled: bool = True):
        self.kff_pan = kff_pan
        self.kff_tilt = kff_tilt
        self.enabled = enabled

    def compute(self, estimated_pan_vel_deg_s: float, estimated_tilt_vel_deg_s: float) -> Tuple[float, float]:
        """
        Computes velocity feed-forward rate output (deg/s).
        """
        if not self.enabled:
            return (0.0, 0.0)

        ff_pan = self.kff_pan * estimated_pan_vel_deg_s
        ff_tilt = self.kff_tilt * estimated_tilt_vel_deg_s
        return (ff_pan, ff_tilt)


class SCurveFeedForward:
    """3rd-order Jerk-Limited S-Curve Feedforward Command Profiler.

    Enforces maximum acceleration and maximum jerk limits to eliminate motor chatter
    and optical gimbal overshoot during Search -> Acquire -> Track mode transitions.
    """

    def __init__(
        self,
        kff_pan: float = 1.0,
        kff_tilt: float = 1.0,
        max_accel_deg_s2: float = 360.0,
        max_jerk_deg_s3: float = 1200.0,
        enabled: bool = True,
    ) -> None:
        self.kff_pan = kff_pan
        self.kff_tilt = kff_tilt
        self.max_accel = max_accel_deg_s2
        self.max_jerk = max_jerk_deg_s3
        self.enabled = enabled

        self._current_v_pan = 0.0
        self._current_v_tilt = 0.0
        self._current_a_pan = 0.0
        self._current_a_tilt = 0.0

    def reset(self) -> None:
        self._current_v_pan = 0.0
        self._current_v_tilt = 0.0
        self._current_a_pan = 0.0
        self._current_a_tilt = 0.0

    def compute(
        self,
        target_pan_vel_deg_s: float,
        target_tilt_vel_deg_s: float,
        dt: float = 0.01,
    ) -> Tuple[float, float]:
        """Compute S-curve jerk-limited velocity feedforward outputs (deg/s)."""
        if not self.enabled or dt <= 0.0:
            return (0.0, 0.0)

        # Pan axis S-curve profiling with square-root deceleration braking curve
        des_v_pan = self.kff_pan * target_pan_vel_deg_s
        e_v_pan = des_v_pan - self._current_v_pan
        a_limit_pan = math.sqrt(max(0.0, 2.0 * self.max_jerk * abs(e_v_pan)))
        target_a_pan = math.copysign(min(self.max_accel, a_limit_pan), e_v_pan)

        da_pan = float(np.clip(target_a_pan - self._current_a_pan, -self.max_jerk * dt, self.max_jerk * dt))
        self._current_a_pan += da_pan
        self._current_v_pan += self._current_a_pan * dt

        # Tilt axis S-curve profiling
        des_v_tilt = self.kff_tilt * target_tilt_vel_deg_s
        e_v_tilt = des_v_tilt - self._current_v_tilt
        a_limit_tilt = math.sqrt(max(0.0, 2.0 * self.max_jerk * abs(e_v_tilt)))
        target_a_tilt = math.copysign(min(self.max_accel, a_limit_tilt), e_v_tilt)

        da_tilt = float(np.clip(target_a_tilt - self._current_a_tilt, -self.max_jerk * dt, self.max_jerk * dt))
        self._current_a_tilt += da_tilt
        self._current_v_tilt += self._current_a_tilt * dt

        return (self._current_v_pan, self._current_v_tilt)
