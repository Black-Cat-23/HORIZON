"""
Effect Size Module
==================
Calculates Cohen's d and Cliff's delta effect sizes.
"""

from __future__ import annotations
import math
from typing import Sequence
import numpy as np


class EffectSize:
    """Calculates standardized effect sizes for comparative distributions."""

    @staticmethod
    def cohens_d(a: Sequence[float], b: Sequence[float]) -> float:
        if len(a) < 2 or len(b) < 2:
            return 0.0
        arr_a = np.array(a, dtype=np.float64)
        arr_b = np.array(b, dtype=np.float64)

        mean_a, mean_b = np.mean(arr_a), np.mean(arr_b)
        var_a, var_b = np.var(arr_a, ddof=1), np.var(arr_b, ddof=1)

        pooled_std = math.sqrt(((len(arr_a) - 1) * var_a + (len(arr_b) - 1) * var_b) / (len(arr_a) + len(arr_b) - 2))
        if pooled_std == 0.0:
            return 0.0
        return float((mean_a - mean_b) / pooled_std)

    @staticmethod
    def interpret_cohens_d(d: float) -> str:
        abs_d = abs(d)
        if abs_d < 0.2:
            return "Negligible"
        elif abs_d < 0.5:
            return "Small"
        elif abs_d < 0.8:
            return "Medium"
        else:
            return "Large"
