"""
HORIZON Phase 5 Tracking & State Estimation Subsystem
============================================================
Real-time target state estimation, continuous-velocity Kalman filtering,
Mahalanobis gating, multi-candidate track association, and quality monitoring.
"""

from tracking.association import (
    AssociationResult,
    CHI2_2DOF_THRESHOLDS,
    MahalanobisGate,
    MeasurementCandidate,
    Track,
    TrackAssociator,
)
from tracking.diagnostics import (
    EstimatorEvaluator,
    EvaluationMetrics,
    TrackingErrorSample,
    draw_tracking_annotations,
)
from tracking.estimation import (
    CovarianceEllipseData,
    EstimatorStatus,
    FilterState,
    Innovation,
    KalmanFilterConfig,
    StateEstimate,
    TargetKalmanFilter,
    build_measurement_matrix,
    build_measurement_noise_matrix,
    build_process_noise_matrix,
    build_transition_matrix,
    compute_covariance_ellipse,
    compute_innovation,
    enforce_symmetry,
    validate_covariance,
)
from tracking.quality import (
    TrackQuality,
    evaluate_track_quality,
)

__all__ = [
    # Association
    "AssociationResult",
    "CHI2_2DOF_THRESHOLDS",
    "MahalanobisGate",
    "MeasurementCandidate",
    "Track",
    "TrackAssociator",
    # Estimation
    "CovarianceEllipseData",
    "EstimatorStatus",
    "FilterState",
    "Innovation",
    "KalmanFilterConfig",
    "StateEstimate",
    "TargetKalmanFilter",
    "build_measurement_matrix",
    "build_measurement_noise_matrix",
    "build_process_noise_matrix",
    "build_transition_matrix",
    "compute_covariance_ellipse",
    "compute_innovation",
    "enforce_symmetry",
    "validate_covariance",
    # Quality
    "TrackQuality",
    "evaluate_track_quality",
    # Diagnostics
    "EstimatorEvaluator",
    "EvaluationMetrics",
    "TrackingErrorSample",
    "draw_tracking_annotations",
]
