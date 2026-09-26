"""IMM model definitions for Phase 14.

The existing :class:`KalmanEstimator` (CV model) is reused unchanged – it
provides the standard 4‑state constant‑velocity filter. For the additional
models we instantiate separate ``KalmanEstimator`` objects with custom
configuration objects that define the required process‑noise matrix ``Q``
and transition matrix ``F``.

Three models are defined:

* **CVModel** – constant velocity (4‑state) – re‑uses the existing
  ``KalmanEstimator``.
* **CAModel** – constant acceleration (6‑state) – adds acceleration
  states ``ax`` and ``ay``. The state vector is ``[x, y, vx, vy, ax, ay]``.
* **HMModel** – high‑maneuver CV (4‑state) – identical dynamics to CV but
  with an elevated process‑noise covariance to allow rapid response to
  sudden direction changes.

All models conform to a tiny ``BaseModel`` protocol exposing the methods
required by the IMM framework:

```python
    predict(dt: float) -> None
    update(z: np.ndarray, R: np.ndarray) -> None
    state() -> np.ndarray          # 4‑element fused state (position+velocity)
    covariance() -> np.ndarray      # 4×4 covariance (projected for fusion)
    innovation() -> np.ndarray | None
    likelihood() -> float | None
```

The ``CAModel`` internally maintains a 6‑state filter but provides a
projected 4‑state view for the IMM fusion step (by dropping the acceleration
components). The ``HMModel`` simply scales the CV ``Q`` matrix.
"""

from __future__ import annotations

import numpy as np
from dataclasses import dataclass
from typing import Optional

from tracking.estimation.kalman import TargetKalmanFilter, KalmanFilterConfig
from tracking.estimation.state import StateEstimate


@dataclass
class BaseModel:
    """Minimal interface required by the IMM framework.

    Sub‑classes must implement ``predict``, ``update``, ``state``,
    ``covariance``, ``innovation`` and ``likelihood``.  The ``state`` and
    ``covariance`` methods return the *projected* 4‑state representation
    required for fusion (position + velocity only).
    """

    def predict(self, dt: float) -> None:  # pragma: no cover – abstract
        raise NotImplementedError

    def update(self, z: np.ndarray, R: np.ndarray) -> None:  # pragma: no cover – abstract
        raise NotImplementedError

    def state(self) -> np.ndarray:  # pragma: no cover – abstract
        raise NotImplementedError

    def covariance(self) -> np.ndarray:  # pragma: no cover – abstract
        raise NotImplementedError

    def innovation(self) -> Optional[np.ndarray]:  # pragma: no cover – abstract
        raise NotImplementedError

    def likelihood(self) -> Optional[float]:  # pragma: no cover – abstract
        raise NotImplementedError

    def reset(self) -> None:  # pragma: no cover – abstract
        raise NotImplementedError


class CVModel(BaseModel):
    """Constant‑velocity model – thin wrapper around the existing CV Kalman filter.

    The underlying ``TargetKalmanFilter`` is instantiated with the default
    configuration (or a ``KalmanFilterConfig`` supplied via ``config``).
    """

    def __init__(self, config: Optional[KalmanFilterConfig] = None):
        self.kf = TargetKalmanFilter(config)
        self._last_innovation: Optional[np.ndarray] = None
        self._last_likelihood: Optional[float] = None

    def predict(self, dt: float) -> None:
        self.kf.predict(dt, 0.0, 0.0)

    def update(self, z: np.ndarray, R: np.ndarray) -> None:
        # The existing Kalman filter expects a measurement tuple (x, y).
        # ``z`` is a shape (2,) array.
        self.kf.update(z, R)
        # Store the innovation for likelihood computation.
        self._last_innovation = self.kf._last_innovation.residual if self.kf._last_innovation else None
        # Compute likelihood using the Gaussian pdf (log domain handled later).
        if self._last_innovation is not None:
            S = self.kf._H @ self.kf._P_pred @ self.kf._H.T + R
            try:
                inv_S = np.linalg.inv(S)
                det_S = np.linalg.det(S)
                exponent = -0.5 * self._last_innovation.T @ inv_S @ self._last_innovation
                self._last_likelihood = float(
                    (2 * np.pi) ** (-self._last_innovation.size / 2) * det_S ** (-0.5) * np.exp(exponent)
                )
            except np.linalg.LinAlgError:
                self._last_likelihood = None
        else:
            self._last_likelihood = None

    def state(self) -> np.ndarray:
        # Return the 4‑element position/velocity state.
        if self.kf.state_vector is None:
            raise RuntimeError("CVModel state not initialized")
        return self.kf.state_vector.squeeze()

    def covariance(self) -> np.ndarray:
        if self.kf.covariance_matrix is None:
            raise RuntimeError("CVModel covariance not initialized")
        return self.kf.covariance_matrix

    def innovation(self) -> Optional[np.ndarray]:
        return self._last_innovation

    def likelihood(self) -> Optional[float]:
        return self._last_likelihood

    def reset(self) -> None:
        self.kf.reset()
        self._last_innovation = None
        self._last_likelihood = None


