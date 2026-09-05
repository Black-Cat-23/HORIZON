"""
Unit tests for Binomial Wilson score confidence intervals.
"""

from benchmark.metrics import compute_binomial_ci


def test_binomial_confidence_interval():
    p, lo, hi = compute_binomial_ci(successes=90, total=100, confidence=0.95)
    assert p == 0.9
    assert 0.8 < lo < 0.9
    assert 0.9 < hi < 0.96
