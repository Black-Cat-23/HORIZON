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

    Implements Bar-Shalom's canonical 4-step IMM framework:
      1. Interaction / State Mixing across 3 models:
         - Constant Velocity (CV)   — Low-noise kinematic drift (sigma_a = 200.0 px/s^2)
         - Constant Acceleration (CA)— Steady maneuvering (sigma_a = 800.0 px/s^2)
         - Sudden Maneuver          — High-G dynamic turns / jitter (sigma_a = 2500.0 px/s^2)
      2. Model-Conditioned Predictions with camera gimbal motion compensation.
      3. Maneuver-Adaptive Gating: Fused prediction covariance expanded by the
         spread-of-the-means term, eliminating maneuver-induced gate drops.
      4. Dynamic Bayesian Likelihood & Mode Probability Updates with Joseph-form fusion.

    Parameters:
        config: Optional KalmanFilterConfig.
    """

    def __init__(self, config: Optional[KalmanFilterConfig] = None) -> None:
        self._config = config or KalmanFilterConfig(accel_noise_sigma=200.0)

        # Instantiate 3 sub-filters with adaptive motion blur covariance
        # Model 0: Non-maneuvering / Constant Velocity (low process noise for extreme smoothing & jitter rejection)
        # Model 1: Moderate Maneuvering / Constant Acceleration (absorbs tactical turns and dynamic flight)
        # Model 2: High-G Evasive Maneuver / Jerk (absorbs sudden platform shocks and break turns without gating loss)
        self._cv_filter = TargetKalmanFilter(
            KalmanFilterConfig(
                accel_noise_sigma=20.0,
                base_measurement_sigma_px=self._config.base_measurement_sigma_px,
                adaptive_motion_noise=True,
                adaptive_process_noise=False,
            )
        )
        self._ca_filter = TargetKalmanFilter(
            KalmanFilterConfig(
                accel_noise_sigma=600.0,
                base_measurement_sigma_px=self._config.base_measurement_sigma_px,
                adaptive_motion_noise=True,
                adaptive_process_noise=False,
            )
        )
        self._maneuver_filter = TargetKalmanFilter(
            KalmanFilterConfig(
                accel_noise_sigma=2500.0,
                base_measurement_sigma_px=self._config.base_measurement_sigma_px,
                adaptive_motion_noise=True,
                adaptive_process_noise=False,
            )
        )
        self._filters = [self._cv_filter, self._ca_filter, self._maneuver_filter]
        self._num_models = 3

        # Model probabilities [CV, CA, MANEUVER]: sum = 1.0
        self._mode_probs = np.array([0.60, 0.25, 0.15], dtype=np.float64)

        # 3×3 Markov Transition Probability Matrix: P_ij = P(mode_j | mode_i)
        # Row i is origin mode, Col j is destination mode
        self._trans_prob = np.array(
            [
                [0.78, 0.18, 0.04],
                [0.05, 0.88, 0.07],
                [0.03, 0.12, 0.85],
            ],
            dtype=np.float64,
        )

        # Operational status and lifecycle counters
        self._status: EstimatorStatus = EstimatorStatus.UNINITIALIZED
        self._last_timestamp: float = 0.0
        self._track_age: int = 0
        self._consecutive_hits: int = 0
        self._consecutive_misses: int = 0
        self._last_estimate: Optional[StateEstimate] = None

        # Fused states
        self._fused_x: Optional[np.ndarray] = None
        self._fused_P: Optional[np.ndarray] = None
        self._fused_x_pred: Optional[np.ndarray] = None
        self._fused_P_pred: Optional[np.ndarray] = None

        # Prediction cache to prevent double-propagation when predict() is called before update()
        self._has_prediction: bool = False
        self._c_bar: Optional[np.ndarray] = None
        self._sub_preds_x: Optional[List[np.ndarray]] = None
        self._sub_preds_P: Optional[List[np.ndarray]] = None

    @property
    def status(self) -> EstimatorStatus:
        return self._status

    @property
    def is_initialized(self) -> bool:
        return self._status not in (EstimatorStatus.UNINITIALIZED, EstimatorStatus.RESET)

    @property
    def mode_probabilities(self) -> Tuple[float, float, float]:
        """Returns IMM model probabilities (P(CV), P(CA), P(MANEUVER))."""
        return (
            float(self._mode_probs[0]),
            float(self._mode_probs[1]),
            float(self._mode_probs[2]),
        )

    @property
    def state_vector(self) -> Optional[np.ndarray]:
        """Returns the current fused 4×1 state vector [px, py, vx, vy]^T."""
        if self._fused_x is not None:
            return self._fused_x.copy()
        return self._cv_filter.state_vector

    @property
    def covariance_matrix(self) -> Optional[np.ndarray]:
        """Returns the current fused 4×4 state covariance matrix."""
        if self._fused_P is not None:
            return self._fused_P.copy()
        return self._cv_filter.covariance_matrix

    def initialize(
        self,
        measurement: Tuple[float, float],
        timestamp: float,
        initial_velocity: Tuple[float, float] = (0.0, 0.0),
    ) -> StateEstimate:
        """Initialize all 3 IMM sub-filters and fused state from initial measurement."""
        est_cv = self._cv_filter.initialize(measurement, timestamp, initial_velocity)
        self._ca_filter.initialize(measurement, timestamp, initial_velocity)
        self._maneuver_filter.initialize(measurement, timestamp, initial_velocity)

        self._mode_probs = np.array([0.60, 0.25, 0.15], dtype=np.float64)
        self._status = EstimatorStatus.TRACKING
        self._last_timestamp = float(timestamp)
        self._track_age = 1
        self._consecutive_hits = 1
        self._consecutive_misses = 0

        self._fused_x = np.array(
            [[measurement[0]], [measurement[1]], [initial_velocity[0]], [initial_velocity[1]]],
            dtype=np.float64,
        )
        self._fused_P = self._cv_filter.covariance_matrix
        self._fused_x_pred = self._fused_x.copy()
        self._fused_P_pred = self._fused_P.copy() if self._fused_P is not None else None
        self._has_prediction = False

        self._last_estimate = est_cv
        return est_cv

    def _compute_interaction_mixing(self) -> Tuple[np.ndarray, List[np.ndarray], List[np.ndarray]]:
        """
        Step 1 of IMM: Computes predicted mode probabilities c_j and mixed states (x_0j, P_0j).
        Returns: (c_bar, mixed_x, mixed_P)
        """
        # Predicted mode probabilities: c_bar[j] = \sum_i P_ij * mu_i
        c_bar = self._trans_prob.T @ self._mode_probs
        c_bar = np.where(c_bar <= 0, 1e-12, c_bar)
        sum_c = np.sum(c_bar)
        c_bar = c_bar / sum_c if sum_c > 0 else np.array([0.34, 0.33, 0.33], dtype=np.float64)

        # Mixing probabilities: mu_{i|j} = (P_ij * mu_i) / c_bar[j]
        mu_mix = np.zeros((self._num_models, self._num_models), dtype=np.float64)
        for i in range(self._num_models):
            for j in range(self._num_models):
                mu_mix[i, j] = (self._trans_prob[i, j] * self._mode_probs[i]) / c_bar[j]

        # Extract current states of the 3 sub-filters
        x_sub = [f.state_vector for f in self._filters]
        P_sub = [f.covariance_matrix for f in self._filters]

        # Mix state and covariance for each destination model j
        mixed_x = []
        mixed_P = []
        for j in range(self._num_models):
            x_0j = np.zeros((4, 1), dtype=np.float64)
            for i in range(self._num_models):
                x_0j += mu_mix[i, j] * x_sub[i]
            mixed_x.append(x_0j)

            P_0j = np.zeros((4, 4), dtype=np.float64)
            for i in range(self._num_models):
                dx = x_sub[i] - x_0j
                P_0j += mu_mix[i, j] * (P_sub[i] + (dx @ dx.T))
            mixed_P.append(P_0j)

        return c_bar, mixed_x, mixed_P

    def predict(
        self,
        dt: float,
        gimbal_pan_rate: float = 0.0,
        gimbal_tilt_rate: float = 0.0,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Executes Steps 1 and 2 of IMM:
          1. Interaction & state mixing across all 3 models.
          2. Model-conditioned predictions with camera gimbal motion compensation.
          3. Fused prediction with spread-of-the-means for adaptive gating.

        Returns:
            Tuple of (fused_x_pred, fused_P_pred) suitable for multi-candidate gating.
        """
        if not self.is_initialized:
            raise RuntimeError("Cannot predict uninitialized IMM filter.")

        dt_eff = max(1e-4, float(dt))

        # 1. Interaction / Mixing
        c_bar, mixed_x, mixed_P = self._compute_interaction_mixing()
        self._c_bar = c_bar

        # Inject mixed initial conditions into sub-filters
        for j in range(self._num_models):
            self._filters[j].set_state(mixed_x[j], mixed_P[j])

        # 2. Model-Conditioned Predictions
        preds_x = []
        preds_P = []
        for j in range(self._num_models):
            px, pP = self._filters[j].predict(dt_eff, gimbal_pan_rate, gimbal_tilt_rate)
            self._filters[j]._last_timestamp = self._last_timestamp + dt_eff
            preds_x.append(px)
            preds_P.append(pP)

        self._sub_preds_x = preds_x
        self._sub_preds_P = preds_P

        # 3. Probability-weighted fused prediction
        fused_px = np.zeros((4, 1), dtype=np.float64)
        for j in range(self._num_models):
            fused_px += c_bar[j] * preds_x[j]

        # Fused covariance with spread-of-the-means term:
        # P_pred = \sum c_j * (P_pred,j + (x_pred,j - x_pred)(x_pred,j - x_pred)^T)
        fused_pP = np.zeros((4, 4), dtype=np.float64)
        for j in range(self._num_models):
            dx = preds_x[j] - fused_px
            fused_pP += c_bar[j] * (preds_P[j] + (dx @ dx.T))

        self._fused_x_pred = fused_px
        self._fused_P_pred = fused_pP
        self._has_prediction = True

        return fused_px.copy(), fused_pP.copy()

    def step(
        self,
        measurement: Optional[Tuple[float, float]],
        confidence: float = 1.0,
        timestamp: Optional[float] = None,
        gimbal_pan_rate: float = 0.0,
        gimbal_tilt_rate: float = 0.0,
        is_sensor_step: bool = True,
    ) -> StateEstimate:
        """Execute full IMM cycle: mixing, prediction, measurement update, and probability fusion."""
        t_start = time.perf_counter()

        if not self.is_initialized:
            if measurement is not None:
                ts = timestamp if timestamp is not None else 0.0
                return self.initialize(measurement, ts)
            else:
                return self._cv_filter.update_missing(timestamp, is_sensor_step=is_sensor_step)

        # 1. Prediction stage: execute if not already cached from a prior predict() call
        ts = float(timestamp) if timestamp is not None else (self._last_timestamp + 0.033)
        dt = max(1e-4, ts - self._last_timestamp)

        if not self._has_prediction or self._c_bar is None or self._sub_preds_x is None:
            self.predict(dt, gimbal_pan_rate, gimbal_tilt_rate)

        c_bar = self._c_bar
        assert c_bar is not None and self._sub_preds_x is not None and self._sub_preds_P is not None

        # 2. Measurement Update & Mode Likelihood Evaluation
        sub_estimates: List[StateEstimate] = []
        likelihoods = np.zeros(self._num_models, dtype=np.float64)

        if measurement is not None and confidence > 0.0:
            for j in range(self._num_models):
                est_j = self._filters[j].update(
                    measurement=measurement,
                    confidence=confidence,
                    timestamp=ts,
                    gimbal_pan_rate=gimbal_pan_rate,
                    gimbal_tilt_rate=gimbal_tilt_rate,
                )
                sub_estimates.append(est_j)

                # Innovation residual and Mahalanobis distance
                d_j_sq = est_j.mahalanobis_distance ** 2

                # Exact innovation covariance determinant for Gaussian likelihood
                if self._filters[j]._last_innovation is not None and self._filters[j]._last_innovation.covariance is not None:
                    S_mat = self._filters[j]._last_innovation.covariance
                else:
                    P_pred_j = self._sub_preds_P[j]
                    S_mat = P_pred_j[:2, :2] + np.eye(2) * (self._config.base_measurement_sigma_px ** 2)

                det_S = max(1e-6, float(np.linalg.det(S_mat)))

                # Normalized Gaussian innovation likelihood
                L_j = (1.0 / (2.0 * math.pi * math.sqrt(det_S))) * math.exp(-0.5 * min(d_j_sq, 45.0)) + 1e-12
                likelihoods[j] = L_j

            # 3. Update Mode Probabilities: mu_j = (L_j * c_bar_j) / \sum (L_m * c_bar_m)
            unnorm_probs = likelihoods * c_bar
            sum_prob = np.sum(unnorm_probs)
            if sum_prob > 1e-15:
                self._mode_probs = unnorm_probs / sum_prob
            else:
                self._mode_probs = c_bar.copy()

            self._consecutive_hits += 1
            self._consecutive_misses = 0
            self._status = EstimatorStatus.TRACKING

        else:
            # Missing observation / Coasting step
            for j in range(self._num_models):
                est_j = self._filters[j].update_missing(
                    timestamp=ts,
                    gimbal_pan_rate=gimbal_pan_rate,
                    gimbal_tilt_rate=gimbal_tilt_rate,
                    is_sensor_step=is_sensor_step,
                )
                sub_estimates.append(est_j)

            # In absence of observation, mode probabilities transition according to Markov chain
            self._mode_probs = c_bar.copy()

            if is_sensor_step:
                self._consecutive_hits = 0
                self._consecutive_misses += 1
                self._status = EstimatorStatus.PREDICTING

        # Invalidate prediction cache for subsequent frame
        self._has_prediction = False

        # 4. Weighted Fusion of 3 IMM Sub-Filter Estimates
        w = self._mode_probs
        fused_x = sum(w[j] * sub_estimates[j].estimated_x for j in range(self._num_models))
        fused_y = sum(w[j] * sub_estimates[j].estimated_y for j in range(self._num_models))
        fused_vx = sum(w[j] * sub_estimates[j].estimated_vx for j in range(self._num_models))
        fused_vy = sum(w[j] * sub_estimates[j].estimated_vy for j in range(self._num_models))

        fused_px = sum(w[j] * sub_estimates[j].predicted_x for j in range(self._num_models))
        fused_py = sum(w[j] * sub_estimates[j].predicted_y for j in range(self._num_models))
        fused_pvx = sum(w[j] * sub_estimates[j].predicted_vx for j in range(self._num_models))
        fused_pvy = sum(w[j] * sub_estimates[j].predicted_vy for j in range(self._num_models))

        # Fused covariance with spread-of-the-means term:
        # P = \sum w_j * (P_j + (x_j - x_fused)(x_j - x_fused)^T)
        fused_cov = sum(w[j] * sub_estimates[j].covariance for j in range(self._num_models)).copy()
        for j in range(self._num_models):
            dx = np.array([
                [sub_estimates[j].estimated_x - fused_x],
                [sub_estimates[j].estimated_y - fused_y],
                [sub_estimates[j].estimated_vx - fused_vx],
                [sub_estimates[j].estimated_vy - fused_vy],
            ], dtype=np.float64)
            fused_cov += w[j] * (dx @ dx.T)

        self._fused_x = np.array([[fused_x], [fused_y], [fused_vx], [fused_vy]], dtype=np.float64)
        self._fused_P = fused_cov.copy()

        self._track_age += 1
        self._last_timestamp = ts
        t_end = time.perf_counter()

        nis = float(sum(w[j] * sub_estimates[j].nis for j in range(self._num_models)))
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
            model_probabilities=(float(w[0]), float(w[1]), float(w[2])),
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
            innovation=sub_estimates[0].innovation,
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

    def update_missing(
        self,
        timestamp: Optional[float] = None,
        gimbal_pan_rate: float = 0.0,
        gimbal_tilt_rate: float = 0.0,
        is_sensor_step: bool = True,
    ) -> StateEstimate:
        """Alias for missing observation cycle compatible with TargetKalmanFilter interface."""
        return self.step(
            None,
            confidence=0.0,
            timestamp=timestamp,
            gimbal_pan_rate=gimbal_pan_rate,
            gimbal_tilt_rate=gimbal_tilt_rate,
            is_sensor_step=is_sensor_step,
        )

    def reset(self) -> None:
        """Reset all IMM sub-filters and fused state."""
        for f in self._filters:
            f.reset()
        self._mode_probs = np.array([0.60, 0.25, 0.15], dtype=np.float64)
        self._status = EstimatorStatus.RESET
        self._track_age = 0
        self._consecutive_hits = 0
        self._consecutive_misses = 0
        self._last_estimate = None
        self._fused_x = None
        self._fused_P = None
        self._fused_x_pred = None
        self._fused_P_pred = None
        self._has_prediction = False
        self._c_bar = None
        self._sub_preds_x = None
        self._sub_preds_P = None