class CAModel(BaseModel):
    """Constant‑acceleration model (6‑state).

    This model builds its own transition and process‑noise matrices for a
    6‑state state vector ``[x, y, vx, vy, ax, ay]``. It re‑uses the generic
    ``TargetKalmanFilter`` code path but supplies a custom ``KalmanFilterConfig``
    that forces the correct dimensionality.
    """

    def __init__(self, q_ca: float = 5.0):
        # Build a custom config for the CA model.
        cfg = KalmanFilterConfig(
            accel_noise_sigma=q_ca,  # Jerk noise used as proxy for acceleration noise
            process_model_type="ca",  # Custom flag – the filter code will ignore it; we handle F/Q manually.
        )
        self.kf = TargetKalmanFilter(cfg)
        self._last_innovation: Optional[np.ndarray] = None
        self._last_likelihood: Optional[float] = None

    def _build_F_Q(self, dt: float) -> tuple[np.ndarray, np.ndarray]:
        # Transition matrix for constant acceleration (6×6).
        F = np.array(
            [
                [1, 0, dt, 0, 0.5 * dt ** 2, 0],
                [0, 1, 0, dt, 0, 0.5 * dt ** 2],
                [0, 0, 1, 0, dt, 0],
                [0, 0, 0, 1, 0, dt],
                [0, 0, 0, 0, 1, 0],
                [0, 0, 0, 0, 0, 1],
            ]
        )
        # Process‑noise (white jerk) – scalar q_ca scaled by dt^5 etc.
        q = self.kf.config.accel_noise_sigma ** 2
        Q = q * np.array(
            [
                [dt ** 5 / 20, 0, dt ** 4 / 8, 0, dt ** 3 / 6, 0],
                [0, dt ** 5 / 20, 0, dt ** 4 / 8, 0, dt ** 3 / 6],
                [dt ** 4 / 8, 0, dt ** 3 / 3, 0, dt ** 2 / 2, 0],
                [0, dt ** 4 / 8, 0, dt ** 3 / 3, 0, dt ** 2 / 2],
                [dt ** 3 / 6, 0, dt ** 2 / 2, 0, dt, 0],
                [0, dt ** 3 / 6, 0, dt ** 2 / 2, 0, dt],
            ]
        )
        return F, Q

    def predict(self, dt: float) -> None:
        # Manually propagate the 6‑state filter.
        F, Q = self._build_F_Q(dt)
        # Predict step using same algebra as in the Kalman filter.
        x = self.kf.state_vector.squeeze()
        P = self.kf.covariance_matrix
        x_pred = F @ x
        P_pred = F @ P @ F.T + Q
        self.kf._x_pred = x_pred[:, None]  # store as column vector for consistency
        self.kf._P_pred = P_pred
        self.kf._x = x_pred[:, None]
        self.kf._P = P_pred

    def update(self, z: np.ndarray, R: np.ndarray) -> None:
        # Measurement matrix H extracts position only (2×6).
        H = np.array([[1, 0, 0, 0, 0, 0], [0, 1, 0, 0, 0, 0]])
        x_pred = self.kf._x_pred.squeeze()
        P_pred = self.kf._P_pred
        # Innovation
        y = z - H @ x_pred
        S = H @ P_pred @ H.T + R
        try:
            K = P_pred @ H.T @ np.linalg.inv(S)
        except np.linalg.LinAlgError:
            K = np.zeros((6, 2))
        x_upd = x_pred + K @ y
        I_KH = np.eye(6) - K @ H
        P_upd = I_KH @ P_pred @ I_KH.T + K @ R @ K.T  # Joseph form
        self.kf._x = x_upd[:, None]
        self.kf._P = P_upd
        # Store innovation and likelihood.
        self._last_innovation = y
        try:
            inv_S = np.linalg.inv(S)
            det_S = np.linalg.det(S)
            exponent = -0.5 * y.T @ inv_S @ y
            self._last_likelihood = float(
                (2 * np.pi) ** (-y.size / 2) * det_S ** (-0.5) * np.exp(exponent)
            )
        except np.linalg.LinAlgError:
            self._last_likelihood = None

    def state(self) -> np.ndarray:
        # Project 6‑state to 4‑state (drop acceleration).
        full_state = self.kf.state_vector.squeeze()
        return full_state[:4]

    def covariance(self) -> np.ndarray:
        # Project covariance: extract top‑left 4×4 block.
        full_P = self.kf.covariance_matrix
        return full_P[:4, :4]

    def innovation(self) -> Optional[np.ndarray]:
        return self._last_innovation

    def likelihood(self) -> Optional[float]:
        return self._last_likelihood

    def reset(self) -> None:
        self.kf.reset()
        self._last_innovation = None
        self._last_likelihood = None


