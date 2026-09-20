"""
HORIZON Statistical Mahalanobis Gating
============================================
Statistical validation gating for optical beacon detections using
Chi-squared distance testing.

Theoretical Basis:
    Under linear Gaussian assumptions, the measurement residual
    y = z - H * x_pred is distributed as:
        y ~ N(0, S)
    The squared Mahalanobis distance:
        d^2 = y^T * S^-1 * y
    follows a Chi-squared distribution with n_z degrees of freedom
    (here n_z = 2 for image coordinates [u, v]):
        d^2 ~ ChiSq(2)

    Standard Chi-squared thresholds for 2 DOF:
        p = 0.90  ==>  gamma = 4.605
        p = 0.95  ==>  gamma = 5.991
        p = 0.99  ==>  gamma = 9.210  (Nominal default)
        p = 0.999 ==>  gamma = 13.816

Strict Invariant: Zero access to true target position or ground-truth state.
"""

from __future__ import annotations

import math
from typing import Optional, Tuple
import numpy as np

from tracking.estimation.innovation import compute_innovation

# Standard Chi-squared cumulative distribution thresholds for 2 Degrees of Freedom
CHI2_2DOF_THRESHOLDS = {
    0.90: 4.605,
    0.95: 5.991,
    0.99: 9.210,
    0.999: 13.816,
}


class MahalanobisGate:
    """Statistical ellipsoidal validation gate for measurement association and outlier rejection."""

    def __init__(self, threshold: float = 9.210) -> None:
        """Initialize gate with Chi-squared threshold.

        PROJECT ENGINEERING PARAMETER:
            threshold: Default 9.210 corresponds to 99% probability gate for 2 DOF.
        """
        if threshold <= 0.0:
            raise ValueError(f"Gate threshold must be strictly positive, got {threshold}")
        self._threshold = float(threshold)

    @property
    def threshold(self) -> float:
        return self._threshold

    def test(
        self,
        z: np.ndarray,
        x_pred: np.ndarray,
        P_pred: np.ndarray,
        H: np.ndarray,
        R: np.ndarray,
        custom_threshold: Optional[float] = None,
    ) -> Tuple[bool, float, float]:
        """Test whether observation z falls within the validation ellipsoid.

        Args:
            z: Observation vector (2,) or (2, 1).
            x_pred: Predicted state vector (4, 1).
            P_pred: Predicted covariance matrix (4, 4).
            H: Measurement matrix (2, 4).
            R: Measurement noise covariance (2, 2).
            custom_threshold: Optional override for gate threshold.

        Returns:
            Tuple of (is_within_gate, mahalanobis_sq, mahalanobis_distance)
        """
        thresh = custom_threshold if custom_threshold is not None else self._threshold

        inno = compute_innovation(z, x_pred, P_pred, H, R)
        d2 = inno.mahalanobis_sq
        d = inno.mahalanobis_distance

        is_valid = bool(d2 <= thresh and inno.is_valid)
        return is_valid, d2, d
