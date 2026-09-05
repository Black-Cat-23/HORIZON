"""
Unit tests for Interacting Multiple Model (IMM-EKF) estimator.
HORIZON Phase 6
"""

import pytest
import numpy as np
from estimation.advanced.imm import IMMEKFEstimator
from estimation.advanced.imm_diagnostics import IMMDiagnostics


def test_imm_predict_and_update():
    imm = IMMEKFEstimator()
    z = np.array([100.0, 200.0])
    R = np.eye(2) * 5.0

    fused_x, fused_P, mu = imm.predict_and_update(dt=0.016, z=z, R=R, detection_valid=True)
    assert fused_x.shape == (4,)
    assert fused_P.shape == (4, 4)
    assert len(mu) == 3
    assert np.isclose(np.sum(mu), 1.0)


def test_imm_diagnostics():
    diag = IMMDiagnostics()
    probs = np.array([0.7, 0.2, 0.1])
    res = diag.format_telemetry(probs)
    assert res["imm_dominant_model"] == "CV"
    assert res["imm_prob_cv"] == pytest.approx(0.7)
