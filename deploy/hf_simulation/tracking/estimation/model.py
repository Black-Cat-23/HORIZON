"""
HORIZON Kinematic & Measurement Models
=============================================
Mathematical formulations for constant-velocity state transition,
process noise covariance (Continuous White Noise Acceleration),
observation projection, and adaptive measurement noise.

Coordinate System:
    Image-plane 2D coordinates (pixels and pixels/second).

Strict Invariant: Zero access to true target position or ground-truth state.
"""

from __future__ import annotations

import math
from typing import Literal
import numpy as np


def build_transition_matrix(dt: float) -> np.ndarray:
    """Construct the Constant-Velocity (CV) state transition matrix F(dt).

    State equation:
        x_k = F(dt) * x_{k-1} + w_{k-1}
        where x = [p_x, p_y, v_x, v_y]^T

    Matrix form:
        F = [
            [1, 0, dt,  0],
            [0, 1,  0, dt],
            [0, 0,  1,  0],
            [0, 0,  0,  1]
        ]

    Args:
        dt: Time delta between timestamps [seconds], must be > 0.

    Returns:
        4×4 float64 transition matrix.
    """
    if dt < 0.0:
        raise ValueError(f"Time delta dt must be non-negative, got {dt}")

    F = np.eye(4, dtype=np.float64)
    F[0, 2] = dt
    F[1, 3] = dt
    return F


def build_process_noise_matrix(
    dt: float,
    accel_noise_sigma: float = 50.0,
    model_type: Literal["cwna", "piecewise_constant"] = "cwna",
) -> np.ndarray:
    """Construct the process noise covariance matrix Q(dt).

    PROJECT ENGINEERING PARAMETER:
        accel_noise_sigma: Standard deviation of unmodeled target acceleration [px/s^2].
        Default: 50.0 px/s^2 (corresponds to typical maneuvering target accelerations
        relative to the 640×480 optical focal plane).

    Derivation (Continuous White Noise Acceleration / Singer model limit):
        Assumes target acceleration is zero-mean continuous white noise w(t) with
        spectral density q = sigma_a^2.
        Integrating continuous noise over interval dt yields:
            Q_1D = sigma_a^2 * [
                [dt^3 / 3, dt^2 / 2],
                [dt^2 / 2, dt]
            ]
        Combining independent horizontal (x) and vertical (y) channels:
            Q = [
                [dt^3/3,      0, dt^2/2,      0],
                [     0, dt^3/3,      0, dt^2/2],
                [dt^2/2,      0,     dt,      0],
                [     0, dt^2/2,      0,     dt]
            ] * sigma_a^2

    Alternative (Piecewise Constant White Acceleration):
        Assumes acceleration is constant over time dt with variance sigma_a^2:
            Gamma = [[dt^2/2, 0], [0, dt^2/2], [dt, 0], [0, dt]]
            Q = Gamma * (sigma_a^2 * I_2) * Gamma^T

    Args:
        dt: Time step [seconds].
        accel_noise_sigma: Acceleration disturbance standard deviation [px/s^2].
        model_type: 'cwna' (default) or 'piecewise_constant'.

    Returns:
        4×4 float64 symmetric positive semi-definite matrix Q.
    """
    if dt < 0.0:
        raise ValueError(f"Time delta dt must be non-negative, got {dt}")
    if accel_noise_sigma < 0.0:
        raise ValueError(f"Acceleration noise sigma must be non-negative, got {accel_noise_sigma}")

    q_var = float(accel_noise_sigma**2)

    if model_type == "piecewise_constant":
        dt2 = dt * dt
        dt3 = dt2 * dt
        dt4 = dt3 * dt
        q11 = 0.25 * dt4 * q_var
        q12 = 0.5 * dt3 * q_var
        q22 = dt2 * q_var
    else:  # Continuous White Noise Acceleration (CWNA)
        dt2 = dt * dt
        dt3 = dt2 * dt
        q11 = (dt3 / 3.0) * q_var
        q12 = (dt2 / 2.0) * q_var
        q22 = dt * q_var

    Q = np.zeros((4, 4), dtype=np.float64)
    Q[0, 0] = q11
    Q[0, 2] = q12
    Q[1, 1] = q11
    Q[1, 3] = q12
    Q[2, 0] = q12
    Q[2, 2] = q22
    Q[3, 1] = q12
    Q[3, 3] = q22

    return Q


def build_measurement_matrix() -> np.ndarray:
    """Construct the observation matrix H.

    Observation equation:
        z = H * x + v
        where z = [measured_x, measured_y]^T
              x = [p_x, p_y, v_x, v_y]^T

    Matrix form:
        H = [
            [1, 0, 0, 0],
            [0, 1, 0, 0]
        ]

    Returns:
        2×4 float64 observation matrix.
    """
    H = np.zeros((2, 4), dtype=np.float64)
    H[0, 0] = 1.0
    H[1, 1] = 1.0
    return H


def build_measurement_noise_matrix(
    confidence: float = 1.0,
    base_sigma_px: float = 0.5,
    min_sigma_px: float = 0.05,
    max_sigma_px: float = 5.0,
) -> np.ndarray:
    """Construct the adaptive measurement noise covariance matrix R(confidence).

    PROJECT ENGINEERING PARAMETER:
        base_sigma_px: Nominal perception centroid measurement uncertainty [px]
                       at unit confidence (1.0). Default: 0.5 px.
        min_sigma_px: Lower bound on measurement standard deviation [px].
        max_sigma_px: Upper bound on measurement standard deviation [px].

    Mapping Derivation:
        The perception stage provides a confidence score c in [0.0, 1.0].
        Lower confidence indicates higher spatial variance (e.g. faint beacon,
        atmospheric turbulence, or optical flare).
        sigma_r = base_sigma_px / max(confidence, 0.1)
        sigma_r = clip(sigma_r, min_sigma_px, max_sigma_px)
        R = diag(sigma_r^2, sigma_r^2)

    Args:
        confidence: Perception detection confidence in [0.0, 1.0].
        base_sigma_px: Nominal standard deviation at confidence 1.0 [px].
        min_sigma_px: Minimum allowable standard deviation [px].
        max_sigma_px: Maximum allowable standard deviation [px].

    Returns:
        2×2 float64 diagonal covariance matrix R.
    """
    conf = float(np.clip(confidence, 0.05, 1.0))
    sigma_r = base_sigma_px / conf
    sigma_r = float(np.clip(sigma_r, min_sigma_px, max_sigma_px))
    var_r = sigma_r * sigma_r

    R = np.zeros((2, 2), dtype=np.float64)
    R[0, 0] = var_r
    R[1, 1] = var_r
    return R
