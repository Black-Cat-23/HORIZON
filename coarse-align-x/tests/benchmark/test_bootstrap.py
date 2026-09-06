"""
Unit tests for non-parametric bootstrap confidence intervals.
"""

from benchmark.metrics import compute_bootstrap_ci


def test_bootstrap_confidence_interval():
    data = [10.0, 12.0, 11.0, 10.5, 11.5, 12.5, 9.5, 10.8]
    pt, lo, hi = compute_bootstrap_ci(data, stat_fn="mean", num_samples=500, seed=42)

    assert 10.0 <= pt <= 12.0
    assert lo <= pt <= hi
