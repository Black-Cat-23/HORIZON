"""
HORIZON Perception Module (Phase 4)
==========================================
Classical beacon detection, adaptive filtering, and subpixel centroiding.
"""

from simulator.perception.candidate import BeaconCandidate
from simulator.perception.config import (
    CandidateScoringConfig,
    CentroidConfig,
    DetectorConfig,
    PreprocessingConfig,
)
from simulator.perception.detector import ClassicalBeaconDetector, DetectionResult
from simulator.perception.diagnostics import DetectionDiagnostics

__all__ = [
    "DetectorConfig",
    "PreprocessingConfig",
    "CandidateScoringConfig",
    "CentroidConfig",
    "ClassicalBeaconDetector",
    "DetectionResult",
    "BeaconCandidate",
    "DetectionDiagnostics",
]
