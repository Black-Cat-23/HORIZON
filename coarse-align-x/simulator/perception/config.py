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
    min_area_px: float = 4.0        # Minimum valid beacon area (supporting down to subpixel beacon)
    max_area_px: float = 1600.0     # Maximum valid beacon area (supporting up to 30×30 beacon)
    min_peak_intensity: int = 15    # Minimum peak intensity above noise floor (supporting low contrast / fog)
    min_snr: float = 1.2            # Signal-to-noise ratio threshold
    expected_size_px: float = 10.0  # Project nominal beacon size
    size_tolerance_factor: float = 3.0
    min_circularity: float = 0.10   # Rejects non-optical artifacts while accepting motion-blurred streaks


@dataclass(frozen=True)
class CentroidConfig:
    """Subpixel centroid calculation configuration."""
    method: Literal["weighted_cog", "geometric", "gaussian_fit"] = "weighted_cog"
    roi_padding_px: int = 4         # Margin around candidate bbox for centroid computation
    gaussian_fit_max_iter: int = 20
    gaussian_fit_tol: float = 1e-3


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
    """Parameters and weight allocations for Phase 8 Hybrid Perception Fusion.

    All weights are normalised at runtime — they express relative importance, not
    absolute magnitudes.  Setting a weight to 0.0 removes that feature entirely.

    Acceptance thresholds:
        acceptance_threshold           — gate for any single candidate to be declared detected.
        partial_confidence_threshold   — lower gate ONLY applied to MATCHED (BOTH) pairs;
                                         allows fused confirmation even in heavy disturbance.
        disagreement_rejection_threshold — candidates below this are immediately rejected.

    Matching:
        max_matching_distance_px  — base centroid-distance gate; scaled dynamically by
                                    estimated beacon velocity at runtime.
        velocity_scale_factor     — controls how aggressively velocity widens the gate:
                                    dynamic_gate = base × (1 + vel_px_s / velocity_scale_factor)
                                    Set to 0.0 to disable velocity scaling (fixed gate).
        max_matching_distance_cap — hard upper bound on dynamic gate in pixels.

    SNR gating:
        min_contrast_sigma_factor — contrast gate = max(min_contrast_floor_adu,
                                    min_contrast_sigma_factor × bg_noise_std)
        min_contrast_floor_adu    — absolute minimum contrast (ADU); prevents gate from
                                    collapsing under very low noise estimates.
        min_snr_factor            — SNR gate = max(min_snr_floor,
                                    min_snr_factor × bg_noise_std / 8.0)
        min_snr_floor             — absolute minimum SNR floor.
    """
    # --- Fusion weights (normalised at runtime) ---
    classical_weight: float = 0.28
    neural_weight: float = 0.28
    spatial_weight: float = 0.16
    size_weight: float = 0.10
    optical_weight: float = 0.10
    temporal_weight: float = 0.08

    # --- Acceptance gates ---
    acceptance_threshold: float = 0.28           # any candidate
    partial_confidence_threshold: float = 0.20   # BOTH-source matched pairs only
    disagreement_rejection_threshold: float = 0.10

    # --- Matching geometry ---
    max_matching_distance_px: float = 25.0
    velocity_scale_factor: float = 60.0          # pixels/s per unit of gate expansion
    max_matching_distance_cap: float = 80.0      # hard upper cap (px)
    min_matching_iou: float = 0.10

    # --- SNR-adaptive candidate extraction ---
    min_contrast_sigma_factor: float = 3.0       # contrast >= factor × bg_noise_std
    min_contrast_floor_adu: float = 12.0         # absolute minimum (ADU)
    min_snr_factor: float = 0.90                 # snr >= factor × (bg_noise_std / 8)
    min_snr_floor: float = 1.2                   # absolute minimum SNR

    # --- Feature flags ---
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
    min_detection_confidence: float = 0.28
    perception_mode: Literal["CLASSICAL", "NEURAL", "HYBRID"] = "HYBRID"
    preprocessing: PreprocessingConfig = field(default_factory=PreprocessingConfig)
    scoring: CandidateScoringConfig = field(default_factory=CandidateScoringConfig)
    centroid: CentroidConfig = field(default_factory=CentroidConfig)
    neural: NeuralDetectorConfig = field(default_factory=NeuralDetectorConfig)
    hybrid: HybridDetectorConfig = field(default_factory=HybridDetectorConfig)

