"""
Test Paired Statistics & Effect Size
"""
from analysis.statistics.paired_tests import PairedTests
from analysis.statistics.effect_size import EffectSize

def test_paired_statistics():
    a = [10.0, 12.0, 11.0]
    b = [20.0, 22.0, 21.0]
    p_val = PairedTests.paired_bootstrap_test(a, b, num_samples=100)
    assert p_val >= 0.0

def test_effect_size():
    a = [10.0, 12.0, 11.0]
    b = [20.0, 22.0, 21.0]
    d = EffectSize.cohens_d(a, b)
    assert abs(d) > 0.0
