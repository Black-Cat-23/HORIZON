"""
HORIZON Target State Estimation Representations
=======================================================
Defines state vectors, estimator status enumeration, and immutable
state estimation outputs for optical beacon tracking.

State Vector Convention (Image-Plane):
    x = [p_x, p_y, v_x, v_y]^T
    - p_x: Horizontal pixel position on sensor [px], origin top-left
    - p_y: Vertical pixel position on sensor [px], origin top-left
    - v_x: Horizontal pixel velocity on sensor [px/s]
    - v_y: Vertical pixel velocity on sensor [px/s]

Strict Invariant: Zero access to true target position or ground-truth state.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional, Tuple
import numpy as np


class EstimatorStatus(Enum):
    """Discrete operational state of the target state estimator.

    PROJECT ENGINEERING PARAMETER - State taxonomy for optical state estimation.
    NOTE: These are purely filter states, distinct from future PAT mission states
    (e.g., SEARCH, ACQUIRE, TRACK, DEGRADED, REACQUIRE).
    """
    UNINITIALIZED = "UNINITIALIZED"
    INITIALIZING = "INITIALIZING"
    TRACKING = "TRACKING"
    PREDICTING = "PREDICTING"
    REJECTED_MEASUREMENT = "REJECTED_MEASUREMENT"
    RESET = "RESET"


@dataclass(frozen=True)
class FilterState:
    """Internal state vector and covariance representation."""
    x: np.ndarray  # Shape: (4, 1), float64
    P: np.ndarray  # Shape: (4, 4), float64
    timestamp: float
    track_age: int
    consecutive_hits: int
    consecutive_misses: int


@dataclass(frozen=True)
class EstimatorHealth:
    """Structured telemetry record exposing comprehensive state estimator health.

    Contains statistical metrics (NIS, NEES evaluation), 3-model IMM probabilities,
    uncertainty bounds, and measurement gating decisions for explainable diagnostic health.
    """
    track_health: float                     # [0.0, 1.0] composite estimator health score
    position_sigma: float                   # Total 1-sigma position uncertainty [px]
    velocity_sigma: float                   # Total 1-sigma velocity uncertainty [px/s]
    innovation_health: float                # [0.0, 1.0] innovation consistency score
    model_probabilities: Tuple[float, float, float]  # (P_CV, P_CA, P_MANEUVER)
    measurement_accepted: bool              # Gating decision for current frame
    prediction_age_frames: int             # Consecutive missing measurement predictions
    nis: float                             # Normalized Innovation Squared (NIS = v^T S^-1 v)
    nees_eval: Optional[float] = None       # Evaluation-only NEES ((x_true - x_hat)^T P^-1 (x_true - x_hat))
    mahalanobis_distance: float = 0.0      # Mahalanobis distance d_M = sqrt(NIS)
    mahalanobis_threshold: float = 16.0     # Chi-squared gate threshold (e.g. 16.0 for 99.9% 2DOF)


@dataclass(frozen=True)
class StateEstimate:
    """Standardized output of the Phase 5 State Estimator.

    Contains filtered target kinematics, covariance, innovation metrics,
    and associated tracking quality indicators.
    """
    estimated_x: float
    estimated_y: float
    estimated_vx: float
    estimated_vy: float
    covariance: np.ndarray  # (4, 4) float64
    innovation: Optional[np.ndarray]  # (2, 1) or None during pure prediction
    predicted_x: float
    predicted_y: float
    filter_status: EstimatorStatus
    timestamp: float
    measurement_available: bool
    track_age: int
    consecutive_measurements: int
    consecutive_misses: int
    mahalanobis_distance: float = 0.0
    association_quality: float = 0.0
    processing_time_ms: float = 0.0
    predicted_vx: float = 0.0
    predicted_vy: float = 0.0
    nis: float = 0.0
    nees_eval: Optional[float] = None
    estimator_health: Optional[EstimatorHealth] = None

    @property
    def position_sigma_x(self) -> float:
        """1-sigma standard deviation of horizontal position [px]."""
        return float(np.sqrt(max(0.0, self.covariance[0, 0])))

    @property
    def position_sigma_y(self) -> float:
        """1-sigma standard deviation of vertical position [px]."""
        return float(np.sqrt(max(0.0, self.covariance[1, 1])))

    @property
    def velocity_sigma_x(self) -> float:
        """1-sigma standard deviation of horizontal velocity [px/s]."""
        return float(np.sqrt(max(0.0, self.covariance[2, 2])))

    @property
    def velocity_sigma_y(self) -> float:
        """1-sigma standard deviation of vertical velocity [px/s]."""
        return float(np.sqrt(max(0.0, self.covariance[3, 3])))

    @property
    def position_uncertainty(self) -> float:
        """Total positional standard uncertainty norm sqrt(sigma_x^2 + sigma_y^2) [px]."""
        return float(np.sqrt(max(0.0, self.covariance[0, 0] + self.covariance[1, 1])))

    @property
    def velocity_uncertainty(self) -> float:
        """Total velocity standard uncertainty norm sqrt(sigma_vx^2 + sigma_vy^2) [px/s]."""
        return float(np.sqrt(max(0.0, self.covariance[2, 2] + self.covariance[3, 3])))

