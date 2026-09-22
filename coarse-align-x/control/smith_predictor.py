"""
HORIZON Smith Predictor Latency & Transport Lag Compensator
===========================================================
Internal Plant Model Smith Predictor for compensating camera exposure,
serial transmission, image processing, and actuator transport lag.

Equations:
  y_hat_undelayed(t) = G_p(s) * u(t)
  y_hat_delayed(t) = G_p(s) * u(t - tau)
  e_pred(t) = e_measured(t) + (y_hat_undelayed(t) - y_hat_delayed(t))

Strict Invariant: Zero access to true target position or ground-truth state.
"""

from __future__ import annotations

import collections
from dataclasses import dataclass
from typing import Deque, Tuple
import numpy as np


@dataclass
class SmithPredictorConfig:
    """Configuration for the Smith Predictor latency compensator."""
    latency_seconds: float = 0.05  # 50 ms default transport lag (exposure + processing + bus)
    plant_gain: float = 1.0         # Nominal open-loop plant gain
    time_constant_s: float = 0.02   # 1st-order motor time constant [s]
    buffer_dt_s: float = 0.005      # 200 Hz internal state ring-buffer step size


class SmithPredictor:
    """Smith Predictor Latency Compensator for dual-axis pan/tilt gimbal control."""

    def __init__(self, config: SmithPredictorConfig | None = None) -> None:
        self.config = config or SmithPredictorConfig()

        # Plant internal state estimates [pan, tilt]
        self._undelayed_pan = 0.0
        self._undelayed_tilt = 0.0

        # Ring buffer for delayed command history
        max_samples = max(2, int(np.ceil(self.config.latency_seconds / self.config.buffer_dt_s)))
        self._history: Deque[Tuple[float, float]] = collections.deque(maxlen=max_samples)
        for _ in range(max_samples):
            self._history.append((0.0, 0.0))

    def reset(self) -> None:
        """Reset internal plant model states and history buffer."""
        self._undelayed_pan = 0.0
        self._undelayed_tilt = 0.0
        max_samples = self._history.maxlen or 2
        self._history.clear()
        for _ in range(max_samples):
            self._history.append((0.0, 0.0))

    def predict_error(
        self,
        measured_pan_error_deg: float,
        measured_tilt_error_deg: float,
        cmd_pan_rate_deg_s: float,
        cmd_tilt_rate_deg_s: float,
        dt: float,
    ) -> Tuple[float, float]:
        """Compute delay-free predicted pointing errors using the internal plant model.

        Args:
            measured_pan_error_deg: Measured pan error from perception/estimator [deg].
            measured_tilt_error_deg: Measured tilt error from perception/estimator [deg].
            cmd_pan_rate_deg_s: Latest commanded pan rate [deg/s].
            cmd_tilt_rate_deg_s: Latest commanded tilt rate [deg/s].
            dt: Sample time step [s].

        Returns:
            Tuple[predicted_pan_error_deg, predicted_tilt_error_deg]
        """
        if dt <= 0.0:
            return measured_pan_error_deg, measured_tilt_error_deg

        # 1-sigma 1st order motor response update
        alpha = min(1.0, dt / max(1e-4, self.config.time_constant_s))
        self._undelayed_pan += alpha * (self.config.plant_gain * cmd_pan_rate_deg_s * dt - self._undelayed_pan * alpha)
        self._undelayed_tilt += alpha * (self.config.plant_gain * cmd_tilt_rate_deg_s * dt - self._undelayed_tilt * alpha)

        # Append to ring buffer
        self._history.append((self._undelayed_pan, self._undelayed_tilt))

        # Retrieve delayed prediction from history tail
        delayed_pan, delayed_tilt = self._history[0]

        # Smith predictor innovation: e_pred = e_measured - (y_undelayed - y_delayed)
        # Negative feedback: camera motion reduces tracking error
        pred_pan_err = measured_pan_error_deg - (self._undelayed_pan - delayed_pan)
        pred_tilt_err = measured_tilt_error_deg - (self._undelayed_tilt - delayed_tilt)

        return float(pred_pan_err), float(pred_tilt_err)
