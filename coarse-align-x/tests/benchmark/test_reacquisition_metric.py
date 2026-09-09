"""
Unit tests for reacquisition metric calculations.
"""

from benchmark.metrics import MetricEngine


def test_reacquisition_time_calculation():
    engine = MetricEngine()

    # Track -> Lost -> Reacquired
    telemetry = [
        {"timestamp": 0.0, "state": "TRACK", "true_x": 100.0, "true_y": 100.0, "est_x": 100.0, "est_y": 100.0},
        {"timestamp": 0.1, "state": "LOST", "true_x": 100.0, "true_y": 100.0, "est_x": 100.0, "est_y": 100.0},
        {"timestamp": 0.2, "state": "LOST", "true_x": 100.0, "true_y": 100.0, "est_x": 100.0, "est_y": 100.0},
        {"timestamp": 0.3, "state": "TRACK", "true_x": 100.0, "true_y": 100.0, "est_x": 100.0, "est_y": 100.0},
    ]

    metrics = engine.evaluate_telemetry(telemetry)
    assert metrics["target_loss_count"] == 1
    assert metrics["successful_reacquisition_count"] == 1
    assert metrics["failed_reacquisition_count"] == 0
    assert abs(metrics["reacquisition_time"] - 0.2) < 1e-5
