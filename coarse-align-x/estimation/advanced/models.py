"""
Kinematic Sub-models for IMM-EKF Estimation.
HORIZON Phase 6
"""

from typing import Tuple
import numpy as np


class SubModel:
    """
    Base kinematic sub-model for IMM filtering.
    """
    def __init__(self, name: str, process_noise_sigma: float):
        self.name = name
        self.process_noise_sigma = process_noise_sigma
        self.x = np.zeros(4, dtype=float)  # [px, py, vx, vy]
        self.P = np.eye(4, dtype=float) * 100.0

    def predict(self, dt: float) -> Tuple[np.ndarray, np.ndarray]:
        F = np.array([
            [1.0, 0.0,  dt, 0.0],
            [0.0, 1.0, 0.0,  dt],
            [0.0, 0.0, 1.0, 0.0],
            [0.0, 0.0, 0.0, 1.0],
        ], dtype=float)

        q_std = self.process_noise_sigma
        q_pos = 0.25 * (dt**4) * (q_std**2)
        q_pos_vel = 0.5 * (dt**3) * (q_std**2)
        q_vel = (dt**2) * (q_std**2)

        Q = np.array([
            [q_pos,     0.0, q_pos_vel,     0.0],
            [    0.0, q_pos,     0.0, q_pos_vel],
            [q_pos_vel, 0.0,   q_vel,       0.0],
            [    0.0, q_pos_vel, 0.0,     q_vel],
        ], dtype=float)

        self.x = F @ self.x
        self.P = F @ self.P @ F.T + Q
        return self.x, self.P

    def update(self, z: np.ndarray, R: np.ndarray) -> float:
        """
        Executes Kalman measurement update and computes Gaussian likelihood.
        """
        H = np.array([
            [1.0, 0.0, 0.0, 0.0],
            [0.0, 1.0, 0.0, 0.0],
        ], dtype=float)

        y = z - (H @ self.x)
        S = H @ self.P @ H.T + R
        K = self.P @ H.T @ np.linalg.inv(S)

        # Joseph-form update
        I_KH = np.eye(4) - K @ H
        self.x = self.x + K @ y
        self.P = I_KH @ self.P @ I_KH.T + K @ R @ K.T

        # Calculate measurement likelihood L
        det_S = np.linalg.det(S)
        if det_S <= 0:
            det_S = 1e-6
        inv_S = np.linalg.inv(S)
        mahalanobis_d2 = float(y.T @ inv_S @ y)
        likelihood = (1.0 / (2.0 * np.pi * np.sqrt(det_S))) * np.exp(-0.5 * mahalanobis_d2)
        return float(max(likelihood, 1e-12))