class HMModel(BaseModel):
    """High‑maneuver CV model – same dynamics as CV but with an elevated Q.

    The implementation simply scales the ``Q`` matrix of a wrapped CV model.
    """

    def __init__(self, q_hm: float = 10.0):
        # Start from a default CV config and then scale its Q.
        base_cfg = KalmanFilterConfig()
        self.kf = TargetKalmanFilter(base_cfg)
        self.q_scale = q_hm / base_cfg.accel_noise_sigma  # ratio to default
        self._last_innovation: Optional[np.ndarray] = None
        self._last_likelihood: Optional[float] = None

    def predict(self, dt: float) -> None:
        # Use the standard CV prediction but inflate Q.
        # Build the standard F and Q.
        F = np.array(
            [[1, 0, dt, 0],
             [0, 1, 0, dt],
             [0, 0, 1, 0],
             [0, 0, 0, 1]],
        )
        q = self.kf.config.accel_noise_sigma ** 2 * self.q_scale
        Q = q * np.array(
            [
                [dt ** 3 / 3, 0, dt ** 2 / 2, 0],
                [0, dt ** 3 / 3, 0, dt ** 2 / 2],
                [dt ** 2 / 2, 0, dt, 0],
                [0, dt ** 2 / 2, 0, dt],
            ]
        )
        x = self.kf.state_vector.squeeze()
        P = self.kf.covariance_matrix
        x_pred = F @ x
        P_pred = F @ P @ F.T + Q
        self.kf._x_pred = x_pred[:, None]
        self.kf._P_pred = P_pred
        self.kf._x = x_pred[:, None]
        self.kf._P = P_pred

    def update(self, z: np.ndarray, R: np.ndarray) -> None:
        # Standard CV measurement update (H 2×4).
        H = np.array([[1, 0, 0, 0], [0, 1, 0, 0]])
        x_pred = self.kf._x_pred.squeeze()
        P_pred = self.kf._P_pred
        y = z - H @ x_pred
        S = H @ P_pred @ H.T + R
        try:
            K = P_pred @ H.T @ np.linalg.inv(S)
        except np.linalg.LinAlgError:
            K = np.zeros((4, 2))
        x_upd = x_pred + K @ y
        I_KH = np.eye(4) - K @ H
        P_upd = I_KH @ P_pred @ I_KH.T + K @ R @ K.T
        self.kf._x = x_upd[:, None]
        self.kf._P = P_upd
        self._last_innovation = y
        try:
            inv_S = np.linalg.inv(S)
            det_S = np.linalg.det(S)
            exponent = -0.5 * y.T @ inv_S @ y
            self._last_likelihood = float(
                (2 * np.pi) ** (-y.size / 2) * det_S ** (-0.5) * np.exp(exponent)
            )
        except np.linalg.LinAlgError:
            self._last_likelihood = None

    def state(self) -> np.ndarray:
        return self.kf.state_vector.squeeze()

    def covariance(self) -> np.ndarray:
        return self.kf.covariance_matrix

    def innovation(self) -> Optional[np.ndarray]:
        return self._last_innovation

    def likelihood(self) -> Optional[float]:
        return self._last_likelihood

    def reset(self) -> None:
        self.kf.reset()
        self._last_innovation = None
        self._last_likelihood = None


