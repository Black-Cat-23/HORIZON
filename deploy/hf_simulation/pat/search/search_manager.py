"""
Search Strategy Manager.
HORIZON Phase 6
"""

from typing import Dict, Tuple, List, Optional
from .base import SearchStrategy
from .raster import RasterSearchStrategy
from .spiral import SpiralSearchStrategy
from .belief_map import BeliefMapSearchStrategy


class SearchManager:
    """Manages active search strategies (SPIRAL, RASTER, BELIEF_MAP) and coordinates pattern resets."""

    def __init__(self):
        self.strategies: Dict[str, SearchStrategy] = {
            "SPIRAL": SpiralSearchStrategy(),
            "RASTER": RasterSearchStrategy(),
            "BELIEF_MAP": BeliefMapSearchStrategy(),
        }
        self.active_strategy_name: str = "SPIRAL"

    def set_active_strategy(self, name: str) -> None:
        if name in self.strategies:
            self.active_strategy_name = name

    def reset_active_strategy(self, center_pan_deg: float = 0.0, center_tilt_deg: float = 0.0) -> None:
        current = self.get_active_strategy()
        if current:
            current.reset(center_pan_deg, center_tilt_deg)

    def get_active_strategy(self) -> Optional[SearchStrategy]:
        return self.strategies.get(self.active_strategy_name)

    def update_belief(
        self,
        candidate_pan_deg: float,
        candidate_tilt_deg: float,
        confidence: float,
        uncertainty_deg: float = 0.5,
    ) -> None:
        """Forwards evidence updates to the currently active search strategy."""
        strategy = self.get_active_strategy()
        if strategy:
            strategy.update_belief(candidate_pan_deg, candidate_tilt_deg, confidence, uncertainty_deg)

    def get_command(self, dt: float, current_pan_deg: float, current_tilt_deg: float) -> Tuple[float, float]:
        strategy = self.get_active_strategy()
        if strategy:
            return strategy.next_command(dt, current_pan_deg, current_tilt_deg)
        return (0.0, 0.0)

    def get_trajectory_history(self) -> List[Tuple[float, float]]:
        strategy = self.get_active_strategy()
        if strategy:
            return strategy.get_trajectory_history()
        return []
