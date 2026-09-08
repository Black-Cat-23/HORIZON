"""
Unit tests for MetricEngine with synthetic telemetry with known ground-truth answers.
"""

from benchmark.metrics import MetricEngine


def test_metric_engine_synthetic_telemetry():
    engine = MetricEngine(fov_deg=4.0, sensor_width_px=640)

    # Synthetic 10 frames telemetry with zero tracking error
    telemetry = []
    for i in range(10):
        telemetry.append({
            "timestamp": i * 0.1,
            "frame_idx": i,
            "state": "TRACK",
            "true_x": 320.0,
            "true_y": 240.0,
            "est_x": 320.0,
            "est_y": 240.0,
            "det_x": 320.0,
            "det_y": 240.0,
            "detected": True,
            "processing_time_ms": 10.0,
            "is_saturated": False,
        })

    metrics = engine.evaluate_telemetry(telemetry)
    assert metrics["mean_tracking_error"] == 0.0
    assert metrics["RMSE_tracking_error"] == 0.0
    assert metrics["lock_retention_rate"] == 1.0
    assert metrics["detection_success_rate"] == 1.0
    assert metrics["target_loss_count"] == 0


def test_metric_engine_known_error():
    engine = MetricEngine(fov_deg=4.0, sensor_width_px=640)

    # 4 frames with known errors: 3, 4, 0, 0 -> hypot(3,4)=5.0 error
    telemetry = [
        {"timestamp": 0.0, "state": "TRACK", "true_x": 300.0, "true_y": 200.0, "est_x": 303.0, "est_y": 204.0, "detected": True, "processing_time_ms": 5.0},
        {"timestamp": 0.1, "state": "TRACK", "true_x": 300.0, "true_y": 200.0, "est_x": 303.0, "est_y": 204.0, "detected": True, "processing_time_ms": 5.0},
    ]

    metrics = engine.evaluate_telemetry(telemetry)
    assert abs(metrics["mean_tracking_error"] - 5.0) < 1e-5
    assert abs(metrics["RMSE_tracking_error"] - 5.0) < 1e-5
