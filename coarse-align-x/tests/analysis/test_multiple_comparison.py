"""
Test Multiple Comparison Correction & Robustness Grid
"""
from analysis.statistics.correction import MultipleComparisonCorrection
from analysis.robustness.boundary_analysis import BoundaryAnalyzer, RobustnessRegion

def test_bh_correction():
    p_vals = [0.01, 0.04, 0.03]
    res = MultipleComparisonCorrection.benjamini_hochberg(p_vals)
    assert len(res) == 3

def test_boundary_analyzer():
    reg = BoundaryAnalyzer.classify_region(5.0, 0.9)
    assert reg == RobustnessRegion.STABLE
