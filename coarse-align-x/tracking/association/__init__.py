"""
HORIZON Track Association Package
========================================
Public interfaces for track management, Mahalanobis gating,
and multi-candidate association.
"""

from tracking.association.association import (
    AssociationResult,
    MeasurementCandidate,
    TrackAssociator,
)
from tracking.association.gate import (
    CHI2_2DOF_THRESHOLDS,
    MahalanobisGate,
)
from tracking.association.track import Track

__all__ = [
    "AssociationResult",
    "MeasurementCandidate",
    "TrackAssociator",
    "CHI2_2DOF_THRESHOLDS",
    "MahalanobisGate",
    "Track",
]
