"""
Unit tests for 2D parameter grid sweeps and robustness envelopes.
"""

from benchmark.robustness import RobustnessEnvelopeEngine


def test_robustness_grid_sweep():
    engine = RobustnessEnvelopeEngine(success_rate_threshold=0.8, max_degraded_error_px=20.0)

    # Synthetic evaluator
    def mock_evaluator(x, y):
        # High noise (x > 30) leads to failure
        if x > 30.0:
            return (10, 2, 40.0, 60.0)  # 20% success rate, 40px error
        else:
            return (10, 10, 5.0, 10.0)  # 100% success rate, 5px error

    res = engine.evaluate_grid(
        param_x_name="noise_sigma",
        param_x_values=[10.0, 20.0, 40.0],
        param_y_name="jitter",
        param_y_values=[1.0, 2.0],
        cell_evaluator=mock_evaluator,
    )

    assert len(res["grid_results"]) == 6
    matrix_class = res["classification_matrix"]
    assert matrix_class[0][0] == "SUCCESS"
    assert matrix_class[0][2] == "FAILURE"
