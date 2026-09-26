"""
HORIZON Linear Quadratic Gaussian (LQG) / LQR State Regulator
=============================================================
Discrete-time LQR optimal state feedback controller for dual-axis optical tracking.

Solves Discrete Algebraic Riccati Equation (DARE):
  P = A^T P A - (A^T P B) (R + B^T P B)^-1 (B^T P A) + Q
  K_LQR = (R + B^T P B)^-1 B^T P A
  u_k = -K_LQR * x_k

Strict Invariant: Zero access to true target position or ground-truth state.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple
import numpy as np


@dataclass
class LQGConfig:
    """Configuration weights for LQG/LQR state regulator."""
    q_pos_weight: float = 100.0  # State position error penalty weight
    q_vel_weight: float = 1.0    # State velocity error penalty weight
    r_control_cost: float = 0.05 # Control effort penalty cost
    max_output_deg_s: float = 60.0


class LQGController:
    """Discrete Linear Quadratic Regulator (LQR) for 2D pan and tilt optical tracking."""

    def __init__(self, config: LQGConfig | None = None) -> None:
        self.config = config or LQGConfig()
        self._k_gain: np.ndarray | None = None
        self._prev_dt = 0.0

    def _solve_dare(self, A: np.ndarray, B: np.ndarray, Q: np.ndarray, R: np.ndarray) -> np.ndarray:
        """Solve Discrete Algebraic Riccati Equation (DARE) via iterative fixed-point algorithm."""
        P = Q.copy()
        for _ in range(100):
            inv_term = np.linalg.inv(R + B.T @ P @ B)
            P_next = A.T @ P @ A - (A.T @ P @ B) @ inv_term @ (B.T @ P @ A) + Q
            if np.max(np.abs(P_next - P)) < 1e-6:
                P = P_next
                break
            P = P_next

        # K_LQR = (R + B^T P B)^-1 B^T P A
        K = np.linalg.inv(R + B.T @ P @ B) @ (B.T @ P @ A)
        return K

    def compute(
        self,
        error_pos_deg: float,
        error_vel_deg_s: float,
        dt: float,
    ) -> float:
        """Compute optimal LQR control effort for a single axis.

        Args:
            error_pos_deg: Pointing error [deg].
            error_vel_deg_s: Pointing rate error [deg/s].
            dt: Sample time step [s].

        Returns:
            Control command rate [deg/s].
        """
        if dt <= 0.0:
            return 0.0

        # Update gain matrix if dt changed significantly
        if abs(dt - self._prev_dt) > 1e-4 or self._k_gain is None:
            dt_c = min(0.1, max(1e-3, dt))
            A = np.array([[1.0, dt_c], [0.0, 1.0]], dtype=np.float64)
            B = np.array([[0.5 * dt_c**2], [dt_c]], dtype=np.float64)
            Q = np.diag([self.config.q_pos_weight, self.config.q_vel_weight]).astype(np.float64)
            R = np.array([[self.config.r_control_cost]], dtype=np.float64)

            try:
                self._k_gain = self._solve_dare(A, B, Q, R)
                self._prev_dt = dt
            except np.linalg.LinAlgError:
                self._k_gain = np.array([[1.5, 0.1]], dtype=np.float64)

        x_state = np.array([[error_pos_deg], [error_vel_deg_s]], dtype=np.float64)
        u_cmd = float((self._k_gain @ x_state).item())

        # Saturation clamping
        max_rate = self.config.max_output_deg_s
        return float(np.clip(u_cmd, -max_rate, max_rate))
