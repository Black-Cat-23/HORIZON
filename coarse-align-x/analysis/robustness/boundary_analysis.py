"""
Boundary Analysis Module
========================
Classifies 2D robustness parameter grid cells into STABLE, DEGRADED, or FAILURE operational states.
"""

from __future__ import annotations
from enum import Enum
from typing import Any, Dict


class RobustnessRegion(str, Enum):
    STABLE = "STABLE"
    DEGRADED = "DEGRADED"
    FAILURE = "FAILURE"


class BoundaryAnalyzer:
    """Classifies operational region based on mean error and lock retention."""

    @staticmethod
    def classify_region(mean_error: float, lock_retention: float) -> RobustnessRegion:
        if mean_error < 15.0 and lock_retention > 0.8:
            return RobustnessRegion.STABLE
        elif mean_error < 50.0 and lock_retention > 0.3:
            return RobustnessRegion.DEGRADED
        else:
            return RobustnessRegion.FAILURE
