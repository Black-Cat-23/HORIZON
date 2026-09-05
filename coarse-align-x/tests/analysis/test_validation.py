"""
Unit tests for trial schema validation and directory audit.
"""

from analysis.validation import validate_trial_result, audit_trials_directory


def test_validate_trial_result_valid():
    trial_data = {
        "experiment_id": "EXP_01",
        "trial_id": "TRIAL_01",
        "algorithm": "OURS",
        "seed": 42,
        "scenario_id": "nominal",
        "status": "SUCCESS",
        "metrics": {
            "simulation_duration": 10.0,
            "average_fps": 60.0,
            "processing_time": 15.0,
            "P95_processing_time": 20.0,
            "mean_tracking_error": 2.5,
            "median_tracking_error": 2.1,
            "RMSE_tracking_error": 3.0,
            "P95_tracking_error": 4.5,
            "P99_tracking_error": 5.0,
            "lock_retention_rate": 0.98,
        },
        "resolved_configuration": {},
    }

    is_valid, issues = validate_trial_result(trial_data)
    assert is_valid
    assert len(issues) == 0


def test_validate_trial_result_invalid():
    trial_data = {
        "experiment_id": "EXP_01",
        "algorithm": "OURS",
    }

    is_valid, issues = validate_trial_result(trial_data)
    assert not is_valid
    assert len(issues) > 0
