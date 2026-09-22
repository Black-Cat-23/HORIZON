"""
HORIZON Ground-Truth Tracking Evaluation Engine
======================================================
Isolated benchmarking and accuracy evaluation utility.

Strict Scope Isolation:
    This module is strictly for offline or post-step verification and validation.
    The core tracking and estimation modules (tracking.estimation, tracking.association)
    do NOT import, reference, or access this evaluation module.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import math
from typing import List, Optional, Tuple
import numpy as np


@dataclass(frozen=True)
class TrackingErrorSample:
    """Individual time-step tracking evaluation error sample."""
    timestamp: float
    pos_error_px: float
    vel_error_px_s: float
    nees: float  # Normalized Estimation Error Squared


@dataclass(frozen=True)
class EvaluationMetrics:
    """Aggregated statistical evaluation metrics."""
    samples_count: int
    position_rmse: float
    position_error_mean: float
    position_error_median: float
    position_error_p95: float
    position_error_p99: float
    position_error_max: float
    velocity_rmse: float
    velocity_error_mean: float
    velocity_error_median: float
    velocity_error_p95: float
    velocity_error_p99: float
    velocity_error_max: float
    mean_nees: float


class EstimatorEvaluator:
    """Compares estimated target states against true projected kinematics."""

    def __init__(self) -> None:
        self._samples: List[TrackingErrorSample] = []
        self._pos_errors: List[float] = []
        self._vel_errors: List[float] = []
        self._nees_values: List[float] = []

    @property
    def sample_count(self) -> int:
        return len(self._samples)

    def record_step(
        self,
        estimated_pos: Tuple[float, float],
        estimated_vel: Tuple[float, float],
        covariance: np.ndarray,
        gt_pos: Tuple[float, float],
        gt_vel: Tuple[float, float],
        timestamp: float = 0.0,
    ) -> TrackingErrorSample:
        """Record an error sample comparing estimate to ground truth.

        Args:
            estimated_pos: (u_hat, v_hat) in pixels.
            estimated_vel: (vx_hat, vy_hat) in px/s.
            covariance: 4×4 state covariance matrix.
            gt_pos: (u_true, v_true) projected ground truth in pixels.
            gt_vel: (vx_true, vy_true) true velocity in pixels/s.
            timestamp: Simulation timestamp.

        Returns:
            TrackingErrorSample.
        """
        # Positional Euclidean error
        dx = float(estimated_pos[0] - gt_pos[0])
        dy = float(estimated_pos[1] - gt_pos[1])
        pos_err = math.sqrt(dx * dx + dy * dy)

        # Velocity Euclidean error
        dvx = float(estimated_vel[0] - gt_vel[0])
        dvy = float(estimated_vel[1] - gt_vel[1])
        vel_err = math.sqrt(dvx * dvx + dvy * dvy)

        # Normalized Estimation Error Squared (NEES)
        # epsilon_x = (x - x_true)^T * P^-1 * (x - x_true)
        err_vec = np.array([[dx], [dy], [dvx], [dvy]], dtype=np.float64)
        try:
            # Solve P * v = err_vec
            v = np.linalg.solve(covariance, err_vec)
            nees = float((err_vec.T @ v).item())
            nees = max(0.0, nees)
        except np.linalg.LinAlgError:
            nees = float((err_vec.T @ np.linalg.pinv(covariance) @ err_vec).item())
            nees = max(0.0, nees)

        sample = TrackingErrorSample(
            timestamp=timestamp,
            pos_error_px=pos_err,
            vel_error_px_s=vel_err,
            nees=nees,
        )

        self._samples.append(sample)
        self._pos_errors.append(pos_err)
        self._vel_errors.append(vel_err)
        self._nees_values.append(nees)

        return sample

    def compute_metrics(self) -> EvaluationMetrics:
        """Compute aggregated statistical summary metrics."""
        n = len(self._samples)
        if n == 0:
            return EvaluationMetrics(
                samples_count=0,
                position_rmse=0.0,
                position_error_mean=0.0,
                position_error_median=0.0,
                position_error_p95=0.0,
                position_error_p99=0.0,
                position_error_max=0.0,
                velocity_rmse=0.0,
                velocity_error_mean=0.0,
                velocity_error_median=0.0,
                velocity_error_p95=0.0,
                velocity_error_p99=0.0,
                velocity_error_max=0.0,
                mean_nees=0.0,
            )

        pos_arr = np.array(self._pos_errors, dtype=np.float64)
        vel_arr = np.array(self._vel_errors, dtype=np.float64)
        nees_arr = np.array(self._nees_values, dtype=np.float64)

        pos_rmse = float(np.sqrt(np.mean(pos_arr ** 2)))
        vel_rmse = float(np.sqrt(np.mean(vel_arr ** 2)))

        return EvaluationMetrics(
            samples_count=n,
            position_rmse=pos_rmse,
            position_error_mean=float(np.mean(pos_arr)),
            position_error_median=float(np.median(pos_arr)),
            position_error_p95=float(np.percentile(pos_arr, 95)),
            position_error_p99=float(np.percentile(pos_arr, 99)),
            position_error_max=float(np.max(pos_arr)),
            velocity_rmse=vel_rmse,
            velocity_error_mean=float(np.mean(vel_arr)),
            velocity_error_median=float(np.median(vel_arr)),
            velocity_error_p95=float(np.percentile(vel_arr, 95)),
            velocity_error_p99=float(np.percentile(vel_arr, 99)),
            velocity_error_max=float(np.max(vel_arr)),
            mean_nees=float(np.mean(nees_arr)),
        )

    def reset(self) -> None:
        """Clear all evaluation records."""
        self._samples.clear()
        self._pos_errors.clear()
        self._vel_errors.clear()
        self._nees_values.clear()
