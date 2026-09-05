"""
Unit tests for Empirical CDF and Histogram calculations.
"""

from analysis.distributions import compute_ecdf, compute_histogram_bins


def test_ecdf_calculation():
    vals = [3.0, 1.0, 4.0, 2.0]
    x_s, y_s = compute_ecdf(vals)

    assert x_s == [1.0, 2.0, 3.0, 4.0]
    assert y_s == [0.25, 0.5, 0.75, 1.0]


def test_histogram_bins():
    vals = list(range(100))
    res = compute_histogram_bins(vals, num_bins=10)

    assert len(res["counts"]) == 10
    assert len(res["bin_edges"]) == 11
