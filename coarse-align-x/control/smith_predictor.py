"""
HORIZON Smith Predictor Latency & Transport Lag Compensator
===========================================================
Internal Plant Model Smith Predictor for compensating camera exposure,
serial transmission, image processing, and actuator transport lag.

Physical Model:
  Rate command u(t) -> Rate-limited & Acceleration-limited 1st-order motor response -> Continuous position integration.
  y_hat_undelayed(t) = G_p(s) * u(t)
  y_hat_delayed(t) = G_p(s) * u(t - tau)
  e_pred(t) = e_measured(t) - (y_hat_undelayed(t) - y_hat_delayed(t))

Strict Invariant: Zero access to true target position or ground-truth state.
"""

from __future__ import annotations

import collections
from dataclasses import dataclass
from typing import Deque, Tuple, Optional
import numpy as np


@dataclass
class SmithPredictorConfig:
    """Configuration for the Smith Predictor latency compensator."""
    latency_seconds: float = 0.033  # Nominal transport lag [s]
    plant_gain: float = 1.0         # Nominal open-loop plant gain
    rate_limit_deg_s: float = 20.0  # Matches CameraGimbal rate limit [deg/s]
    accel_limit_deg_s2: float = 300.0  # Matches CameraGimbal accel limit [deg/s^2]
    max_history_seconds: float = 0.50  # Up to 500 ms historical state buffer
    buffer_dt_s: float = 0.01        # Timestep interval for historical state buffer


class SmithPredictor:
    """Smith Predictor Latency Compensator for dual-axis pan/tilt gimbal control."""

    def __init__(self, config: SmithPredictorConfig | None = None) -> None:
        self.config = config or SmithPredictorConfig()

        # Plant internal position and velocity states [pan, tilt]
        self._undelayed_pan = 0.0
        self._undelayed_tilt = 0.0
        self._actual_rate_pan = 0.0
        self._actual_rate_tilt = 0.0
        self._sim_time = 0.0

        # Ring buffer storing (timestamp, undelayed_pan, undelayed_tilt)
        self._history: Deque[Tuple[float, float, float]] = collections.deque(maxlen=200)
        self._history.append((0.0, 0.0, 0.0))

    def reset(self) -> None:
        """Reset internal plant model states and history buffer."""
        self._undelayed_pan = 0.0
        self._undelayed_tilt = 0.0
        self._actual_rate_pan = 0.0
        self._actual_rate_tilt = 0.0
        self._sim_time = 0.0
        self._history.clear()
        self._history.append((0.0, 0.0, 0.0))

    def predict_error(
        self,
        measured_pan_error_deg: float,
        measured_tilt_error_deg: float,
        cmd_pan_rate_deg_s: float,
        cmd_tilt_rate_deg_s: float,
        dt: float,
        latency_s: Optional[float] = None,
    ) -> Tuple[float, float]:
        """Compute delay-free predicted pointing errors using the internal plant model.

        Args:
            measured_pan_error_deg: Measured pan error from perception/estimator [deg].
            measured_tilt_error_deg: Measured tilt error from perception/estimator [deg].
            cmd_pan_rate_deg_s: Latest commanded pan rate [deg/s].
            cmd_tilt_rate_deg_s: Latest commanded tilt rate [deg/s].
            dt: Sample time step [s].
            latency_s: Optional dynamic transport latency [s]. If None, uses config.

        Returns:
            Tuple[predicted_pan_error_deg, predicted_tilt_error_deg]
        """
        if dt <= 0.0:
            return float(measured_pan_error_deg), float(measured_tilt_error_deg)

        self._sim_time += dt

        # 1. Physical Motor Rate Dynamics (Rate and Acceleration Limited)
        target_pan = float(np.clip(cmd_pan_rate_deg_s * self.config.plant_gain, -self.config.rate_limit_deg_s, self.config.rate_limit_deg_s))
        target_tilt = float(np.clip(cmd_tilt_rate_deg_s * self.config.plant_gain, -self.config.rate_limit_deg_s, self.config.rate_limit_deg_s))

        max_delta = self.config.accel_limit_deg_s2 * dt
        self._actual_rate_pan += float(np.clip(target_pan - self._actual_rate_pan, -max_delta, max_delta))
        self._actual_rate_tilt += float(np.clip(target_tilt - self._actual_rate_tilt, -max_delta, max_delta))

        # Clamp actual rates to physical limits
        self._actual_rate_pan = float(np.clip(self._actual_rate_pan, -self.config.rate_limit_deg_s, self.config.rate_limit_deg_s))
        self._actual_rate_tilt = float(np.clip(self._actual_rate_tilt, -self.config.rate_limit_deg_s, self.config.rate_limit_deg_s))

        # 2. Continuous Position Integration (No Artificial Leaky Decay)
        self._undelayed_pan += self._actual_rate_pan * dt
        self._undelayed_tilt += self._actual_rate_tilt * dt

        # Append state to history buffer
        self._history.append((self._sim_time, self._undelayed_pan, self._undelayed_tilt))

        # 3. Retrieve Delayed Prediction with Continuous Time Interpolation
        tau = latency_s if (latency_s is not None and latency_s > 0.0) else self.config.latency_seconds
        t_delayed = self._sim_time - tau

        delayed_pan, delayed_tilt = self._interpolate_delayed(t_delayed)

        # 4. Smith Predictor Innovation:
        # e_pred = e_measured - (y_undelayed - y_delayed)
        pred_pan_err = measured_pan_error_deg - (self._undelayed_pan - delayed_pan)
        pred_tilt_err = measured_tilt_error_deg - (self._undelayed_tilt - delayed_tilt)

        return float(pred_pan_err), float(pred_tilt_err)

    def _interpolate_delayed(self, t_target: float) -> Tuple[float, float]:
        """Interpolate undelayed position at t_target from history buffer."""
        if not self._history:
            return 0.0, 0.0

        if t_target <= self._history[0][0]:
            return self._history[0][1], self._history[0][2]

        if t_target >= self._history[-1][0]:
            return self._history[-1][1], self._history[-1][2]

        # Scan history for surrounding bracket [t_prev, t_curr]
        for i in range(len(self._history) - 1, 0, -1):
            t_curr, p_curr, t_c_tilt = self._history[i]
            t_prev, p_prev, t_p_tilt = self._history[i - 1]
            if t_prev <= t_target <= t_curr:
                denom = t_curr - t_prev
                if denom <= 1e-9:
                    return p_curr, t_c_tilt
                alpha = (t_target - t_prev) / denom
                p_interp = p_prev + alpha * (p_curr - p_prev)
                t_interp = t_p_tilt + alpha * (t_c_tilt - t_p_tilt)
                return float(p_interp), float(t_interp)

        return self._history[0][1], self._history[0][2]
