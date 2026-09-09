"""
HORIZON Optical Target Kalman Filter Engine
===================================================
Constant-Velocity Kalman filter with continuous white noise acceleration,
Joseph-form covariance stabilization, Mahalanobis gating, and missing
observation prediction handling.

Strict Invariant: Zero access to true target position or ground-truth state.
All state calculations are derived strictly from sensor measurements and models.
"""

from __future__ import annotations

from dataclasses import dataclass
import logging
import math
import time
from typing import Optional, Tuple
import numpy as np

from tracking.estimation.covariance import (
    compute_covariance_ellipse,
    enforce_symmetry,
    validate_covariance,
)
from tracking.estimation.innovation import Innovation, compute_innovation
from tracking.estimation.model import (
    build_measurement_matrix,
    build_measurement_noise_matrix,
    build_process_noise_matrix,
    build_transition_matrix,
)
from tracking.estimation.state import EstimatorHealth, EstimatorStatus, StateEstimate
from tracking.quality.track_quality import TrackQuality, evaluate_track_quality

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class KalmanFilterConfig:
    """Tuning parameters for the constant-velocity Kalman filter.

    All numerical parameters are PROJECT ENGINEERING PARAMETERS.
    """
    # Unmodeled target acceleration standard deviation [px/s^2]
    # Accommodates dynamic flight maneuvers, platform motion, and camera jitter (up to ~600 px/s^2)
    accel_noise_sigma: float = 600.0

    # Nominal perception centroid measurement noise at confidence=1.0 [px]
    base_measurement_sigma_px: float = 0.5

    # Initial position uncertainty standard deviation [px]
    initial_pos_sigma_px: float = 5.0

    # Initial velocity uncertainty standard deviation [px/s]
    # High initial uncertainty allows filter to rapidly learn velocity from subsequent frames
    initial_vel_sigma_px_s: float = 120.0

    # Chi-square gate threshold for 2 DOF (p=0.99 -> 9.21, robust maneuvering -> 16.0)
    gate_chi2_threshold: float = 16.0

    # Maximum consecutive rejections before re-acquiring on confident beacon detection
    max_consecutive_rejections_before_reacquire: int = 2

    # Enable numerically stable Joseph-form covariance update:
    # P = (I - KH) P_pred (I - KH)^T + K R K^T
    use_joseph_form: bool = True

    # Process noise model formulation: 'cwna' (Continuous White Noise Acceleration)
    process_model_type: str = "cwna"

    # Minimum valid dt to guard against duplicate/stale timestamps [seconds]
    min_dt_seconds: float = 1e-4

    # Maximum valid dt before warning or forced coast clamp [seconds]
    max_dt_seconds: float = 2.0


