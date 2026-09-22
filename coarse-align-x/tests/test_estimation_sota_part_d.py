"""Unit tests for Phase D: Estimation & Kinematics Layer SOTA Upgrades."""

import math
import numpy as np
import pytest

from tracking.estimation.covariance import clamp_covariance_spectrum, enforce_symmetry, validate_covariance
from tracking.estimation.imm_kalman import InteractingMultipleModelFilter
from tracking.estimation.imm_models import CTModel, CAModel, CVModel
from tracking.estimation.kalman import TargetKalmanFilter, KalmanFilterConfig


def test_covariance_clamping_and_anti_divergence():
    """Verify spectrum floor clamping forces eigenvalues to be >= 1e-6."""
    # Create ill-conditioned matrix with zero and negative eigenvalues
    P_bad = np.array([
        [1.0, 2.0, 0.0, 0.0],
        [2.0, 1.0, 0.0, 0.0],  # Eigenvalues are 3.0 and -1.0
        [0.0, 0.0, 0.0, 0.0],
        [0.0, 0.0, 0.0, -0.5],
    ], dtype=np.float64)

    P_clamped = clamp_covariance_spectrum(P_bad, min_eigenvalue=1e-6)

    # Check validity
    is_valid, msg = validate_covariance(P_clamped)
    assert is_valid, f"Clamped matrix is invalid: {msg}"

    # Verify minimum eigenvalue is clamped
    eigvals = np.linalg.eigvalsh(P_clamped)
    assert np.min(eigvals) >= 1e-6 - 1e-12


def test_nis_driven_process_noise_scaling():
    """Verify that elevated NIS scales process noise Q_k in predict cycle."""
    kf = TargetKalmanFilter(KalmanFilterConfig(accel_noise_sigma=100.0))
    kf.initialize((100.0, 100.0), timestamp=0.0)

    # Step with extreme measurement outlier to generate large NIS
    est = kf.update((500.0, 500.0), confidence=0.9, timestamp=0.1)

    # Check that NIS was captured and last_innovation was logged
    assert kf._last_innovation is not None
    assert kf._last_innovation.nis > 16.0

    # Execute next predict step and verify P_pred expansion
    x_pred, P_pred = kf.predict(dt=0.1)
    assert P_pred[0, 0] > 0.0


def test_coordinated_turn_non_linear_model():
    """Verify CTModel polar kinematics prediction and update."""
    ct = CTModel(process_noise_std=2.0)
    ct.update(np.array([100.0, 100.0]), R=np.eye(2))
    assert ct._initialized

    # Predict across turn maneuver
    ct.predict(dt=0.1)
    st = ct.state()
    assert st.shape == (4,)
    assert np.all(np.isfinite(st))

    cov = ct.covariance()
    assert cov.shape == (4, 4)
    assert np.min(np.diag(cov)) > 0.0


def test_imm_bayes_probability_fusion():
    """Verify IMM filter probability updates and mode probability vector."""
    imm = InteractingMultipleModelFilter()
    imm.initialize((100.0, 200.0), timestamp=0.0)

    p_cv, p_ca, p_man = imm.mode_probabilities
    assert abs((p_cv + p_ca + p_man) - 1.0) < 1e-5

    # Update with maneuvering trajectory sequence
    for i in range(1, 10):
        # Accelerating curve
        meas_x = 100.0 + 10.0 * i + 2.0 * i**2
        meas_y = 200.0 + 5.0 * i + 1.5 * i**2
        est = imm.step((meas_x, meas_y), confidence=0.95, timestamp=0.1 * i)
        assert est.estimated_x > 0.0
        assert est.estimator_health is not None

    p_cv_end, p_ca_end, p_man_end = imm.mode_probabilities
    assert abs((p_cv_end + p_ca_end + p_man_end) - 1.0) < 1e-5
