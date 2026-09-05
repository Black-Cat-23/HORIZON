"""
HORIZON Target State Model
==================================
Ground-truth target state representation in continuous floating-point
world pixel coordinates.

Strict constraint: GROUND TRUTH ONLY.
No detected/estimated values, confidence, Kalman states, or controller outputs.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TargetState:
    """Ground truth state of a target beacon at a specific point in time.

    Coordinates are in world pixels:
      - Coordinate origin: top-left (0, 0)
      - +X: right
      - +Y: down

    Attributes:
        target_id: Unique identifier for the target (e.g. 1).
        timestamp: Simulation time in seconds.
        x: Continuous X position in world pixels.
        y: Continuous Y position in world pixels.
        vx: X velocity in pixels per second.
        vy: Y velocity in pixels per second.
        ax: X acceleration in pixels per second squared.
        ay: Y acceleration in pixels per second squared.
        visible: Boolean flag indicating if target is optically active/visible.
    """
    target_id: int
    timestamp: float
    x: float
    y: float
    vx: float
    vy: float
    ax: float
    ay: float
    visible: bool = True

    @property
    def speed(self) -> float:
        """Current scalar speed in pixels per second."""
        return (self.vx ** 2 + self.vy ** 2) ** 0.5

    @property
    def acceleration_magnitude(self) -> float:
        """Current scalar acceleration magnitude in pixels/s²."""
        return (self.ax ** 2 + self.ay ** 2) ** 0.5
