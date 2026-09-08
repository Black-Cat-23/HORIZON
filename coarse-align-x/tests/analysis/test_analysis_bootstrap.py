"""
Test Analysis Bootstrap & Confidence Intervals
"""
from analysis.statistics.bootstrap import DeterministicBootstrap
from analysis.statistics.confidence_intervals import ConfidenceIntervals

def test_analysis_bootstrap():
    data = [1.0, 2.0, 3.0, 4.0, 5.0]
    low, high = DeterministicBootstrap.bootstrap_ci(data, num_samples=100, seed=42)
    assert low <= high

def test_wilson_ci():
    low, high = ConfidenceIntervals.wilson_score_interval(5, 10)
    assert 0.0 <= low <= high <= 1.0
