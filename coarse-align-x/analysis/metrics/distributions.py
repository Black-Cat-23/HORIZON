"""
Empirical Distribution Module
=============================
Calculates eCDF step functions and histogram density binnings.
"""

from __future__ import annotations
from typing import Any, Dict, List, Sequence, Tuple
import numpy as np


class EmpiricalDistribution:
    """Computes empirical distribution functions and density bins."""

    @staticmethod
    def compute_ecdf(values: Sequence[float]) -> Tuple[np.ndarray, np.ndarray]:
        if not values:
            return np.array([]), np.array([])
        sorted_vals = np.sort(values)
        y = np.arange(1, len(sorted_vals) + 1) / len(sorted_vals)
        return sorted_vals, y

    @staticmethod
    def compute_histogram(values: Sequence[float], bins: int = 20) -> Tuple[np.ndarray, np.ndarray]:
        if not values:
            return np.array([]), np.array([])
        counts, bin_edges = np.histogram(values, bins=bins, density=True)
        return counts, bin_edges


def compute_ecdf(values: List[float] | np.ndarray) -> Tuple[List[float], List[float]]:
    """Compute Empirical Cumulative Distribution Function (eCDF)."""
    arr = np.sort(np.asarray(values, dtype=float))
    n = len(arr)
    if n == 0:
        return [], []

    y = np.arange(1, n + 1) / float(n)
    return arr.tolist(), y.tolist()


def compute_histogram_bins(
    values: List[float] | np.ndarray, num_bins: int = 20
) -> Dict[str, Any]:
    """Compute histogram bin edges and normalized density values."""
    arr = np.asarray(values, dtype=float)
    if len(arr) == 0:
        return {"counts": [], "bin_edges": []}

    counts, bin_edges = np.histogram(arr, bins=num_bins)
    return {
        "counts": counts.tolist(),
        "bin_edges": bin_edges.tolist(),
        "bin_centers": ((bin_edges[:-1] + bin_edges[1:]) / 2.0).tolist(),
    }
