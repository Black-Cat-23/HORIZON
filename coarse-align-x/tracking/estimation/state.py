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
