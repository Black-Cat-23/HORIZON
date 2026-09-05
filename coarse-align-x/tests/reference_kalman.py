"""
HORIZON Independent Numerical Reference Kalman Filter
============================================================
A baseline, standard textbook Kalman filter implementation using direct
matrix inversion (np.linalg.inv) and standard non-Joseph covariance update:
    P = (I - KH) * P_pred

Used exclusively for independent numerical cross-checks in automated tests.
Strict Invariant: Production code does not depend on this reference.
"""

from __future__ import annotations

from typing import Tuple
import numpy as np


class IndependentReferenceKalman:
    """Standard textbook discrete-time Kalman filter for 2D constant velocity."""

    def __init__(
        self,
        q_accel_var: float = 2500.0,
        r_meas_var: float = 0.25,
        p_pos_var: float = 25.0,
        p_vel_var: float = 14400.0,
    ) -> None:
        self.q_accel_var = float(q_accel_var)
        self.r_meas_var = float(r_meas_var)
        self.H = np.array([[1.0, 0.0, 0.0, 0.0], [0.0, 1.0, 0.0, 0.0]], dtype=np.float64)

        self.x = np.zeros((4, 1), dtype=np.float64)
        self.P = np.diag([p_pos_var, p_pos_var, p_vel_var, p_vel_var]).astype(np.float64)
        self.x_pred = self.x.copy()
        self.P_pred = self.P.copy()

    def initialize(self, z: Tuple[float, float]) -> None:
        self.x = np.array([[z[0]], [z[1]], [0.0], [0.0]], dtype=np.float64)
        self.x_pred = self.x.copy()

    def predict(self, dt: float) -> Tuple[np.ndarray, np.ndarray]:
        # F matrix
        F = np.array(
            [
                [1.0, 0.0, dt, 0.0],
                [0.0, 1.0, 0.0, dt],
                [0.0, 0.0, 1.0, 0.0],
                [0.0, 0.0, 0.0, 1.0],
            ],
            dtype=np.float64,
        )

        # CWNA Q matrix
        dt2 = dt * dt
        dt3 = dt2 * dt
        q = self.q_accel_var
        Q = np.array(
            [
                [(dt3 / 3.0) * q, 0.0, (dt2 / 2.0) * q, 0.0],
                [0.0, (dt3 / 3.0) * q, 0.0, (dt2 / 2.0) * q],
                [(dt2 / 2.0) * q, 0.0, dt * q, 0.0],
                [0.0, (dt2 / 2.0) * q, 0.0, dt * q],
            ],
            dtype=np.float64,
        )

        self.x_pred = F @ self.x
        self.P_pred = (F @ self.P @ F.T) + Q
        return self.x_pred, self.P_pred

    def update(self, z: Tuple[float, float]) -> Tuple[np.ndarray, np.ndarray]:
        z_col = np.array([[z[0]], [z[1]]], dtype=np.float64)
        R = np.diag([self.r_meas_var, self.r_meas_var]).astype(np.float64)

        # Residual
        y = z_col - (self.H @ self.x_pred)

        # S = H P_pred H^T + R
        S = (self.H @ self.P_pred @ self.H.T) + R

        # Direct explicit textbook inversion
        S_inv = np.linalg.inv(S)
        K = self.P_pred @ self.H.T @ S_inv

        # State update
        self.x = self.x_pred + (K @ y)

        # Standard textbook covariance update: P = (I - KH) P_pred
        I = np.eye(4, dtype=np.float64)
        self.P = (I - (K @ self.H)) @ self.P_pred

        return self.x, self.P
