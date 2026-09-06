"""
Test Result Validation
"""
from analysis.validation.result_validator import ResultValidator, TrialValidityState

def test_result_validation_valid():
    validator = ResultValidator()
    data = {
        "experiment_id": "EXP_1",
        "trial_id": "T1",
        "algorithm": "OURS",
        "seed": 42,
        "scenario_id": "NOMINAL",
        "resolved_configuration": {},
        "status": "SUCCESS",
        "metrics": {"mean_tracking_error_px": 10.0},
        "software_version": "1.0.0",
    }
    state, reason = validator.validate_trial(data)
    assert state == TrialValidityState.VALID
    assert reason is None
