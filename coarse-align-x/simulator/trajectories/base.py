"""
HORIZON Trajectory Base Interface
=========================================
Abstract base class for all target motion trajectories.
Trajectories define target dynamics in continuous time.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Tuple


class Trajectory(ABC):
    """Abstract interface for all target trajectories.

    Encapsulates target motion kinematics. Has no awareness of rendering,
    cameras, detectors, or UI components.
    """

    @abstractmethod
    def state_at(self, t: float) -> Tuple[float, float, float, float, float, float]:
        """Compute target kinematic state at simulation time t.

        Args:
            t: Simulation timestamp in seconds (t >= 0).

        Returns:
            Tuple of (x, y, vx, vy, ax, ay):
              - x, y: continuous position in world pixels
              - vx, vy: instantaneous velocity in pixels/second
              - ax, ay: instantaneous acceleration in pixels/second²
        """
        pass

    @abstractmethod
    def reset(self) -> None:
        """Reset internal state if the trajectory maintains state (e.g., random walk)."""
        pass
