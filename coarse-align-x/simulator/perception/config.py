"""
HORIZON Perception Configuration
=======================================
Typed configuration dataclasses for Phase 4 classical beacon detection,
Phase 7 neural YOLOv8n ONNX perception, preprocessing, candidate scoring, and subpixel centroiding.

Strict Invariant: Zero ground-truth dependencies or leakage.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


@dataclass(frozen=True)
class PreprocessingConfig:
    """Optical frame preprocessing configuration."""
    enable_adaptive_median: bool = True
    max_median_window: int = 5
    enable_background_subtraction: bool = True
    gaussian_blur_sigma: float = 0.0  # 0.0 = disabled to avoid blurring small subpixel beacons


@dataclass(frozen=True)
class CandidateScoringConfig:
    """Parameters for beacon candidate extraction, filtering, and scoring."""
    min_area_px: float = 4.0        # Minimum valid beacon area (supporting down to 5×5 subpixel beacon)
    max_area_px: float = 650.0      # Maximum valid beacon area (supporting up to 20×20 beacon)
    min_peak_intensity: int = 40    # Minimum peak intensity above noise floor
    min_snr: float = 1.2            # Signal-to-noise ratio threshold
    expected_size_px: float = 10.0  # Project nominal beacon size
    size_tolerance_factor: float = 3.0
    min_circularity: float = 0.25   # Rejects highly elongated noise streaks


@dataclass(frozen=True)
class CentroidConfig:
    """Subpixel centroid calculation configuration."""
    method: Literal["weighted_cog", "geometric", "gaussian_fit"] = "weighted_cog"
    roi_padding_px: int = 4         # Margin around candidate bbox for centroid computation
    gaussian_fit_max_iter: int = 50
    gaussian_fit_tol: float = 1e-4


@dataclass(frozen=True)
class NeuralDetectorConfig:
    """Configuration parameters for Phase 7 YOLOv8n ONNX Neural Detector."""
    onnx_model_path: str = "research/training/models/yolov8n_beacon.onnx"
    metadata_path: str = "research/training/models/model_metadata.json"
    confidence_threshold: float = 0.35
    nms_iou_threshold: float = 0.45
    input_size: int = 640
    enable_subpixel_refinement: bool = True


@dataclass(frozen=True)
class HybridFusionConfig:
    """Parameters and weight allocations for Phase 8 Hybrid Perception Fusion."""
    classical_weight: float = 0.30
    neural_weight: float = 0.30
    spatial_weight: float = 0.15
    size_weight: float = 0.10
    optical_weight: float = 0.10
    temporal_weight: float = 0.05
    max_matching_distance_px: float = 25.0
    min_matching_iou: float = 0.10
    acceptance_threshold: float = 0.35
    disagreement_rejection_threshold: float = 0.15
    enable_optical_centroid_refinement: bool = True
    enable_temporal_consistency: bool = True


@dataclass(frozen=True)
class HybridDetectorConfig:
    """Configuration for Phase 8 HybridBeaconDetector System."""
    fusion: HybridFusionConfig = field(default_factory=HybridFusionConfig)
    fallback_mode: Literal["CLASSICAL_ONLY", "NEURAL_ONLY", "NO_DETECTION"] = "CLASSICAL_ONLY"


@dataclass(frozen=True)
class DetectorConfig:
    """Root configuration for classical, neural, and hybrid perception engines."""
    input_width: int = 640
    input_height: int = 480
    min_detection_confidence: float = 0.35
    perception_mode: Literal["CLASSICAL", "NEURAL", "HYBRID"] = "HYBRID"
    preprocessing: PreprocessingConfig = field(default_factory=PreprocessingConfig)
    scoring: CandidateScoringConfig = field(default_factory=CandidateScoringConfig)
    centroid: CentroidConfig = field(default_factory=CentroidConfig)
    neural: NeuralDetectorConfig = field(default_factory=NeuralDetectorConfig)
    hybrid: HybridDetectorConfig = field(default_factory=HybridDetectorConfig)