class TargetKalmanFilter:
    """Discrete-time Constant-Velocity Kalman Filter for optical beacon tracking.

    Operates in sensor 2D image coordinates (u, v) and pixel velocities (v_u, v_v).
    """

    def __init__(self, config: Optional[KalmanFilterConfig] = None) -> None:
        self._config = config or KalmanFilterConfig()
        self._H = build_measurement_matrix()

        # Internal state vector x: (4, 1) float64
        self._x: Optional[np.ndarray] = None
        # Internal covariance matrix P: (4, 4) float64
        self._P: Optional[np.ndarray] = None

        # Predicted state vector x_pred: (4, 1) float64
        self._x_pred: Optional[np.ndarray] = None
        # Predicted covariance matrix P_pred: (4, 4) float64
        self._P_pred: Optional[np.ndarray] = None

        # Operational status
        self._status: EstimatorStatus = EstimatorStatus.UNINITIALIZED
        self._last_timestamp: float = 0.0
        self._track_age: int = 0
        self._consecutive_hits: int = 0
        self._consecutive_misses: int = 0
        self._last_innovation: Optional[Innovation] = None

    @property
    def config(self) -> KalmanFilterConfig:
        return self._config

    @property
    def status(self) -> EstimatorStatus:
        return self._status

    @property
    def is_initialized(self) -> bool:
        return self._status not in (EstimatorStatus.UNINITIALIZED, EstimatorStatus.RESET)

    @property
    def state_vector(self) -> Optional[np.ndarray]:
        """Current 4×1 state vector [px, py, vx, vy]^T."""
        return self._x.copy() if self._x is not None else None

    @property
    def covariance_matrix(self) -> Optional[np.ndarray]:
        """Current 4×4 state covariance matrix."""
        return self._P.copy() if self._P is not None else None

    def initialize(
        self,
        measurement: Tuple[float, float],
        timestamp: float,
        initial_velocity: Tuple[float, float] = (0.0, 0.0),
    ) -> StateEstimate:
        """Initialize the filter state from an initial measurement.

        INITIALIZATION POLICY:
            - Position is set directly to the initial observation z_0.
            - Velocity is initialized to zero (0.0, 0.0) px/s (preferred policy)
              or user-configured prior.
            - Initial covariance P_0 is diagonal with position variance sigma_p0^2
              and large velocity variance sigma_v0^2, ensuring subsequent updates
              rapidly estimate the true kinematic velocity without bias.

        Strict Invariant: Ground-truth velocity is NEVER used for initialization.
        """
        t_start = time.perf_counter()
        zx, zy = measurement
        vx0, vy0 = initial_velocity

        self._x = np.array([[zx], [zy], [vx0], [vy0]], dtype=np.float64)
        self._x_pred = self._x.copy()

        p_var = self._config.initial_pos_sigma_px ** 2
        v_var = self._config.initial_vel_sigma_px_s ** 2

        self._P = np.diag([p_var, p_var, v_var, v_var]).astype(np.float64)
        self._P_pred = self._P.copy()

        self._last_timestamp = float(timestamp)
        self._track_age = 1
        self._consecutive_hits = 1
        self._consecutive_misses = 0
        self._status = EstimatorStatus.TRACKING
        self._last_innovation = None

        t_end = time.perf_counter()
        return self._build_estimate(
            innovation=None,
            measurement_available=True,
            mahalanobis_dist=0.0,
            proc_ms=(t_end - t_start) * 1000.0,
        )

    def predict(
        self,
        dt: float,
        gimbal_pan_rate: float = 0.0,
        gimbal_tilt_rate: float = 0.0,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Propagate state and covariance forward by timestep dt with gimbal motion compensation.

        State propagation:
            x_pred = F(dt) * P * F(dt)^T + Q(dt)
            x_pred[u] += -gimbal_pan_rate * (640 / 4.0) * dt
            x_pred[v] += -gimbal_tilt_rate * (480 / 3.0) * dt

        Args:
            dt: Time delta in seconds. Must satisfy min_dt <= dt <= max_dt.
            gimbal_pan_rate: Current camera pan rate in deg/s.
            gimbal_tilt_rate: Current camera tilt rate in deg/s.

        Returns:
            Tuple of (x_pred, P_pred).
        """
        if not self.is_initialized or self._x is None or self._P is None:
            raise RuntimeError("Cannot predict uninitialized Kalman filter.")

        if dt <= 0.0:
            logger.warning("Predict called with non-positive dt=%s; retaining prior state", dt)
            return self._x_pred.copy(), self._P_pred.copy()

        # Clamp dt if unexpectedly large (e.g. system pause)
        dt_clamped = min(dt, self._config.max_dt_seconds)

        # 1. State transition matrix F(dt)
        F = build_transition_matrix(dt_clamped)

        # 2. Process noise covariance matrix Q(dt)
        Q = build_process_noise_matrix(
            dt=dt_clamped,
            accel_noise_sigma=self._config.accel_noise_sigma,
            model_type=self._config.process_model_type,  # type: ignore
        )

        # 3. Propagate state: x_pred = F * x
        self._x_pred = F @ self._x

        # 3b. Gimbal motion compensation: camera rotation shifts image pixel coordinates
        if abs(gimbal_pan_rate) > 1e-4 or abs(gimbal_tilt_rate) > 1e-4:
            shift_u = -gimbal_pan_rate * (640.0 / 4.0) * dt_clamped
            shift_v = -gimbal_tilt_rate * (480.0 / 3.0) * dt_clamped
            self._x_pred[0, 0] += shift_u
            self._x_pred[1, 0] += shift_v

        # 4. Propagate covariance: P_pred = F * P * F^T + Q
        P_pred = (F @ self._P @ F.T) + Q
        self._P_pred = enforce_symmetry(P_pred)

        return self._x_pred.copy(), self._P_pred.copy()

    def update(
        self,
        measurement: Tuple[float, float],
        confidence: float = 1.0,
        timestamp: Optional[float] = None,
        gimbal_pan_rate: float = 0.0,
        gimbal_tilt_rate: float = 0.0,
    ) -> StateEstimate:
        """Perform measurement update with Mahalanobis gating and Joseph-form update.

        Args:
            measurement: (u, v) measured pixel centroid.
            confidence: Perception confidence score in [0.0, 1.0].
            timestamp: Optional measurement timestamp.
            gimbal_pan_rate: Current camera pan rate in deg/s.
            gimbal_tilt_rate: Current camera tilt rate in deg/s.

        Returns:
            StateEstimate with updated state or rejected prediction.
        """
        t_start = time.perf_counter()

        if not self.is_initialized:
            # Auto-initialize on first measurement
            ts = timestamp if timestamp is not None else 0.0
            return self.initialize(measurement, ts)

        # Handle time step propagation if timestamp provided
        if timestamp is not None and timestamp > self._last_timestamp:
            dt = timestamp - self._last_timestamp
            self.predict(dt, gimbal_pan_rate, gimbal_tilt_rate)
            self._last_timestamp = timestamp
        elif timestamp is not None and timestamp <= self._last_timestamp:
            logger.warning(
                "Non-increasing timestamp received (curr=%s, prev=%s); skipping predict",
                timestamp,
                self._last_timestamp,
            )

        z = np.array([[measurement[0]], [measurement[1]]], dtype=np.float64)

        # Compute adaptive measurement noise R(confidence)
        R = build_measurement_noise_matrix(
            confidence=confidence,
            base_sigma_px=self._config.base_measurement_sigma_px,
        )

        # Compute innovation: y = z - H * x_pred, S = H P_pred H^T + R
        assert self._x_pred is not None and self._P_pred is not None
        inno = compute_innovation(z, self._x_pred, self._P_pred, self._H, R)
        self._last_innovation = inno

        # Mahalanobis gating test: d^2 <= gamma_gate
        # Adaptive innovation gating threshold:
        # High confidence detections (>= 0.60) under platform jitter/maneuvers allow up to 100.0 (d ~ 10 sigma)
        # to prevent spurious outlier rejections caused by platform motion or camera jitter steps.
        effective_gate_sq = self._config.gate_chi2_threshold
        if confidence >= 0.60:
            effective_gate_sq = max(effective_gate_sq, 100.0)

        is_initializing = (self._track_age <= 1)
        if not is_initializing and inno.mahalanobis_sq > effective_gate_sq:
            # If rejected for consecutive frames and a high-confidence beacon detection is present,
            # re-acquire so the estimator never gets permanently stuck on a stale trajectory
            if (
                self._consecutive_misses >= 1
                and confidence >= 0.60
            ):
                logger.info("Re-acquiring track after %d consecutive gate rejections", self._consecutive_misses)
                ts = timestamp if timestamp is not None else self._last_timestamp
                return self.initialize(measurement, ts)

            # Outlier rejected: retain predicted state, do NOT update state
            self._status = EstimatorStatus.REJECTED_MEASUREMENT
            self._x = self._x_pred.copy()
            self._P = self._P_pred.copy()
            self._consecutive_misses += 1
            self._track_age += 1

            t_end = time.perf_counter()
            return self._build_estimate(
                innovation=inno.residual,
                measurement_available=False,
                mahalanobis_dist=inno.mahalanobis_distance,
                proc_ms=(t_end - t_start) * 1000.0,
            )

        # Kalman Gain: K = P_pred * H^T * S^-1
        # Computed via numerically stable solve: S^T * K^T = H * P_pred^T
        S = inno.covariance
        H = self._H
        P_pred = self._P_pred
        x_pred = self._x_pred

        try:
            # Solve K = (P_pred * H^T) * S^-1 ==> K * S = P_pred * H^T
            # Using S.T * K.T = H * P_pred
            K = np.linalg.solve(S, H @ P_pred).T
        except np.linalg.LinAlgError:
            K = P_pred @ H.T @ np.linalg.pinv(S)

        # State Update: x = x_pred + K * y
        self._x = x_pred + (K @ inno.residual)

        # Covariance Update
        I_4 = np.eye(4, dtype=np.float64)
        I_KH = I_4 - (K @ H)

        if self._config.use_joseph_form:
            # Joseph stabilized covariance form:
            # P = (I - KH) * P_pred * (I - KH)^T + K * R * K^T
            P_new = (I_KH @ P_pred @ I_KH.T) + (K @ R @ K.T)
        else:
            # Standard form: P = (I - KH) * P_pred
            P_new = I_KH @ P_pred

        self._P = enforce_symmetry(P_new)
        self._status = EstimatorStatus.TRACKING
        self._consecutive_hits += 1
        self._consecutive_misses = 0
        self._track_age += 1

        t_end = time.perf_counter()
        return self._build_estimate(
            innovation=inno.residual,
            measurement_available=True,
            mahalanobis_dist=inno.mahalanobis_distance,
            proc_ms=(t_end - t_start) * 1000.0,
        )

    def update_missing(self, timestamp: Optional[float] = None) -> StateEstimate:
        """Handle a missing measurement (detected=False).

        Advances time and relies on kinematic prediction without measurement update.
        Expands covariance naturally via process noise Q.
        """
        t_start = time.perf_counter()

        if not self.is_initialized:
            # Cannot update uninitialized filter with no measurement
            self._status = EstimatorStatus.UNINITIALIZED
            t_end = time.perf_counter()
            return StateEstimate(
                estimated_x=320.0,
                estimated_y=240.0,
                estimated_vx=0.0,
                estimated_vy=0.0,
                covariance=np.zeros((4, 4), dtype=np.float64),
                innovation=None,
                predicted_x=320.0,
                predicted_y=240.0,
                filter_status=EstimatorStatus.UNINITIALIZED,
                timestamp=timestamp if timestamp is not None else 0.0,
                measurement_available=False,
                track_age=0,
                consecutive_measurements=0,
                consecutive_misses=0,
                processing_time_ms=(t_end - t_start) * 1000.0,
            )

        if timestamp is not None and timestamp > self._last_timestamp:
            dt = timestamp - self._last_timestamp
            self.predict(dt)
            self._last_timestamp = timestamp

        # Retain predicted state and covariance
        self._x = self._x_pred.copy() if self._x_pred is not None else self._x
        self._P = self._P_pred.copy() if self._P_pred is not None else self._P

        self._status = EstimatorStatus.PREDICTING
        self._consecutive_hits = 0
        self._consecutive_misses += 1
        self._track_age += 1

        t_end = time.perf_counter()
        return self._build_estimate(
            innovation=None,
            measurement_available=False,
            mahalanobis_dist=0.0,
            proc_ms=(t_end - t_start) * 1000.0,
        )

    def reset(self) -> None:
        """Completely reset the filter to uninitialized state.

        Clears state vector, covariance, timestamps, innovation, and counters.
        """
        self._x = None
        self._P = None
        self._x_pred = None
        self._P_pred = None
        self._status = EstimatorStatus.RESET
        self._last_timestamp = 0.0
        self._track_age = 0
        self._consecutive_hits = 0
        self._consecutive_misses = 0
        self._last_innovation = None

    def compute_nees(self, x_true: np.ndarray) -> float:
        """Compute Normalized Estimation Error Squared (NEES) against ground truth x_true for offline evaluation ONLY."""
        if self._x is None or self._P is None:
            return 0.0
        return compute_nees_evaluation(x_true, self._x, self._P)

    def _build_estimate(
        self,
        innovation: Optional[np.ndarray],
        measurement_available: bool,
        mahalanobis_dist: float,
        proc_ms: float,
    ) -> StateEstimate:
        """Helper to assemble immutable StateEstimate with EstimatorHealth."""
        assert self._x is not None and self._P is not None
        pred_x = float(self._x_pred[0, 0]) if self._x_pred is not None else float(self._x[0, 0])
        pred_y = float(self._x_pred[1, 0]) if self._x_pred is not None else float(self._x[1, 0])
        pred_vx = float(self._x_pred[2, 0]) if self._x_pred is not None else float(self._x[2, 0])
        pred_vy = float(self._x_pred[3, 0]) if self._x_pred is not None else float(self._x[3, 0])

        nis = float(mahalanobis_dist ** 2)
        pos_sigma = float(np.sqrt(max(0.0, self._P[0, 0] + self._P[1, 1])))
        vel_sigma = float(np.sqrt(max(0.0, self._P[2, 2] + self._P[3, 3])))

        # Compute composite estimator health score [0.0, 1.0]
        gate_thresh = self._config.gate_chi2_threshold
        inno_health = float(np.clip(math.exp(-0.5 * min(nis, 50.0) / gate_thresh), 0.0, 1.0)) if measurement_available else 0.5
        pos_health = float(np.clip(1.0 / (1.0 + pos_sigma / 20.0), 0.0, 1.0))
        track_health = float(0.5 * inno_health + 0.5 * pos_health)

        health = EstimatorHealth(
            track_health=track_health,
            position_sigma=pos_sigma,
            velocity_sigma=vel_sigma,
            innovation_health=inno_health,
            model_probabilities=(1.0, 0.0, 0.0),
            measurement_accepted=measurement_available,
            prediction_age_frames=self._consecutive_misses,
            nis=nis,
            nees_eval=None,
            mahalanobis_distance=float(mahalanobis_dist),
            mahalanobis_threshold=float(gate_thresh),
        )

        return StateEstimate(
            estimated_x=float(self._x[0, 0]),
            estimated_y=float(self._x[1, 0]),
            estimated_vx=float(self._x[2, 0]),
            estimated_vy=float(self._x[3, 0]),
            covariance=self._P.copy(),
            innovation=innovation.copy() if innovation is not None else None,
            predicted_x=pred_x,
            predicted_y=pred_y,
            filter_status=self._status,
            timestamp=self._last_timestamp,
            measurement_available=measurement_available,
            track_age=self._track_age,
            consecutive_measurements=self._consecutive_hits,
            consecutive_misses=self._consecutive_misses,
            mahalanobis_distance=float(mahalanobis_dist),
            association_quality=inno_health if measurement_available else 0.0,
            processing_time_ms=float(proc_ms),
            predicted_vx=pred_vx,
            predicted_vy=pred_vy,
            nis=nis,
            nees_eval=None,
            estimator_health=health,
        )


def compute_nees_evaluation(x_true: np.ndarray, x_est: np.ndarray, P_est: np.ndarray) -> float:
    """Compute Normalized Estimation Error Squared (NEES) for offline evaluation ONLY.

    NEES = (x_true - x_est)^T * P_est^-1 * (x_true - x_est)
    STRICT INVARIANT: Evaluation-only metric. Does NOT influence filter updates or control laws.
    """
    err = (x_true.ravel() - x_est.ravel()).reshape(-1, 1)
    try:
        inv_P = np.linalg.inv(P_est)
        nees = float((err.T @ inv_P @ err)[0, 0])
    except np.linalg.LinAlgError:
        inv_P = np.linalg.pinv(P_est)
        nees = float((err.T @ inv_P @ err)[0, 0])
    return max(0.0, nees)
