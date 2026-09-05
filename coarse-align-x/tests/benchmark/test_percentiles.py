"""
Unit tests for percentile calculations.
"""

from benchmark.metrics import compute_percentiles


def test_percentiles_calculation():
    values = list(range(1, 101))  # 1 to 100
    res = compute_percentiles(values)

    assert abs(res["p50"] - 50.5) < 1.0
    assert abs(res["p95"] - 95.05) < 1.0
    assert res["max"] == 100.0
