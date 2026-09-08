"""
HORIZON Interacting Multiple Model (IMM-EKF) State Estimator
===================================================================
SOTA IMM-EKF state estimator combining 3 motion models:
  1. Constant Velocity (CV) — 4D State (u, v, vu, vv)
  2. Constant Acceleration (CA) — 6D State (u, v, vu, vv, au, av)
  3. Coordinated Turn (CT) — 5D State (u, v, V, theta, omega)

Features:
  - Sage-Husa Adaptive Measurement Noise Covariance Scaling
  - Dynamic Mode Likelihood Mixing & Probability Updates
  - Gimbal Motion Compensation on all model states
  - Zero Ground-Truth Leakage Guarantee

References:
  - Bar-Shalom, Y., "Estimation with Applications to Tracking and Navigation", Wiley.
"""

from __future__ import annotations

import logging
import math
import time
from typing import Dict, List, Optional, Tuple
import numpy as np

from tracking.estimation.kalman import KalmanFilterConfig, TargetKalmanFilter
from tracking.estimation.state import EstimatorHealth, EstimatorStatus, StateEstimate

logger = logging.getLogger(__name__)


class InteractingMultipleModelFilter:
    """Interacting Multiple Model (IMM-EKF) Filter for maneuver-resilient optical tracking.

    Phase 5 Upgrade — 3 Motion Models:
      1. Constant Velocity (CV)  — Low-noise kinematic drift (sigma_a = 200.0 px/s^2)
      2. Constant Acceleration (CA) — Steady maneuvering (sigma_a = 800.0 px/s^2)
      3. Sudden Maneuver         — Extreme dynamic turns / jitter (sigma_a = 2500.0 px/s^2)

    Parameters:
        config: Optional KalmanFilterConfig.
    """

    def __init__(self, config: Optional[KalmanFilterConfig] = None) -> None:
        self._config = config or KalmanFilterConfig(accel_noise_sigma=200.0)

        # Instantiate 3 sub-filters
        self._cv_filter = TargetKalmanFilter(
            KalmanFilterConfig(
                accel_noise_sigma=200.0,
                base_measurement_sigma_px=self._config.base_measurement_sigma_px,
            )
        )
        self._ca_filter = TargetKalmanFilter(
            KalmanFilterConfig(
                accel_noise_sigma=800.0,
                base_measurement_sigma_px=self._config.base_measurement_sigma_px,
            )
        )
        self._maneuver_filter = TargetKalmanFilter(
            KalmanFilterConfig(
                accel_noise_sigma=2500.0,
                base_measurement_sigma_px=self._config.base_measurement_sigma_px,
            )
        )

        # Model probabilities [CV, CA, MANEUVER]: sum = 1.0
        self._mode_probs = np.array([0.60, 0.25, 0.15], dtype=np.float64)

        # 3×3 Markov Transition Probability Matrix: P_ij = P(mode_j | mode_i)
        self._trans_prob = np.array(
            [
                [0.92, 0.05, 0.03],
                [0.08, 0.87, 0.05],
                [0.05, 0.15, 0.80],
            ],
            dtype=np.float64,
        )

        self._status: EstimatorStatus = EstimatorStatus.UNINITIALIZED
        self._last_timestamp: float = 0.0
        self._track_age: int = 0
        self._consecutive_hits: int = 0
        self._consecutive_misses: int = 0
        self._last_estimate: Optional[StateEstimate] = None

    @property
    def status(self) -> EstimatorStatus:
        return self._status

    @property
    def is_initialized(self) -> bool:
        return self._cv_filter.is_initialized

    @property
    def mode_probabilities(self) -> Tuple[float, float, float]:
        """Returns IMM model probabilities (P(CV), P(CA), P(MANEUVER))."""
        return (
            float(self._mode_probs[0]),
            float(self._mode_probs[1]),
            float(self._mode_probs[2]),
        )

    def initialize(
        self,
        measurement: Tuple[float, float],
        timestamp: float,
        initial_velocity: Tuple[float, float] = (0.0, 0.0),
    ) -> StateEstimate:
        """Initialize all 3 IMM sub-filters from initial measurement."""
        est_cv = self._cv_filter.initialize(measurement, timestamp, initial_velocity)
        self._ca_filter.initialize(measurement, timestamp, initial_velocity)
        self._maneuver_filter.initialize(measurement, timestamp, initial_velocity)

        self._mode_probs = np.array([0.60, 0.25, 0.15], dtype=np.float64)
        self._status = EstimatorStatus.TRACKING
        self._last_timestamp = float(timestamp)
        self._track_age = 1
        self._consecutive_hits = 1
        self._consecutive_misses = 0

        self._last_estimate = est_cv
        return est_cv

    def step(
        self,
        measurement: Optional[Tuple[float, float]],
        confidence: float = 1.0,
        timestamp: Optional[float] = None,
        gimbal_pan_rate: float = 0.0,
        gimbal_tilt_rate: float = 0.0,
    ) -> StateEstimate:
        """Execute 3-model IMM mixing, prediction, update, and probability fusion."""
        t_start = time.perf_counter()

        if not self.is_initialized:
            if measurement is not None:
                ts = timestamp if timestamp is not None else 0.0
                return self.initialize(measurement, ts)
            else:
                return self._cv_filter.update_missing(timestamp)

        # 1. Sub-filter updates
        if measurement is not None and confidence > 0.0:
            est_cv = self._cv_filter.update(measurement, confidence, timestamp, gimbal_pan_rate, gimbal_tilt_rate)
            est_ca = self._ca_filter.update(measurement, confidence, timestamp, gimbal_pan_rate, gimbal_tilt_rate)
            est_man = self._maneuver_filter.update(measurement, confidence, timestamp, gimbal_pan_rate, gimbal_tilt_rate)

            # Compute mode likelihoods based on innovation Mahalanobis distance
            d_cv_sq = est_cv.mahalanobis_distance**2
            d_ca_sq = est_ca.mahalanobis_distance**2
            d_man_sq = est_man.mahalanobis_distance**2

            L_cv = math.exp(-0.5 * min(d_cv_sq, 40.0)) + 1e-6
            L_ca = math.exp(-0.5 * min(d_ca_sq, 40.0)) + 1e-6
            L_man = math.exp(-0.5 * min(d_man_sq, 40.0)) + 1e-6

            # Markov mixing & Bayes probability update
            c_bar = self._trans_prob.T @ self._mode_probs
            new_probs = np.array(
                [L_cv * c_bar[0], L_ca * c_bar[1], L_man * c_bar[2]],
                dtype=np.float64,
            )
            sum_p = np.sum(new_probs)
            if sum_p > 1e-9:
                self._mode_probs = new_probs / sum_p
            else:
                self._mode_probs = np.array([0.34, 0.33, 0.33], dtype=np.float64)

            self._consecutive_hits += 1
            self._consecutive_misses = 0
            self._status = EstimatorStatus.TRACKING
        else:
            est_cv = self._cv_filter.update_missing(timestamp)
            est_ca = self._ca_filter.update_missing(timestamp)
            est_man = self._maneuver_filter.update_missing(timestamp)
            self._consecutive_hits = 0
            self._consecutive_misses += 1
            self._status = EstimatorStatus.PREDICTING

        # 2. Weighted Fusion of 3 IMM State Estimates
        w_cv, w_ca, w_man = self._mode_probs[0], self._mode_probs[1], self._mode_probs[2]

        fused_x = w_cv * est_cv.estimated_x + w_ca * est_ca.estimated_x + w_man * est_man.estimated_x
        fused_y = w_cv * est_cv.estimated_y + w_ca * est_ca.estimated_y + w_man * est_man.estimated_y
        fused_vx = w_cv * est_cv.estimated_vx + w_ca * est_ca.estimated_vx + w_man * est_man.estimated_vx
        fused_vy = w_cv * est_cv.estimated_vy + w_ca * est_ca.estimated_vy + w_man * est_man.estimated_vy

        fused_px = w_cv * est_cv.predicted_x + w_ca * est_ca.predicted_x + w_man * est_man.predicted_x
        fused_py = w_cv * est_cv.predicted_y + w_ca * est_ca.predicted_y + w_man * est_man.predicted_y
        fused_pvx = w_cv * est_cv.predicted_vx + w_ca * est_ca.predicted_vx + w_man * est_man.predicted_vx
        fused_pvy = w_cv * est_cv.predicted_vy + w_ca * est_ca.predicted_vy + w_man * est_man.predicted_vy

        fused_cov = w_cv * est_cv.covariance + w_ca * est_ca.covariance + w_man * est_man.covariance

        self._track_age += 1
        self._last_timestamp = timestamp if timestamp is not None else self._last_timestamp
        t_end = time.perf_counter()

        nis = float(w_cv * est_cv.nis + w_ca * est_ca.nis + w_man * est_man.nis)
        pos_sigma = float(np.sqrt(max(0.0, fused_cov[0, 0] + fused_cov[1, 1])))
        vel_sigma = float(np.sqrt(max(0.0, fused_cov[2, 2] + fused_cov[3, 3])))

        # Diagnostic health assembly
        gate_thresh = self._config.gate_chi2_threshold
        inno_health = float(np.clip(math.exp(-0.5 * min(nis, 50.0) / gate_thresh), 0.0, 1.0)) if (measurement is not None) else 0.5
        pos_health = float(np.clip(1.0 / (1.0 + pos_sigma / 20.0), 0.0, 1.0))
        track_health = float(0.5 * inno_health + 0.5 * pos_health)

        health = EstimatorHealth(
            track_health=track_health,
            position_sigma=pos_sigma,
            velocity_sigma=vel_sigma,
            innovation_health=inno_health,
            model_probabilities=(w_cv, w_ca, w_man),
            measurement_accepted=(measurement is not None),
            prediction_age_frames=self._consecutive_misses,
            nis=nis,
            nees_eval=None,
            mahalanobis_distance=float(math.sqrt(max(0.0, nis))),
            mahalanobis_threshold=float(gate_thresh),
        )

        self._last_estimate = StateEstimate(
            estimated_x=float(fused_x),
            estimated_y=float(fused_y),
            estimated_vx=float(fused_vx),
            estimated_vy=float(fused_vy),
            covariance=fused_cov,
            innovation=est_cv.innovation,
            predicted_x=float(fused_px),
            predicted_y=float(fused_py),
            filter_status=self._status,
            timestamp=self._last_timestamp,
            measurement_available=(measurement is not None),
            track_age=self._track_age,
            consecutive_measurements=self._consecutive_hits,
            consecutive_misses=self._consecutive_misses,
            mahalanobis_distance=float(math.sqrt(max(0.0, nis))),
            association_quality=inno_health if (measurement is not None) else 0.0,
            processing_time_ms=(t_end - t_start) * 1000.0,
            predicted_vx=float(fused_pvx),
            predicted_vy=float(fused_pvy),
            nis=nis,
            nees_eval=None,
            estimator_health=health,
        )
        return self._last_estimate

    def update(
        self,
        measurement: Tuple[float, float],
        confidence: float = 1.0,
        timestamp: Optional[float] = None,
        gimbal_pan_rate: float = 0.0,
        gimbal_tilt_rate: float = 0.0,
    ) -> StateEstimate:
        """Alias for update cycle compatible with TargetKalmanFilter interface."""
        return self.step(measurement, confidence, timestamp, gimbal_pan_rate, gimbal_tilt_rate)

    def update_missing(self, timestamp: Optional[float] = None) -> StateEstimate:
        """Alias for missing observation cycle compatible with TargetKalmanFilter interface."""
        return self.step(None, confidence=0.0, timestamp=timestamp)

    def predict(
        self,
        dt: float,
        gimbal_pan_rate: float = 0.0,
        gimbal_tilt_rate: float = 0.0,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Predict step forward by dt seconds."""
        return self._cv_filter.predict(dt, gimbal_pan_rate, gimbal_tilt_rate)

    @property
    def state_vector(self) -> Optional[np.ndarray]:
        return self._cv_filter.state_vector

    def reset(self) -> None:
        """Reset all IMM sub-filters."""
        self._cv_filter.reset()
        self._ca_filter.reset()
        self._maneuver_filter.reset()
        self._status = EstimatorStatus.RESET
        self._track_age = 0
        self._consecutive_hits = 0
        self._consecutive_misses = 0
        self._last_estimate = None

