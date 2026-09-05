"""
Unit tests for DistributionAggregator.
"""

from analysis.aggregation import DistributionAggregator


def test_distribution_aggregator():
    trials = [
        {"success": True, "metrics": {"mean_tracking_error": 5.0, "RMSE_tracking_error": 6.0, "lock_retention_rate": 0.9, "processing_time": 10.0}},
        {"success": True, "metrics": {"mean_tracking_error": 10.0, "RMSE_tracking_error": 12.0, "lock_retention_rate": 0.8, "processing_time": 12.0}},
    ]

    res = DistributionAggregator.aggregate(trials)

    assert res["total_trials"] == 2
    assert res["success_count"] == 2
    assert res["success_rate"] == 1.0
    assert abs(res["tracking_error"]["mean"] - 7.5) < 1e-4
