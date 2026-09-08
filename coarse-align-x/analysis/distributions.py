"""
Empirical Distribution Analysis Engine
======================================
Computes Empirical CDFs, histogram binnings, and distribution percentiles for performance vectors.
"""

from analysis.metrics.distributions import compute_ecdf, compute_histogram_bins, EmpiricalDistribution

__all__ = ["compute_ecdf", "compute_histogram_bins", "EmpiricalDistribution"]
