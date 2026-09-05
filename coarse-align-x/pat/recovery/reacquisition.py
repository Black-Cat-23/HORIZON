"""
Reacquisition Manager.
HORIZON Phase 6
"""

from typing import Optional, Tuple
from ..thresholds import PATThresholds
from ..search.spiral import SpiralSearchStrategy


class ReacquisitionManager:
    """
    Manages recovery and target reacquisition when tracking is lost.
    Initiates localized spiral search around predicted target location and last-known state.
    """

    def __init__(self, thresholds: Optional[PATThresholds] = None):
        self.thresholds = thresholds or PATThresholds()
        self.search_strategy = SpiralSearchStrategy(
            initial_radius_deg=0.3,
            radius_step_deg=0.5,
            max_radius_deg=3.5,
            angular_rate_rad_s=2.0,
        )
        self.active = False
        self.reacquire_duration_s = 0.0
        self.attempt_count = 0

    def start_reacquisition(self, center_pan_deg: float, center_tilt_deg: float) -> None:
        """
        Starts reacquisition search centered at the predicted/last-known target position.
        """
        self.active = True
        self.reacquire_duration_s = 0.0
        self.attempt_count += 1
        self.search_strategy.reset(center_pan_deg, center_tilt_deg)

    def process_step(self, dt: float, current_pan_deg: float, current_tilt_deg: float) -> Tuple[float, float, bool]:
        """
        Updates reacquisition search timers and generates search rate commands.
        
        Returns:
            Tuple[pan_rate_deg_s, tilt_rate_deg_s, is_timed_out]
        """
        if not self.active:
            return (0.0, 0.0, False)

        self.reacquire_duration_s += dt

        if self.reacquire_duration_s >= self.thresholds.reacquire_timeout_s or self.search_strategy.is_complete():
            self.active = False
            return (0.0, 0.0, True)

        pan_rate, tilt_rate = self.search_strategy.next_command(dt, current_pan_deg, current_tilt_deg)
        return (pan_rate, tilt_rate, False)

    def reset(self) -> None:
        self.active = False
        self.reacquire_duration_s = 0.0
        self.attempt_count = 0