class CTModel(BaseModel):
    """Coordinated Turn (CT) non-linear model (5-state: [x, y, V, psi, omega]).

    Model state:
      x, y: 2D position [px]
      V: linear speed [px/s]
      psi: heading angle [rad]
      omega: turn rate [rad/s]
    """

    def __init__(self, process_noise_std: float = 1.0):
        self.q_std = process_noise_std
        self._x = np.zeros(5, dtype=np.float64)
        self._P = np.eye(5, dtype=np.float64) * 10.0
        self._last_innovation: Optional[np.ndarray] = None
        self._last_likelihood: Optional[float] = None
        self._initialized = False

    def predict(self, dt: float) -> None:
        if not self._initialized:
            return
        x, y, V, psi, w = self._x
        if abs(w) > 1e-5:
            x_next = x + (V / w) * (np.sin(psi + w * dt) - np.sin(psi))
            y_next = y - (V / w) * (np.cos(psi + w * dt) - np.cos(psi))
            F = np.array([
                [1, 0, (np.sin(psi + w * dt) - np.sin(psi)) / w, (V / w) * (np.cos(psi + w * dt) - np.cos(psi)), (V * dt * np.cos(psi + w * dt)) / w - (V * (np.sin(psi + w * dt) - np.sin(psi))) / (w ** 2)],
                [0, 1, (-np.cos(psi + w * dt) + np.cos(psi)) / w, (V / w) * (np.sin(psi + w * dt) - np.sin(psi)), (V * dt * np.sin(psi + w * dt)) / w - (V * (-np.cos(psi + w * dt) + np.cos(psi))) / (w ** 2)],
                [0, 0, 1, 0, 0],
                [0, 0, 0, 1, dt],
                [0, 0, 0, 0, 1],
            ])
        else:
            x_next = x + V * np.cos(psi) * dt
            y_next = y + V * np.sin(psi) * dt
            F = np.array([
                [1, 0, np.cos(psi) * dt, -V * np.sin(psi) * dt, 0],
                [0, 1, np.sin(psi) * dt, V * np.cos(psi) * dt, 0],
                [0, 0, 1, 0, 0],
                [0, 0, 0, 1, dt],
                [0, 0, 0, 0, 1],
            ])
        psi_next = (psi + w * dt + np.pi) % (2 * np.pi) - np.pi
        self._x = np.array([x_next, y_next, V, psi_next, w], dtype=np.float64)

        Q = np.diag([0.1 * dt**2, 0.1 * dt**2, (self.q_std * dt)**2, (0.1 * dt)**2, (0.05 * dt)**2])
        self._P = F @ self._P @ F.T + Q

    def update(self, z: np.ndarray, R: np.ndarray) -> None:
        if not self._initialized:
            # Auto initialize
            self._x = np.array([z[0], z[1], 0.0, 0.0, 0.0], dtype=np.float64)
            self._initialized = True
            return

        H = np.array([[1, 0, 0, 0, 0], [0, 1, 0, 0, 0]], dtype=np.float64)
        y = z - H @ self._x
        S = H @ self._P @ H.T + R
        try:
            inv_S = np.linalg.inv(S)
            K = self._P @ H.T @ inv_S
            det_S = max(1e-12, float(np.linalg.det(S)))
            exponent = -0.5 * float(y.T @ inv_S @ y)
            self._last_likelihood = float((2 * np.pi) ** (-1.0) * (det_S ** -0.5) * np.exp(exponent))
        except np.linalg.LinAlgError:
            K = np.zeros((5, 2))
            self._last_likelihood = None

        self._x = self._x + K @ y
        I_KH = np.eye(5) - K @ H
        self._P = I_KH @ self._P @ I_KH.T + K @ R @ K.T
        self._last_innovation = y

    def state(self) -> np.ndarray:
        # Convert polar state [x, y, V, psi, omega] to Cartesian 4-state [x, y, vx, vy]
        x, y, V, psi, _ = self._x
        vx = V * np.cos(psi)
        vy = V * np.sin(psi)
        return np.array([x, y, vx, vy], dtype=np.float64)

    def covariance(self) -> np.ndarray:
        # Approximate 4x4 Cartesian covariance
        P_cart = np.zeros((4, 4), dtype=np.float64)
        P_cart[0:2, 0:2] = self._P[0:2, 0:2]
        P_cart[2, 2] = max(10.0, float(self._P[2, 2]))
        P_cart[3, 3] = max(10.0, float(self._P[2, 2]))
        return P_cart

    def innovation(self) -> Optional[np.ndarray]:
        return self._last_innovation

    def likelihood(self) -> Optional[float]:
        return self._last_likelihood

    def reset(self) -> None:
        self._x = np.zeros(5, dtype=np.float64)
        self._P = np.eye(5, dtype=np.float64) * 10.0
        self._initialized = False
        self._last_innovation = None
        self._last_likelihood = None


