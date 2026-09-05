"""
Confidence Intervals Module
============================
Wilson Score Binomial 95% CIs and continuous percentile CIs.
"""

from __future__ import annotations
import math
from typing import Tuple


class ConfidenceIntervals:
    """Calculates Wilson Score Binomial Confidence Intervals for proportions."""

    @staticmethod
    def wilson_score_interval(successes: int, total: int, z: float = 1.96) -> Tuple[float, float]:
        if total <= 0:
            return 0.0, 0.0
        p = successes / total
        denominator = 1.0 + (z**2) / total
        centre = (p + (z**2) / (2 * total)) / denominator
        spread = (z / denominator) * math.sqrt((p * (1.0 - p) / total) + ((z**2) / (4 * (total**2))))
        lower = max(0.0, centre - spread)
        upper = min(1.0, centre + spread)
        return lower, upper
