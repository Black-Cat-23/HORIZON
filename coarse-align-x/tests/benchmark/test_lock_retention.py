"""
Unit tests for lock retention rate formula.
"""

from benchmark.metrics import MetricEngine


def test_lock_retention_rate_full_and_half():
    engine = MetricEngine()

    # 100% lock (10 frames TRACK)
    telemetry_100 = [{"timestamp": i * 0.1, "state": "TRACK", "true_x": 100.0, "true_y": 100.0, "est_x": 100.0, "est_y": 100.0} for i in range(10)]
    metrics_100 = engine.evaluate_telemetry(telemetry_100)
    assert abs(metrics_100["lock_retention_rate"] - 1.0) < 1e-5

    # 50% lock (5 TRACK, 5 LOST)
    telemetry_50 = [{"timestamp": i * 0.1, "state": "TRACK" if i < 5 else "LOST", "true_x": 100.0, "true_y": 100.0, "est_x": 100.0, "est_y": 100.0} for i in range(10)]
    metrics_50 = engine.evaluate_telemetry(telemetry_50)
    assert abs(metrics_50["lock_retention_rate"] - 0.5) < 1e-5
