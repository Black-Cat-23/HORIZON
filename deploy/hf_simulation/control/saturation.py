"""
Controller Actuator Saturation Limiter.
HORIZON Phase 6
"""

from typing import Tuple, Dict, Any
import numpy as np


class ControllerSaturation:
    """
    Enforces physical gimbal pan/tilt rate saturation limits and logs saturation events.
    Default max rates: max pan = 5.0 deg/s, max tilt = 5.0 deg/s.
    """

    def __init__(self, max_pan_rate_deg_s: float = 20.0, max_tilt_rate_deg_s: float = 20.0):
        self.max_pan_rate = max_pan_rate_deg_s
        self.max_tilt_rate = max_tilt_rate_deg_s
        self.saturation_count = 0

    def apply(self, pan_rate_deg_s: float, tilt_rate_deg_s: float) -> Tuple[float, float, bool]:
        """
        Clamps commanded pan and tilt rates to configured maximum physical limits.
        
        Returns:
            Tuple[actual_pan_rate, actual_tilt_rate, is_saturated]
        """
        clamped_pan = float(np.clip(pan_rate_deg_s, -self.max_pan_rate, self.max_pan_rate))
        clamped_tilt = float(np.clip(tilt_rate_deg_s, -self.max_tilt_rate, self.max_tilt_rate))

        is_saturated = (abs(clamped_pan - pan_rate_deg_s) > 1e-4) or (abs(clamped_tilt - tilt_rate_deg_s) > 1e-4)
        if is_saturated:
            self.saturation_count += 1

        return (clamped_pan, clamped_tilt, is_saturated)
