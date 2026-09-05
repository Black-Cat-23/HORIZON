"""
Target Velocity Feed-Forward Controller.
HORIZON Phase 6
"""

from typing import Tuple


class VelocityFeedForward:
    """
    Velocity feed-forward term calculating rate additions from estimated target angular velocity.
    Disabled by default until explicitly enabled/validated.
    """

    def __init__(self, kff_pan: float = 0.5, kff_tilt: float = 0.5, enabled: bool = False):
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
