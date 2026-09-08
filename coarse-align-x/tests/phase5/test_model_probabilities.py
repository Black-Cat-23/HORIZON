"""
Phase 5 Model Probabilities, Prediction, Timestamp & Gating Unit Tests
"""

import numpy as np
import pytest
from tracking.estimation.imm_kalman import InteractingMultipleModelFilter
from tracking.estimation.kalman import TargetKalmanFilter, KalmanFilterConfig, compute_nees_evaluation
from tracking.estimation.state import EstimatorStatus


def test_model_switching_on_high_dynamics():
    imm = InteractingMultipleModelFilter()
    imm.initialize((100.0, 100.0), timestamp=0.0)

    # Low dynamics CV phase
    for i in range(1, 10):
        imm.step((100.0 + i * 2.0, 100.0 + i * 2.0), timestamp=i * 0.05)
    p_cv_start, p_ca_start, p_man_start = imm.mode_probabilities

    # High acceleration maneuver step
    for i in range(10, 20):
        imm.step((100.0 + i * 20.0 + 5.0 * (i**2), 100.0 + i * 15.0), timestamp=i * 0.05)
    p_cv_man, p_ca_man, p_man_man = imm.mode_probabilities

    assert p_man_man + p_ca_man > p_cv_man or p_man_man > p_man_start


def test_prediction_forward_projection():
    kf = TargetKalmanFilter()
    kf.initialize((200.0, 200.0), timestamp=0.0, initial_velocity=(20.0, 10.0))

    x_pred, P_pred = kf.predict(dt=0.1)
    assert pytest.approx(x_pred[0, 0], abs=1e-3) == 202.0
    assert pytest.approx(x_pred[1, 0], abs=1e-3) == 201.0


def test_timestamp_integrity_non_constant_dt():
    kf = TargetKalmanFilter()
    kf.initialize((100.0, 100.0), timestamp=0.0)

    timestamps = [0.03, 0.08, 0.15, 0.22, 0.35]
    for i, t in enumerate(timestamps):
        est = kf.update((100.0 + i * 2.0, 100.0 + i * 1.0), timestamp=t)
        assert est.timestamp == t


def test_nees_evaluation_metric():
    x_true = np.array([100.0, 200.0, 10.0, 5.0])
    x_est = np.array([101.0, 199.0, 9.5, 5.2])
    P_est = np.diag([2.0, 2.0, 1.0, 1.0])

    nees = compute_nees_evaluation(x_true, x_est, P_est)
    assert nees >= 0.0
    assert not np.isnan(nees)
