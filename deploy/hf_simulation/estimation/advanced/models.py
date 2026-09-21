"""
Kinematic Sub-models for IMM-EKF Estimation.
HORIZON — SIH 2026 PS SIH26169 (PDF Section 6.5)

Defines 6-State Angular Vector:
x = [theta_x, theta_y, omega_x, omega_y, ax, ay]^T
where:
  theta_x, theta_y : horizontal / vertical angular error (deg or rad)
  omega_x, omega_y : angular velocity (deg/s or rad/s)
  ax, ay           : angular acceleration (deg/s^2 or rad/s^2)
"""

from __future__ import annotations
from typing import Tuple
import numpy as np


class SubModel:
    """
    Kinematic 6-state sub-model for IMM filtering.
    """

    def __init__(self, name: str, process_noise_sigma: float) -> None:
        self.name = name
        self.process_noise_sigma = float(process_noise_sigma)

        # 6-State Vector: [theta_x, theta_y, omega_x, omega_y, ax, ay]
        self.x: np.ndarray = np.zeros(6, dtype=float)
        self.P: np.ndarray = np.eye(6, dtype=float) * 100.0

    def predict(self, dt: float) -> Tuple[np.ndarray, np.ndarray]:
        """
        Executes kinematic state propagation and process noise covariance addition.
        
        State transition equation:
          theta(k+1) = theta(k) + omega(k)*dt + 0.5*a(k)*dt^2
          omega(k+1) = omega(k) + a(k)*dt
          a(k+1)     = a(k)
        """
        dt2 = 0.5 * (dt ** 2)

        F = np.array([
            [1.0, 0.0,  dt, 0.0, dt2, 0.0],
            [0.0, 1.0, 0.0,  dt, 0.0, dt2],
            [0.0, 0.0, 1.0, 0.0,  dt, 0.0],
            [0.0, 0.0, 0.0, 1.0, 0.0,  dt],
            [0.0, 0.0, 0.0, 0.0, 1.0, 0.0],
            [0.0, 0.0, 0.0, 0.0, 0.0, 1.0],
        ], dtype=float)

        q_std = self.process_noise_sigma
        
        # Piecewise continuous white noise model for 3D state per axis (pos, vel, accel)
        q5 = (dt ** 5) / 20.0 * (q_std ** 2)
        q4 = (dt ** 4) / 8.0 * (q_std ** 2)
        q3 = (dt ** 3) / 6.0 * (q_std ** 2)
        q3_v = (dt ** 3) / 3.0 * (q_std ** 2)
        q2 = (dt ** 2) / 2.0 * (q_std ** 2)
        q1 = dt * (q_std ** 2)

        Q = np.array([
            [q5, 0.0, q4, 0.0, q3, 0.0],
            [0.0, q5, 0.0, q4, 0.0, q3],
            [q4, 0.0, q3_v, 0.0, q2, 0.0],
            [0.0, q4, 0.0, q3_v, 0.0, q2],
            [q3, 0.0, q2, 0.0, q1, 0.0],
            [0.0, q3, 0.0, q2, 0.0, q1],
        ], dtype=float)

        self.x = F @ self.x
        self.P = F @ self.P @ F.T + Q
        return self.x, self.P

    def update(self, z: np.ndarray, R: np.ndarray) -> float:
        """
        Executes Kalman measurement update for 2D angular measurement z = [theta_x, theta_y]
        and returns Gaussian likelihood.
        """
        H = np.array([
            [1.0, 0.0, 0.0, 0.0, 0.0, 0.0],
            [0.0, 1.0, 0.0, 0.0, 0.0, 0.0],
        ], dtype=float)

        y = z - (H @ self.x)
        S = H @ self.P @ H.T + R
        K = self.P @ H.T @ np.linalg.inv(S)

        # Joseph-form covariance update for numerical stability
        I_KH = np.eye(6, dtype=float) - K @ H
        self.x = self.x + K @ y
        self.P = I_KH @ self.P @ I_KH.T + K @ R @ K.T

        # Calculate measurement likelihood
        det_S = float(np.linalg.det(S))
        if det_S <= 0:
            det_S = 1e-6
        inv_S = np.linalg.inv(S)
        mahalanobis_d2 = float(y.T @ inv_S @ y)
        likelihood = (1.0 / (2.0 * np.pi * np.sqrt(det_S))) * np.exp(-0.5 * mahalanobis_d2)
        return float(max(likelihood, 1e-12))
