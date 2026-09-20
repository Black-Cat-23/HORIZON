"""
HORIZON Tracking Diagnostics Package
===========================================
Ground-truth evaluation and visual diagnostic utilities.
"""

from tracking.diagnostics.evaluation import (
    EstimatorEvaluator,
    EvaluationMetrics,
    TrackingErrorSample,
)
from tracking.diagnostics.visualization import draw_tracking_annotations

__all__ = [
    "EstimatorEvaluator",
    "EvaluationMetrics",
    "TrackingErrorSample",
    "draw_tracking_annotations",
]
