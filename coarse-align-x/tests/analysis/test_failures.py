"""
Unit tests for FailureAnalyzer.
"""

from analysis.failures import FailureAnalyzer


def test_failure_analyzer():
    trials = [
        {"status": "SUCCESS"},
        {"status": "SUCCESS"},
        {"status": "EXCESSIVE_ERROR"},
    ]

    res = FailureAnalyzer.analyze_trial_group(trials)

    assert res["total_trials"] == 3
    assert res["failure_counts"]["SUCCESS"] == 2
    assert res["failure_counts"]["EXCESSIVE_ERROR"] == 1
    assert abs(res["failure_percentages"]["SUCCESS"] - 66.66666666666666) < 1e-4
