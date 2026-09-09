"""
Test Metric Aggregation & Percentiles
"""
from analysis.metrics.aggregator import DistributionAggregator

def test_metric_aggregation():
    data = [10.0, 20.0, 30.0, 40.0, 50.0]
    res = DistributionAggregator.aggregate_values(data)
    assert res["count"] == 5
    assert res["mean"] == 30.0
    assert res["median"] == 30.0
    assert res["p50"] == 30.0
