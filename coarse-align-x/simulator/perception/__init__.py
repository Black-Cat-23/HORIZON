"""
HORIZON Perception Module (Phase 4)
==========================================
Classical beacon detection, adaptive filtering, and subpixel centroiding.
"""

from simulator.perception.candidate import BeaconCandidate
from simulator.perception.candidate_matcher import CandidateMatcher, MatchState, MatchedPair
from simulator.perception.config import (
    CandidateScoringConfig,
    CentroidConfig,
    DetectorConfig,
    HybridDetectorConfig,
    HybridFusionConfig,
    NeuralDetectorConfig,
    PreprocessingConfig,
)
from simulator.perception.detector import ClassicalBeaconDetector, DetectionResult
from simulator.perception.diagnostics import DetectionDiagnostics
from simulator.perception.hybrid_candidate import CandidateSource, UnifiedCandidate
from simulator.perception.hybrid_detector import HybridBeaconDetector
from simulator.perception.neural_detector import NeuralBeaconDetector

__all__ = [
    "DetectorConfig",
    "PreprocessingConfig",
    "CandidateScoringConfig",
    "CentroidConfig",
    "NeuralDetectorConfig",
    "HybridDetectorConfig",
    "HybridFusionConfig",
    "ClassicalBeaconDetector",
    "NeuralBeaconDetector",
    "HybridBeaconDetector",
    "DetectionResult",
    "BeaconCandidate",
    "UnifiedCandidate",
    "CandidateSource",
    "CandidateMatcher",
    "MatchState",
    "MatchedPair",
    "DetectionDiagnostics",
]

