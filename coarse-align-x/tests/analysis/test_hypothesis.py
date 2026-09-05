"""
Unit tests for HypothesisTestingEngine.
"""

from analysis.hypothesis import HypothesisTestingEngine


def test_pairwise_comparison():
    errs_a = [10.0, 12.0, 11.0, 10.5, 11.5]
    errs_b = [5.0, 6.0, 5.5, 5.2, 5.8]

    res = HypothesisTestingEngine.compare_algorithm_pair("OURS", errs_b, "B1", errs_a)

    assert res["percentage_improvement"] > 0
    assert abs(res["cohens_d"]) > 0.8  # Large effect size
    assert res["effect_size_label"] == "Large"


def test_battlefield_matrix_fdr():
    data = {
        "OURS": [2.0, 2.5, 2.1, 2.3],
        "B1": [10.0, 12.0, 11.0, 10.5],
        "B0": [300.0, 300.0, 300.0, 300.0],
    }

    res = HypothesisTestingEngine.evaluate_battlefield_matrix(data)
    assert len(res["pairwise_comparisons"]) == 3
    assert all("adjusted_p_value" in c for c in res["pairwise_comparisons"])
