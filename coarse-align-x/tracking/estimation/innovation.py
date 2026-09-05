"""
HORIZON Innovation & Residual Mathematics
================================================
Calculates observation residuals, innovation covariance matrices,
Euclidean residual norms, and squared Mahalanobis statistical distances.

Strict Invariant: Zero access to true target position or ground-truth state.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Optional, Tuple
import numpy as np


@dataclass(frozen=True)
class Innovation:
    """Kalman innovation (measurement residual) container."""
    residual: np.ndarray          # Shape: (2, 1) float64 [px]
    covariance: np.ndarray        # Shape: (2, 2) float64 [px^2]
    mahalanobis_sq: float         # d^2 = y^T * S^-1 * y (dimensionless)
    mahalanobis_distance: float   # d = sqrt(d^2)
    norm: float                   # Euclidean norm ||y||_2 [px]
    is_valid: bool = True

    @property
    def residual_x(self) -> float:
        """Horizontal residual component [px]."""
        return float(self.residual[0, 0])

    @property
    def residual_y(self) -> float:
        """Vertical residual component [px]."""
        return float(self.residual[1, 0])


def compute_innovation(
    z: np.ndarray,
    x_pred: np.ndarray,
    P_pred: np.ndarray,
    H: np.ndarray,
    R: np.ndarray,
) -> Innovation:
    """Compute observation residual y, innovation covariance S, and Mahalanobis distance.

    Equations:
        y = z - H * x_pred
        S = H * P_pred * H^T + R
        d^2 = y^T * S^-1 * y

    Numerical Stability:
        d^2 is evaluated using a linear system solve (np.linalg.solve)
        rather than explicit matrix inversion to minimize roundoff error:
            S * v = y  ==>  v = S^-1 * y
            d^2 = y^T * v

    Args:
        z: Observation vector, shape (2, 1) or (2,) [px].
        x_pred: Predicted state vector, shape (4, 1) [px, px/s].
        P_pred: Predicted covariance matrix, shape (4, 4).
        H: Observation matrix, shape (2, 4).
        R: Measurement noise matrix, shape (2, 2).

    Returns:
        Innovation dataclass.
    """
    z_col = np.asarray(z, dtype=np.float64).reshape((2, 1))
    x_col = np.asarray(x_pred, dtype=np.float64).reshape((4, 1))

    # Measurement residual
    y = z_col - (H @ x_col)

    # Innovation covariance S = H P_pred H^T + R
    S = (H @ P_pred @ H.T) + R
    S = 0.5 * (S + S.T)  # enforce symmetry

    # Euclidean norm
    res_norm = float(np.linalg.norm(y))

    # Mahalanobis distance d^2 = y^T * S^-1 * y
    try:
        # Solve S * v = y
        v = np.linalg.solve(S, y)
        d2 = float((y.T @ v).item())
        # Numerical guard: variance cannot be negative
        d2 = max(0.0, d2)
        d = math.sqrt(d2)
        valid = bool(np.isfinite(d2))
    except np.linalg.LinAlgError:
        # Ill-conditioned S fallback: pseudo-inverse
        S_pinv = np.linalg.pinv(S)
        d2 = float((y.T @ S_pinv @ y).item())
        d2 = max(0.0, d2)
        d = math.sqrt(d2)
        valid = False

    return Innovation(
        residual=y,
        covariance=S,
        mahalanobis_sq=d2,
        mahalanobis_distance=d,
        norm=res_norm,
        is_valid=valid,
    )
