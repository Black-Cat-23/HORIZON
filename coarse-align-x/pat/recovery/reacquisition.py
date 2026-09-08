"""
Reacquisition Manager with Adaptive Search Support.
HORIZON Phase 6
"""

from __future__ import annotations

from typing import Optional, Tuple
from ..thresholds import PATThresholds
from ..search.base import SearchStrategy
from ..search.spiral import SpiralSearchStrategy
from ..search.belief_map import BeliefMapSearchStrategy


class ReacquisitionManager:
    """
    Manages recovery and target reacquisition when tracking is lost.
    Initiates localized search (Spiral or Adaptive Bayesian Belief-Map) around
    predicted target location and last-known covariance bounds.
    """

    def __init__(
        self,
        thresholds: Optional[PATThresholds] = None,
        strategy_type: str = "SPIRAL",
    ):
        self.thresholds = thresholds or PATThresholds()
        self.strategy_type = strategy_type

        if strategy_type == "BELIEF_MAP":
            self.search_strategy: SearchStrategy = BeliefMapSearchStrategy(
                span_pan_deg=6.0,
                span_tilt_deg=4.5,
                scan_speed_deg_s=2.5,
                prior_sigma_deg=1.2,
                discount_rate=0.4,
                evidence_gain=3.5,
                max_search_time_s=self.thresholds.reacquire_timeout_s,
            )
        else:
            self.search_strategy = SpiralSearchStrategy(
                initial_radius_deg=0.3,
                radius_step_deg=0.5,
                max_radius_deg=3.5,
                angular_rate_rad_s=2.0,
            )

        self.active = False
        self.reacquire_duration_s = 0.0
        self.attempt_count = 0

    def start_reacquisition(
        self,
        center_pan_deg: float,
        center_tilt_deg: float,
        uncertainty_deg: float = 1.0,
    ) -> None:
        """
        Starts reacquisition search centered at the predicted/last-known target position.
        """
        self.active = True
        self.reacquire_duration_s = 0.0
        self.attempt_count += 1
        self.search_strategy.reset(center_pan_deg, center_tilt_deg)
        if isinstance(self.search_strategy, BeliefMapSearchStrategy):
            self.search_strategy.prior_sigma_deg = max(0.5, uncertainty_deg)

    def update_evidence(
        self,
        candidate_pan_deg: float,
        candidate_tilt_deg: float,
        confidence: float,
        uncertainty_deg: float = 0.5,
    ) -> None:
        """Forwards weak candidate cues to update reacquisition belief map."""
        if self.active and hasattr(self.search_strategy, "update_belief"):
            self.search_strategy.update_belief(
                candidate_pan_deg, candidate_tilt_deg, confidence, uncertainty_deg
            )

    def process_step(
        self,
        dt: float,
        current_pan_deg: float,
        current_tilt_deg: float,
    ) -> Tuple[float, float, bool]:
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
