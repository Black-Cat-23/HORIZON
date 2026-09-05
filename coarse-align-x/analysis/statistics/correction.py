"""
Multiple Comparison Correction Module
======================================
Applies Benjamini-Hochberg False Discovery Rate (FDR) control (alpha=0.05).
"""

from __future__ import annotations
from typing import List, Tuple
import numpy as np


class MultipleComparisonCorrection:
    """Applies Benjamini-Hochberg FDR procedure for p-value adjustment."""

    @staticmethod
    def benjamini_hochberg(p_values: List[float], alpha: float = 0.05) -> List[Tuple[float, bool]]:
        n = len(p_values)
        if n == 0:
            return []

        sorted_indices = np.argsort(p_values)
        sorted_p = np.array(p_values)[sorted_indices]

        adjusted_p = np.zeros(n)
        for i in range(n - 1, -1, -1):
            rank = i + 1
            val = sorted_p[i] * n / rank
            if i == n - 1:
                adjusted_p[i] = min(1.0, val)
            else:
                adjusted_p[i] = min(1.0, val, adjusted_p[i + 1])

        reordered_adjusted = np.zeros(n)
        reordered_adjusted[sorted_indices] = adjusted_p

        return [(float(adj), bool(adj <= alpha)) for adj in reordered_adjusted]
