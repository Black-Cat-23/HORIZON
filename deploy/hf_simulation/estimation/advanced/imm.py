"""
Interacting Multiple Model (IMM-EKF) State Estimator.
HORIZON — SIH 2026 PS SIH26169 (PDF Section 6.5)

Blends 3 kinematic 6-state sub-models:
1. Constant Velocity (CV)      : Low process noise
2. Constant Acceleration (CA)  : Moderate process noise
3. Manoeuvre (HIGH-MANOEUVRE)  : High process noise

State vector: x = [theta_x, theta_y, omega_x, omega_y, ax, ay]^T (6-dimensional)
Measurement : z = [theta_x, theta_y]^T (2-dimensional)
"""

from __future__ import annotations
from typing import List, Tuple, Dict, Any
import numpy as np

from .models import SubModel


class IMMEKFEstimator:
    """
    Interacting Multiple Model (IMM) filter operating on 6-state angular dynamics.
    Performs mixing, individual model prediction/update, likelihood calculation,
    probability updating, and state fusion.
    """

    def __init__(self) -> None:
        # 3 sub-models with process noise levels tailored to maneuver intensity
        self.models: List[SubModel] = [
            SubModel("CV", process_noise_sigma=5.0),
            SubModel("CA", process_noise_sigma=25.0),
            SubModel("MANOEUVRE", process_noise_sigma=150.0),
        ]
        self.num_models = len(self.models)

        # Initial model probabilities (equal weight)
        self.mu = np.array([0.4, 0.4, 0.2], dtype=float)

        # Markov transition probability matrix (Pi_ij = P(M_j | M_i))
        self.Pi = np.array([
            [0.90, 0.08, 0.02],
            [0.05, 0.90, 0.05],
            [0.02, 0.08, 0.90],
        ], dtype=float)

        # 6-state fused vector and 6x6 fused covariance
        self.fused_x: np.ndarray = np.zeros(6, dtype=float)
        self.fused_P: np.ndarray = np.eye(6, dtype=float) * 100.0

    def predict_and_update(
        self,
        dt: float,
        z: np.ndarray,
        R: np.ndarray,
        detection_valid: bool,
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Executes complete IMM cycle: mixing -> prediction -> update -> mode probability update -> fusion.
        
        Args:
            dt: Time step in seconds.
            z: 2D angular error measurement vector [theta_x, theta_y].
            R: 2x2 measurement noise covariance.
            detection_valid: True if valid observation candidate is available.

        Returns:
            Tuple[fused_x (6,), fused_P (6,6), model_probabilities (3,)]
        """
        if dt <= 0.0:
            return self.fused_x, self.fused_P, self.mu

        # 1. Calculate Mixing Probabilities (mu_i|j)
        c_j = self.Pi.T @ self.mu  # Normalization constants
        c_j = np.where(c_j <= 0, 1e-12, c_j)

        mu_mix = np.zeros((self.num_models, self.num_models), dtype=float)
        for i in range(self.num_models):
            for j in range(self.num_models):
                mu_mix[i, j] = (self.Pi[i, j] * self.mu[i]) / c_j[j]

        # 2. Mix States (6D) and Covariances (6x6) for each model j
        mixed_x = []
        mixed_P = []
        for j in range(self.num_models):
            x_0j = np.zeros(6, dtype=float)
            for i in range(self.num_models):
                x_0j += mu_mix[i, j] * self.models[i].x
            mixed_x.append(x_0j)

            P_0j = np.zeros((6, 6), dtype=float)
            for i in range(self.num_models):
                dx = self.models[i].x - x_0j
                P_0j += mu_mix[i, j] * (self.models[i].P + np.outer(dx, dx))
            mixed_P.append(P_0j)

        # Set mixed states into sub-models
        for j in range(self.num_models):
            self.models[j].x = mixed_x[j]
            self.models[j].P = mixed_P[j]

        # 3. Model Predictions & Measurement Updates
        likelihoods = np.zeros(self.num_models, dtype=float)
        for j in range(self.num_models):
            self.models[j].predict(dt)
            if detection_valid:
                likelihoods[j] = self.models[j].update(z, R)
            else:
                likelihoods[j] = 1.0  # Equal likelihood during prediction/coast

        # 4. Mode Probability Update
        if detection_valid:
            mu_unnorm = likelihoods * c_j
            sum_mu = float(np.sum(mu_unnorm))
            if sum_mu > 0:
                self.mu = mu_unnorm / sum_mu

        # 5. State & Covariance Fusion (6D)
        self.fused_x = np.zeros(6, dtype=float)
        for j in range(self.num_models):
            self.fused_x += self.mu[j] * self.models[j].x

        self.fused_P = np.zeros((6, 6), dtype=float)
        for j in range(self.num_models):
            dx = self.models[j].x - self.fused_x
            self.fused_P += self.mu[j] * (self.models[j].P + np.outer(dx, dx))

        return self.fused_x, self.fused_P, self.mu
