"""
Unit tests for RobustnessMapGenerator.
"""

from analysis.robustness_map import RobustnessMapGenerator


def test_robustness_map_generator():
    gen = RobustnessMapGenerator()

    cells = [
        {"param_x_val": 1.0, "param_y_val": 10.0, "success_rate": 1.0, "median_error": 5.0},
        {"param_x_val": 2.0, "param_y_val": 10.0, "success_rate": 0.2, "median_error": 50.0},
    ]

    res = gen.generate_map_data(
        param_x_name="noise",
        param_x_vals=[1.0, 2.0],
        param_y_name="jitter",
        param_y_vals=[10.0],
        cell_data=cells,
    )

    assert res["classification_matrix"][0][0] == "SUCCESS"
    assert res["classification_matrix"][0][1] == "FAILURE"
