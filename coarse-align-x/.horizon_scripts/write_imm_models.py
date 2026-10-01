"""
Helper script: atomically rewrites tracking/estimation/imm_models.py.

Fixes applied:
  1. CAModel.predict() crash on None state before initialization.
  2. CVModel.update() calling kf.update(z, R) with wrong API signature
     (R matrix was silently treated as scalar 'confidence').
  3. CAModel mixing 4D / 6D state into TargetKalmanFilter internals
     causing guaranteed shape mismatches.
  4. HMModel.predict() crash on None state before initialization.
  5. np.linalg.inv(S) in all models replaced by analytic 2x2 inversion.
  6. Unclipped Gaussian exponents causing underflow in likelihoods.
"""

import os

TARGET = os.path.join(
    os.path.dirname(__file__), "..", "tracking", "estimation", "imm_models.py"
)

CONTENT = '''\
"""IMM model definitions for Phase 14.

Four motion models with a unified BaseModel protocol:

* **CVModel**  – constant velocity (4-state): wraps TargetKalmanFilter but
  performs the measurement update manually to accept an explicit 2x2 R matrix.
* **CAModel**  – constant acceleration (6-state [x,y,vx,vy,ax,ay]): fully
  self-contained to avoid shape conflicts with the 4-state TargetKalmanFilter.
  Projects to 4-state for IMM fusion.
* **HMModel**  – high-maneuver CV (4-state): same dynamics as CV but with
  elevated process-noise Q. Self-contained for initialization safety.
* **CTModel**  – Coordinated-Turn EKF (5-state [x,y,V,psi,omega]): non-linear
  prediction via exact CT kinematics + linearised Jacobian. Converts to
  Cartesian 4-state for fusion.

Numerical discipline:
  - All 2x2 S-matrix inversions use analytic closed-form (_inv2x2_analytic).
  - Fallback to pseudoinverse when det < 1e-12.
  - Gaussian likelihoods clip Mahalanobis distance at 45.0 to prevent underflow.
  - Joseph-form covariance updates for all models.

Strict invariant: no access to ground-truth target state.
"""

from __future__ import annotations

import math
import numpy as np
from dataclasses import dataclass
from typing import Optional

from tracking.estimation.kalman import TargetKalmanFilter, KalmanFilterConfig


# ---------------------------------------------------------------------------
# Analytic 2x2 inversion helper (shared by all models)
# ---------------------------------------------------------------------------

def _inv2x2_analytic(S: np.ndarray):
    """Return (inv_S, det_S) for a 2x2 symmetric matrix.

    Uses the analytic formula for speed.  Falls back to pseudoinverse when
    the determinant is below 1e-12 (near-singular innovation covariance).
    """
    S_sym = 0.5 * (S + S.T)
    det_S = float(S_sym[0, 0] * S_sym[1, 1] - S_sym[0, 1] * S_sym[1, 0])
    if abs(det_S) > 1e-12:
        inv_det = 1.0 / det_S
        inv_S = np.array(
            [[S_sym[1, 1] * inv_det, -S_sym[0, 1] * inv_det],
             [-S_sym[1, 0] * inv_det, S_sym[0, 0] * inv_det]],
            dtype=np.float64,
        )
    else:
        inv_S = np.linalg.pinv(S_sym)
    return inv_S, det_S


def _gaussian_likelihood_2d(y: np.ndarray, inv_S: np.ndarray, det_S: float) -> float:
    """Numerically stable 2-D Gaussian likelihood with clipped exponent."""
    d2 = max(0.0, min(float((y.T @ inv_S @ y).item()), 45.0))
    det_safe = max(1e-12, abs(det_S))
    return float((2.0 * math.pi) ** (-1.0) * (det_safe ** -0.5) * math.exp(-0.5 * d2))


# ---------------------------------------------------------------------------
# BaseModel protocol
# ---------------------------------------------------------------------------

@dataclass
class BaseModel:
    """Minimal interface required by the IMM framework."""

    def predict(self, dt: float) -> None:
        raise NotImplementedError

    def update(self, z: np.ndarray, R: np.ndarray) -> None:
        raise NotImplementedError

    def state(self) -> np.ndarray:
        raise NotImplementedError

    def covariance(self) -> np.ndarray:
        raise NotImplementedError

    def innovation(self) -> Optional[np.ndarray]:
        raise NotImplementedError

    def likelihood(self) -> Optional[float]:
        raise NotImplementedError

    def reset(self) -> None:
        raise NotImplementedError


# ---------------------------------------------------------------------------
# CVModel: Constant-Velocity (4-state)
# ---------------------------------------------------------------------------

class CVModel(BaseModel):
    """Constant-velocity model wrapping TargetKalmanFilter.

    The KF is used for state storage and predict().  The update step is
    performed manually so that an explicit 2x2 R matrix is honoured (the
    base KF only supports a scalar confidence level).
    """

    _H = np.array([[1., 0., 0., 0.],
                   [0., 1., 0., 0.]], dtype=np.float64)

    def __init__(self, config: Optional[KalmanFilterConfig] = None):
        self.kf = TargetKalmanFilter(config)
        self._last_innovation: Optional[np.ndarray] = None
        self._last_likelihood: Optional[float] = None

    def predict(self, dt: float) -> None:
        if not self.kf.is_initialized:
            return
        self.kf.predict(dt, 0.0, 0.0)

    def update(self, z: np.ndarray, R: np.ndarray) -> None:
        z_arr = np.asarray(z, dtype=np.float64).ravel()
        if not self.kf.is_initialized:
            self.kf.initialize((float(z_arr[0]), float(z_arr[1])), timestamp=0.0)
            self._last_innovation = np.zeros((2, 1), dtype=np.float64)
            self._last_likelihood = None
            return
        # Fall back to current state when predict() has not been called yet.
        x_pred = self.kf._x_pred if self.kf._x_pred is not None else self.kf._x
        P_pred = self.kf._P_pred if self.kf._P_pred is not None else self.kf._P
        if x_pred is None or P_pred is None:
            self.kf.initialize((float(z_arr[0]), float(z_arr[1])), timestamp=0.0)
            return
        H = self._H
        y = z_arr.reshape(2, 1) - H @ x_pred
        S = H @ P_pred @ H.T + R
        inv_S, det_S = _inv2x2_analytic(S)
        K = P_pred @ H.T @ inv_S
        # Joseph-form update for numerical stability.
        self.kf._x = x_pred + K @ y
        I_KH = np.eye(4, dtype=np.float64) - K @ H
        self.kf._P = I_KH @ P_pred @ I_KH.T + K @ R @ K.T
        self._last_innovation = y
        self._last_likelihood = _gaussian_likelihood_2d(y, inv_S, det_S)

    def state(self) -> np.ndarray:
        if self.kf.state_vector is None:
            return np.zeros(4, dtype=np.float64)
        return self.kf.state_vector.squeeze()

    def covariance(self) -> np.ndarray:
        if self.kf.covariance_matrix is None:
            return np.eye(4, dtype=np.float64) * 100.0
        return self.kf.covariance_matrix

    def innovation(self) -> Optional[np.ndarray]:
        return self._last_innovation

    def likelihood(self) -> Optional[float]:
        return self._last_likelihood

    def reset(self) -> None:
        self.kf.reset()
        self._last_innovation = None
        self._last_likelihood = None


# ---------------------------------------------------------------------------
# CAModel: Constant-Acceleration (6-state, fully self-contained)
# ---------------------------------------------------------------------------

class CAModel(BaseModel):
    """Constant-acceleration 6-state model [x, y, vx, vy, ax, ay].

    Maintains its own 6x1 state vector and 6x6 covariance completely
    independently of TargetKalmanFilter to avoid 4D/6D shape conflicts.
    Projects to a 4-state view for IMM probability fusion.
    """

    _H = np.array([[1., 0., 0., 0., 0., 0.],
                   [0., 1., 0., 0., 0., 0.]], dtype=np.float64)

    def __init__(self, q_ca: float = 5.0):
        self.q_ca = float(q_ca)
        self._x6: Optional[np.ndarray] = None   # (6,1)
        self._P6: Optional[np.ndarray] = None   # (6,6)
        self._initialized: bool = False
        self._last_innovation: Optional[np.ndarray] = None
        self._last_likelihood: Optional[float] = None

    def _FQ(self, dt: float):
        dt2, dt3, dt4, dt5 = dt**2, dt**3, dt**4, dt**5
        F = np.array([
            [1, 0, dt, 0,  0.5*dt2, 0      ],
            [0, 1,  0, dt, 0,       0.5*dt2],
            [0, 0,  1,  0, dt,      0      ],
            [0, 0,  0,  1, 0,       dt     ],
            [0, 0,  0,  0, 1,       0      ],
            [0, 0,  0,  0, 0,       1      ],
        ], dtype=np.float64)
        q = self.q_ca ** 2
        Q = q * np.array([
            [dt5/20, 0,      dt4/8, 0,      dt3/6, 0    ],
            [0,      dt5/20, 0,     dt4/8,  0,     dt3/6],
            [dt4/8,  0,      dt3/3, 0,      dt2/2, 0    ],
            [0,      dt4/8,  0,     dt3/3,  0,     dt2/2],
            [dt3/6,  0,      dt2/2, 0,      dt,    0    ],
            [0,      dt3/6,  0,     dt2/2,  0,     dt   ],
        ], dtype=np.float64)
        return F, Q

    def predict(self, dt: float) -> None:
        if not self._initialized or self._x6 is None or self._P6 is None:
            return
        F, Q = self._FQ(dt)
        self._x6 = F @ self._x6
        self._P6 = F @ self._P6 @ F.T + Q

    def update(self, z: np.ndarray, R: np.ndarray) -> None:
        z_arr = np.asarray(z, dtype=np.float64).ravel()
        if not self._initialized:
            self._x6 = np.array(
                [z_arr[0], z_arr[1], 0., 0., 0., 0.], dtype=np.float64
            ).reshape(6, 1)
            self._P6 = np.diag([25., 25., 14400., 14400., 1e6, 1e6]).astype(np.float64)
            self._initialized = True
            self._last_innovation = np.zeros((2, 1), dtype=np.float64)
            self._last_likelihood = None
            return
        H = self._H
        y = z_arr.reshape(2, 1) - H @ self._x6
        S = H @ self._P6 @ H.T + R
        inv_S, det_S = _inv2x2_analytic(S)
        K = self._P6 @ H.T @ inv_S
        self._x6 = self._x6 + K @ y
        I_KH = np.eye(6, dtype=np.float64) - K @ H
        self._P6 = I_KH @ self._P6 @ I_KH.T + K @ R @ K.T
        self._last_innovation = y
        self._last_likelihood = _gaussian_likelihood_2d(y, inv_S, det_S)

    def state(self) -> np.ndarray:
        """Project 6-state to 4-state [x, y, vx, vy] for IMM fusion."""
        if not self._initialized or self._x6 is None:
            return np.zeros(4, dtype=np.float64)
        return self._x6[:4, 0].copy()

    def covariance(self) -> np.ndarray:
        """Project 6x6 covariance to top-left 4x4 block."""
        if not self._initialized or self._P6 is None:
            return np.eye(4, dtype=np.float64) * 100.0
        return self._P6[:4, :4].copy()

    def innovation(self) -> Optional[np.ndarray]:
        return self._last_innovation

    def likelihood(self) -> Optional[float]:
        return self._last_likelihood

    def reset(self) -> None:
        self._x6 = None
        self._P6 = None
        self._initialized = False
        self._last_innovation = None
        self._last_likelihood = None


# ---------------------------------------------------------------------------
# HMModel: High-Maneuver CV (4-state, elevated Q)
# ---------------------------------------------------------------------------

class HMModel(BaseModel):
    """High-maneuver CV model: CV dynamics with elevated process-noise Q.

    Fully self-contained (does not use TargetKalmanFilter) to avoid the
    uninitialized-state crash that occurs when state_vector is None.
    """

    _H = np.array([[1., 0., 0., 0.],
                   [0., 1., 0., 0.]], dtype=np.float64)

    def __init__(self, q_hm: float = 10.0):
        self.q_hm = float(q_hm)
        self._x4: Optional[np.ndarray] = None   # (4,1)
        self._P4: Optional[np.ndarray] = None   # (4,4)
        self._initialized: bool = False
        self._last_innovation: Optional[np.ndarray] = None
        self._last_likelihood: Optional[float] = None

    def _FQ(self, dt: float):
        dt2, dt3 = dt * dt, dt * dt * dt
        F = np.array([[1, 0, dt, 0],
                      [0, 1, 0, dt],
                      [0, 0, 1, 0],
                      [0, 0, 0, 1]], dtype=np.float64)
        q = self.q_hm ** 2
        Q = q * np.array([
            [dt3/3, 0,     dt2/2, 0    ],
            [0,     dt3/3, 0,     dt2/2],
            [dt2/2, 0,     dt,    0    ],
            [0,     dt2/2, 0,     dt   ],
        ], dtype=np.float64)
        return F, Q

    def predict(self, dt: float) -> None:
        if not self._initialized or self._x4 is None or self._P4 is None:
            return
        F, Q = self._FQ(dt)
        self._x4 = F @ self._x4
        self._P4 = F @ self._P4 @ F.T + Q

    def update(self, z: np.ndarray, R: np.ndarray) -> None:
        z_arr = np.asarray(z, dtype=np.float64).ravel()
        if not self._initialized:
            self._x4 = np.array(
                [z_arr[0], z_arr[1], 0., 0.], dtype=np.float64
            ).reshape(4, 1)
            self._P4 = np.diag([25., 25., 14400., 14400.]).astype(np.float64)
            self._initialized = True
            self._last_innovation = np.zeros((2, 1), dtype=np.float64)
            self._last_likelihood = None
            return
        H = self._H
        y = z_arr.reshape(2, 1) - H @ self._x4
        S = H @ self._P4 @ H.T + R
        inv_S, det_S = _inv2x2_analytic(S)
        K = self._P4 @ H.T @ inv_S
        self._x4 = self._x4 + K @ y
        I_KH = np.eye(4, dtype=np.float64) - K @ H
        self._P4 = I_KH @ self._P4 @ I_KH.T + K @ R @ K.T
        self._last_innovation = y
        self._last_likelihood = _gaussian_likelihood_2d(y, inv_S, det_S)

    def state(self) -> np.ndarray:
        if not self._initialized or self._x4 is None:
            return np.zeros(4, dtype=np.float64)
        return self._x4[:, 0].copy()

    def covariance(self) -> np.ndarray:
        if not self._initialized or self._P4 is None:
            return np.eye(4, dtype=np.float64) * 100.0
        return self._P4.copy()

    def innovation(self) -> Optional[np.ndarray]:
        return self._last_innovation

    def likelihood(self) -> Optional[float]:
        return self._last_likelihood

    def reset(self) -> None:
        self._x4 = None
        self._P4 = None
        self._initialized = False
        self._last_innovation = None
        self._last_likelihood = None


# ---------------------------------------------------------------------------
# CTModel: Coordinated-Turn EKF (5-state non-linear)
# ---------------------------------------------------------------------------

class CTModel(BaseModel):
    """Coordinated-Turn non-linear EKF: state = [x, y, V, psi, omega].

    Predict uses exact CT kinematics with first-order Jacobian linearisation
    for covariance propagation. Update extracts [x, y] via 2x5 H.
    All 2x2 innovation-covariance inversions are analytic.
    """

    _H = np.array([[1., 0., 0., 0., 0.],
                   [0., 1., 0., 0., 0.]], dtype=np.float64)

    def __init__(self, process_noise_std: float = 1.0):
        self.q_std = float(process_noise_std)
        self._x: np.ndarray = np.zeros(5, dtype=np.float64)
        self._P: np.ndarray = np.eye(5, dtype=np.float64) * 10.0
        self._initialized: bool = False
        self._last_innovation: Optional[np.ndarray] = None
        self._last_likelihood: Optional[float] = None

    def predict(self, dt: float) -> None:
        if not self._initialized:
            return
        x, y, V, psi, w = self._x
        if abs(w) > 1e-5:
            sn = math.sin(psi + w * dt)
            cn = math.cos(psi + w * dt)
            so = math.sin(psi)
            co = math.cos(psi)
            wi = 1.0 / w
            wi2 = wi * wi
            x_next = x + (V * wi) * (sn - so)
            y_next = y - (V * wi) * (cn - co)
            F = np.array([
                [1, 0, (sn-so)*wi, (V*wi)*(cn-co),
                 (V*dt*cn)*wi - (V*(sn-so))*wi2],
                [0, 1, -(cn-co)*wi, (V*wi)*(sn-so),
                 (V*dt*sn)*wi - (V*(-cn+co))*wi2],
                [0, 0, 1, 0, 0],
                [0, 0, 0, 1, dt],
                [0, 0, 0, 0, 1],
            ], dtype=np.float64)
        else:
            cp = math.cos(psi)
            sp = math.sin(psi)
            x_next = x + V * cp * dt
            y_next = y + V * sp * dt
            F = np.array([
                [1, 0, cp*dt, -V*sp*dt, 0],
                [0, 1, sp*dt,  V*cp*dt, 0],
                [0, 0, 1, 0, 0],
                [0, 0, 0, 1, dt],
                [0, 0, 0, 0, 1],
            ], dtype=np.float64)
        psi_next = (psi + w * dt + math.pi) % (2.0 * math.pi) - math.pi
        self._x = np.array([x_next, y_next, V, psi_next, w], dtype=np.float64)
        q = self.q_std
        Q = np.diag([
            0.1 * dt**2, 0.1 * dt**2,
            (q * dt)**2, (0.1 * dt)**2, (0.05 * dt)**2,
        ]).astype(np.float64)
        self._P = F @ self._P @ F.T + Q

    def update(self, z: np.ndarray, R: np.ndarray) -> None:
        z_arr = np.asarray(z, dtype=np.float64).ravel()
        if not self._initialized:
            self._x = np.array(
                [z_arr[0], z_arr[1], 0., 0., 0.], dtype=np.float64
            )
            self._initialized = True
            self._last_innovation = np.zeros((2, 1), dtype=np.float64)
            self._last_likelihood = None
            return
        H = self._H
        y = z_arr.reshape(2, 1) - H @ self._x.reshape(5, 1)
        S = H @ self._P @ H.T + R
        inv_S, det_S = _inv2x2_analytic(S)
        K = self._P @ H.T @ inv_S
        self._x = self._x + (K @ y).squeeze()
        I_KH = np.eye(5, dtype=np.float64) - K @ H
        self._P = I_KH @ self._P @ I_KH.T + K @ R @ K.T
        self._last_innovation = y
        self._last_likelihood = _gaussian_likelihood_2d(y, inv_S, det_S)

    def state(self) -> np.ndarray:
        """Convert [x, y, V, psi, omega] -> Cartesian [x, y, vx, vy]."""
        x, y, V, psi, _ = self._x
        return np.array([x, y, V * math.cos(psi), V * math.sin(psi)], dtype=np.float64)

    def covariance(self) -> np.ndarray:
        """Approximate 4x4 Cartesian covariance from polar 5x5 covariance."""
        P_cart = np.zeros((4, 4), dtype=np.float64)
        P_cart[0:2, 0:2] = self._P[0:2, 0:2]
        v_var = max(10.0, float(self._P[2, 2]))
        P_cart[2, 2] = v_var
        P_cart[3, 3] = v_var
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
'''

with open(TARGET, "w", encoding="utf-8", newline="\n") as fh:
    fh.write(CONTENT)

# Verify key properties
with open(TARGET, encoding="utf-8") as fh:
    src = fh.read()

checks = {
    "Analytic inversion present": "_inv2x2_analytic" in src,
    "Joseph-form present": "I_KH @ P_pred @ I_KH.T" in src,
    "CVModel old bug removed": "self.kf.update(z, R)" not in src,
    "CAModel None guard present": "self._x6 is None" in src,
    "HMModel None guard present": "self._x4 is None" in src,
    "CTModel init guard": "if not self._initialized" in src,
    "Exponent clip present": "min(float(" in src,
}

all_ok = True
for name, result in checks.items():
    status = "OK" if result else "FAIL"
    if not result:
        all_ok = False
    print(f"  [{status}] {name}")

print()
if all_ok:
    print("All checks passed. imm_models.py rewritten successfully.")
else:
    print("SOME CHECKS FAILED - inspect the output file!")
