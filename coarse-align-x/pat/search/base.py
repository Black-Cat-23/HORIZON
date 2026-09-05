"""
Abstract Base Class for PAT Search Strategies.
HORIZON Phase 6
"""

from abc import ABC, abstractmethod
from typing import Tuple, List, Dict, Any


class SearchStrategy(ABC):
    """
    Common interface for camera search strategies (Raster, Spiral, etc.).
    Search strategies generate actual angular rate commands (pan_rate_deg_s, tilt_rate_deg_s).
    """

    @abstractmethod
    def next_command(self, dt: float, current_pan_deg: float, current_tilt_deg: float) -> Tuple[float, float]:
        """
        Calculates commanded pan and tilt rates (deg/s) for the next timestep dt.
        
        Args:
            dt: Time step in seconds.
            current_pan_deg: Current camera pan position in degrees.
            current_tilt_deg: Current camera tilt position in degrees.
            
        Returns:
            Tuple[commanded_pan_rate_deg_s, commanded_tilt_rate_deg_s]
        """
        pass

    @abstractmethod
    def reset(self, center_pan_deg: float = 0.0, center_tilt_deg: float = 0.0) -> None:
        """
        Resets search pattern state around a specified angular center.
        """
        pass

    @abstractmethod
    def is_complete(self) -> bool:
        """
        Returns True if the search pattern has completed a full coverage cycle.
        """
        pass

    @abstractmethod
    def get_trajectory_history(self) -> List[Tuple[float, float]]:
        """
        Returns the planned trajectory points in angular coordinate space (pan_deg, tilt_deg) for visualization.
        """
        pass
