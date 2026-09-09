"""
Unit tests for acquisition metric calculations.
"""

from benchmark.metrics import MetricEngine


def test_acquisition_time_calculation():
    engine = MetricEngine()

    # Search for 0.3s (frames 0, 1, 2) before track on frame 3 (ts=0.3s)
    telemetry = [
        {"timestamp": 0.0, "state": "SEARCH", "true_x": 100.0, "true_y": 100.0, "est_x": 100.0, "est_y": 100.0},
        {"timestamp": 0.1, "state": "SEARCH", "true_x": 100.0, "true_y": 100.0, "est_x": 100.0, "est_y": 100.0},
        {"timestamp": 0.2, "state": "SEARCH", "true_x": 100.0, "true_y": 100.0, "est_x": 100.0, "est_y": 100.0},
        {"timestamp": 0.3, "state": "TRACK", "true_x": 100.0, "true_y": 100.0, "est_x": 100.0, "est_y": 100.0},
        {"timestamp": 0.4, "state": "TRACK", "true_x": 100.0, "true_y": 100.0, "est_x": 100.0, "est_y": 100.0},
    ]

    metrics = engine.evaluate_telemetry(telemetry)
    assert metrics["acquisition_start_timestamp"] == 0.0
    assert metrics["acquisition_confirmed_timestamp"] == 0.3
    assert abs(metrics["acquisition_time"] - 0.3) < 1e-5
