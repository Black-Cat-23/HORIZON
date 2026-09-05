"""
Unit tests for Interacting Multiple Model (IMM-EKF) 6-State estimator.
HORIZON — SIH 2026 PS SIH26169 (PDF Section 6.5)
"""

import pytest
import numpy as np
from estimation.advanced.imm import IMMEKFEstimator
from estimation.advanced.imm_diagnostics import IMMDiagnostics


def test_imm_predict_and_update_6state():
    imm = IMMEKFEstimator()
    z = np.array([2.5, -1.2])  # 2D angular error measurement in degrees
    R = np.eye(2) * 0.05

    fused_x, fused_P, mu = imm.predict_and_update(dt=0.016, z=z, R=R, detection_valid=True)
    
    # 6-state vector: [theta_x, theta_y, omega_x, omega_y, ax, ay]
    assert fused_x.shape == (6,)
    assert fused_P.shape == (6, 6)
    assert len(mu) == 3
    assert np.isclose(np.sum(mu), 1.0)


def test_imm_kinematic_acceleration_propagation():
    imm = IMMEKFEstimator()
    z1 = np.array([0.0, 0.0])
    R = np.eye(2) * 0.01

    # Step 1: Initial position at 0
    imm.predict_and_update(dt=0.1, z=z1, R=R, detection_valid=True)

    # Step 2: Accelerating target (quadratic displacement: theta = 0.5 * a * t^2)
    for k in range(1, 10):
        t = k * 0.1
        pos = 0.5 * 2.0 * (t ** 2)  # constant accel = 2.0 deg/s^2
        z_k = np.array([pos, pos])
        fused_x, _, _ = imm.predict_and_update(dt=0.1, z=z_k, R=R, detection_valid=True)

    # State vector should estimate non-zero angular velocity (x[2], x[3]) and acceleration (x[4], x[5])
    assert fused_x[2] > 0.0  # omega_x
    assert fused_x[3] > 0.0  # omega_y
    assert fused_x[4] > 0.0  # a_x
    assert fused_x[5] > 0.0  # a_y


def test_imm_diagnostics():
    diag = IMMDiagnostics()
    probs = np.array([0.7, 0.2, 0.1])
    res = diag.format_telemetry(probs)
    assert res["imm_dominant_model"] == "CV"
    assert res["imm_prob_cv"] == pytest.approx(0.7)
