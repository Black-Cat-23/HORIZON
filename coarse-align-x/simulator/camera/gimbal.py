"""
HORIZON Camera Gimbal & Actuator Rate Limiter
=====================================================
Physical actuator model enforcing strict rate and acceleration constraints
on camera pan and tilt axes.
"""

from __future__ import annotations

import math
from typing import Optional, Tuple


class CameraGimbal:
    """Pan/Tilt camera gimbal mechanism with physical velocity and acceleration limits.

    Parameters:
        rate_limit_deg_s: Maximum slew rate in deg/s (default 5.0 deg/s).
        accel_limit_deg_s2: Maximum slew acceleration in deg/s² (default 50.0 deg/s²).
        initial_pan_deg: Initial pan angle (0 = pointing center).
        initial_tilt_deg: Initial tilt angle (0 = pointing center).
    """

    def __init__(
        self,
        rate_limit_deg_s: float = 5.0,
        accel_limit_deg_s2: Optional[float] = 50.0,
        initial_pan_deg: float = 0.0,
        initial_tilt_deg: float = 0.0,
    ) -> None:
        if rate_limit_deg_s <= 0:
            raise ValueError(f"rate_limit_deg_s must be positive, got {rate_limit_deg_s}")
        if accel_limit_deg_s2 is not None and accel_limit_deg_s2 <= 0:
            raise ValueError(f"accel_limit_deg_s2 must be positive, got {accel_limit_deg_s2}")

        self._rate_limit = float(rate_limit_deg_s)
        self._accel_limit = float(accel_limit_deg_s2) if accel_limit_deg_s2 else None

        self._pan_deg = float(initial_pan_deg)
        self._tilt_deg = float(initial_tilt_deg)

        self._actual_pan_rate = 0.0
        self._actual_tilt_rate = 0.0

        self._commanded_pan_rate = 0.0
        self._commanded_tilt_rate = 0.0

    @property
    def rate_limit(self) -> float:
        return self._rate_limit

    @property
    def accel_limit(self) -> Optional[float]:
        return self._accel_limit

    @property
    def pan_deg(self) -> float:
        return self._pan_deg

    @property
    def tilt_deg(self) -> float:
        return self._tilt_deg

    @property
    def actual_pan_rate(self) -> float:
        return self._actual_pan_rate

    @property
    def actual_tilt_rate(self) -> float:
        return self._actual_tilt_rate

    @property
    def commanded_pan_rate(self) -> float:
        return self._commanded_pan_rate

    @property
    def commanded_tilt_rate(self) -> float:
        return self._commanded_tilt_rate

    def set_rate_command(self, pan_rate_deg_s: float, tilt_rate_deg_s: float) -> None:
        """Issue target rate command (deg/s) to the gimbal axes."""
        self._commanded_pan_rate = float(pan_rate_deg_s)
        self._commanded_tilt_rate = float(tilt_rate_deg_s)

    def step(self, dt: float) -> None:
        """Advance gimbal physical state by timestep dt, applying rate and acceleration limits."""
        if dt <= 0:
            raise ValueError(f"Timestep dt must be positive, got {dt}")

        # 1. Clamp target rates to physical speed limits
        target_pan_rate = max(-self._rate_limit, min(self._rate_limit, self._commanded_pan_rate))
        target_tilt_rate = max(-self._rate_limit, min(self._rate_limit, self._commanded_tilt_rate))

        # 2. Apply acceleration limits if configured
        if self._accel_limit is not None:
            max_delta_rate = self._accel_limit * dt

            delta_pan = target_pan_rate - self._actual_pan_rate
            delta_pan_clamped = max(-max_delta_rate, min(max_delta_rate, delta_pan))
            self._actual_pan_rate += delta_pan_clamped

            delta_tilt = target_tilt_rate - self._actual_tilt_rate
            delta_tilt_clamped = max(-max_delta_rate, min(max_delta_rate, delta_tilt))
            self._actual_tilt_rate += delta_tilt_clamped
        else:
            self._actual_pan_rate = target_pan_rate
            self._actual_tilt_rate = target_tilt_rate

        # Final safety clamp on actual rate
        self._actual_pan_rate = max(-self._rate_limit, min(self._rate_limit, self._actual_pan_rate))
        self._actual_tilt_rate = max(-self._rate_limit, min(self._rate_limit, self._actual_tilt_rate))

        # 3. Integrate position continuously (no teleportation)
        self._pan_deg += self._actual_pan_rate * dt
        self._tilt_deg += self._actual_tilt_rate * dt

    def reset(self, pan_deg: float = 0.0, tilt_deg: float = 0.0) -> None:
        """Reset gimbal angles and rates."""
        self._pan_deg = float(pan_deg)
        self._tilt_deg = float(tilt_deg)
        self._actual_pan_rate = 0.0
        self._actual_tilt_rate = 0.0
        self._commanded_pan_rate = 0.0
        self._commanded_tilt_rate = 0.0
