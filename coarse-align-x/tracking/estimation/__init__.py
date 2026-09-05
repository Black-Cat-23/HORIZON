"""
HORIZON State Estimation Package
=======================================
Public interfaces for Kalman filtering, covariance mathematics,
kinematic transition models, and innovation calculations.
"""

from tracking.estimation.covariance import (
    CovarianceEllipseData,
    compute_covariance_ellipse,
    enforce_symmetry,
    validate_covariance,
)
from tracking.estimation.innovation import Innovation, compute_innovation
from tracking.estimation.kalman import KalmanFilterConfig, TargetKalmanFilter
from tracking.estimation.model import (
    build_measurement_matrix,
    build_measurement_noise_matrix,
    build_process_noise_matrix,
    build_transition_matrix,
)
from tracking.estimation.state import (
    EstimatorStatus,
    FilterState,
    StateEstimate,
)

__all__ = [
    "CovarianceEllipseData",
    "compute_covariance_ellipse",
    "enforce_symmetry",
    "validate_covariance",
    "Innovation",
    "compute_innovation",
    "KalmanFilterConfig",
    "TargetKalmanFilter",
    "build_measurement_matrix",
    "build_measurement_noise_matrix",
    "build_process_noise_matrix",
    "build_transition_matrix",
    "EstimatorStatus",
    "FilterState",
    "StateEstimate",
]
