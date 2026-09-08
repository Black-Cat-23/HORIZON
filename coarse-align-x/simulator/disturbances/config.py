"""
HORIZON Disturbance Configuration
========================================
Typed configuration dataclasses and validation for the Phase 3 disturbance engine.
Enforces official SIH26169 parameters and bounds:
  - Gaussian noise sigma max: 20 pixels
  - Camera jitter max: ±20 pixels/frame
  - Platform motion max: ±20 pixels/frame
  - Atmospheric conditions: CLEAR, HAZE, FOG, RAIN, LOW_LIGHT
  - Phase 3 Extensions: Intensity Fluctuation, Occlusion, Distractors, Correlation, Injection Scheduling
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Optional, Tuple


# =============================================================================
# Sub-component Configurations
# =============================================================================

@dataclass(frozen=True)
class SaltPepperConfig:
    """Salt & Pepper impulse noise configuration.

    Parameters:
        enabled: Toggle noise stage.
        probability: Fraction of image pixels affected (0.0 to 1.0).
                     Default is 0.10 (~10%) per official SIH reference.
    """
    enabled: bool = False
    probability: float = 0.10  # OFFICIAL REFERENCE: ~10%


@dataclass(frozen=True)
class GaussianNoiseConfig:
    """Additive zero-mean Gaussian sensor noise configuration.

    Parameters:
        enabled: Toggle noise stage.
        sigma: Standard deviation in pixel intensity levels.
               Must satisfy 0.0 <= sigma <= 20.0 per official SIH specification.
    """
    enabled: bool = False
    sigma: float = 10.0  # OFFICIAL MAXIMUM: 20.0 pixels


@dataclass(frozen=True)
class PoissonNoiseConfig:
    """Poisson photon-counting shot noise configuration.

    Parameters:
        enabled: Toggle noise stage.
        peak_photons: Effective maximum photon count corresponding to max pixel intensity (255).
                      Lower values produce stronger relative Poisson noise.
                      Label: PROJECT DEFAULT (engineering assumption).
    """
    enabled: bool = False
    peak_photons: float = 50.0  # PROJECT DEFAULT


@dataclass(frozen=True)
class CameraJitterConfig:
    """Image-plane camera jitter configuration (zero-mean displacement).

    Parameters:
        enabled: Toggle jitter.
        max_x_px: Maximum displacement along horizontal image axis (pixels).
                  Must satisfy 0.0 <= max_x_px <= 20.0 per official SIH limit.
        max_y_px: Maximum displacement along vertical image axis (pixels).
                  Must satisfy 0.0 <= max_y_px <= 20.0 per official SIH limit.
        distribution: Displacement distribution ('uniform' or 'normal').
    """
    enabled: bool = False
    max_x_px: float = 5.0   # OFFICIAL MAXIMUM: ±20.0 px/frame
    max_y_px: float = 5.0   # OFFICIAL MAXIMUM: ±20.0 px/frame
    distribution: str = "uniform"  # PROJECT DEFAULT: "uniform" or "normal"


@dataclass(frozen=True)
class PlatformMotionConfig:
    """Continuous platform motion configuration.

    Parameters:
        enabled: Toggle platform motion.
        model: Motion model ('linear', 'circular', 'random', 'spiral', 'figure8').
               Mandatory: 'linear'.
        max_dx_px_per_frame: Maximum velocity along X in pixels per frame.
                             Must satisfy <= 20.0 per official SIH limit.
        max_dy_px_per_frame: Maximum velocity along Y in pixels per frame.
                             Must satisfy <= 20.0 per official SIH limit.
        velocity_x: Desired horizontal velocity in pixels/second (converted to px/frame via dt).
        velocity_y: Desired vertical velocity in pixels/second (converted to px/frame via dt).
        boundary_limit_px: Maximum cumulative platform offset before reversal/bounce (pixels).
    """
    enabled: bool = False
    model: str = "linear"  # Mandatory: linear; Optional: circular, random, spiral, figure8
    max_dx_px_per_frame: float = 20.0  # OFFICIAL MAXIMUM: ±20.0 px/frame
    max_dy_px_per_frame: float = 20.0  # OFFICIAL MAXIMUM: ±20.0 px/frame
    velocity_x: float = 60.0  # px/s (at 60Hz = 1 px/frame)
    velocity_y: float = 30.0  # px/s (at 60Hz = 0.5 px/frame)
    boundary_limit_px: float = 100.0  # PROJECT DEFAULT


VALID_ATMOSPHERE_CONDITIONS = {
    "clear", "haze", "fog", "rain", "low_light"
}

ATMOSPHERE_PRESETS = {
    "clear": {"contrast_factor": 1.0, "brightness_factor": 0.0},
    "haze": {"contrast_factor": 0.65, "brightness_factor": 0.12},
    "fog": {"contrast_factor": 0.35, "brightness_factor": 0.25},
    "rain": {"contrast_factor": 0.70, "brightness_factor": -0.05},
    "low_light": {"contrast_factor": 0.85, "brightness_factor": -0.40},
}


@dataclass(frozen=True)
class AtmosphereConfig:
    """Atmospheric degradation configuration.

    Parameters:
        enabled: Toggle atmospheric degradation.
        condition: Official condition ('clear', 'haze', 'fog', 'rain', 'low_light').
        contrast_factor: Multiplier for image contrast (>= 0.0). PROJECT DEFAULT if None.
        brightness_factor: Additive offset for brightness (-1.0 to 1.0). PROJECT DEFAULT if None.
        severity: Continuous degradation severity scale (0.0 to 1.0).
    """
    enabled: bool = False
    condition: str = "clear"  # OFFICIAL: clear, haze, fog, rain, low_light
    contrast_factor: Optional[float] = None     # PROJECT DEFAULT
    brightness_factor: Optional[float] = None   # PROJECT DEFAULT
    severity: float = 0.5                      # Continuous severity parameter [0.0, 1.0]


@dataclass(frozen=True)
class BeamWanderConfig:
    """Optical beam-centroid wander configuration (Ornstein-Uhlenbeck process).

    Parameters:
        enabled: Toggle beam-wander disturbance.
        std_dev_px: Stationary standard deviation of beam centroid offset (pixels).
        correlation_time_s: OU process correlation time scale tau (seconds, > 0).
    """
    enabled: bool = False
    std_dev_px: float = 2.0         # Standard deviation in pixels
    correlation_time_s: float = 0.5 # Correlation time scale in seconds (> 0)


# =============================================================================
# Phase 3 Extension Configurations
# =============================================================================

@dataclass(frozen=True)
class IntensityFluctuationConfig:
    """Temporal beacon intensity fluctuation (scintillation / envelope fading).

    Parameters:
        enabled: Toggle temporal intensity fluctuation.
        mode: Fluctuation profile ('slow', 'fast', 'mixed').
        depth: Peak modulation depth (0.0 = no variation, 1.0 = full attenuation).
        frequency_hz: Fluctuation frequency scale in Hz (> 0).
    """
    enabled: bool = False
    mode: str = "mixed"       # 'slow', 'fast', 'mixed'
    depth: float = 0.4        # Depth fraction [0.0, 1.0]
    frequency_hz: float = 5.0 # Modulation frequency (Hz)


@dataclass(frozen=True)
class OcclusionConfig:
    """Temporary beacon occlusion configuration.

    Parameters:
        enabled: Toggle temporary occlusion.
        type: Occlusion coverage ('partial', 'complete').
        start_time_s: Simulation timestamp when occlusion starts.
        duration_s: Duration of occlusion event in seconds.
        severity: Fraction of beacon obscured (0.0 to 1.0).
    """
    enabled: bool = False
    type: str = "complete"      # 'partial' or 'complete'
    start_time_s: float = 2.0   # Start timestamp (s)
    duration_s: float = 1.0     # Event duration (s)
    severity: float = 1.0       # Occlusion fraction [0.0, 1.0]


@dataclass(frozen=True)
class DistractorConfig:
    """False optical distractor target generation configuration.

    Parameters:
        enabled: Toggle false optical target distractors.
        type: Distractor geometry/profile ('small_spot', 'large_blob', 'multiple_spots', 'reflection_like', 'noise_cluster').
        count: Number of distractor instances (>= 1).
        intensity: Distractor peak intensity (0–255).
        movement_model: Distractor motion model ('static', 'linear', 'random').
        speed_px_s: Speed of distractor motion in px/s.
    """
    enabled: bool = False
    type: str = "small_spot"   # 'small_spot', 'large_blob', 'multiple_spots', 'reflection_like', 'noise_cluster'
    count: int = 2
    intensity: int = 240
    movement_model: str = "linear"
    speed_px_s: float = 40.0


@dataclass(frozen=True)
class DisturbanceCorrelationConfig:
    """Cross-channel disturbance correlation configuration.

    Parameters:
        enabled: Toggle correlated stochastic processes.
        platform_jitter_coupling: Correlation coefficient between platform motion and camera jitter [0.0, 1.0].
        intensity_atmosphere_coupling: Correlation coefficient between atmospheric fading and intensity fluctuations [0.0, 1.0].
    """
    enabled: bool = False
    platform_jitter_coupling: float = 0.0
    intensity_atmosphere_coupling: float = 0.0


@dataclass(frozen=True)
class InjectionScheduleConfig:
    """Dynamic disturbance injection scheduler configuration.

    Parameters:
        enabled: Toggle time-varying disturbance gain.
        injection_mode: Injection schedule profile ('immediate', 'ramped', 'pulsed', 'scheduled').
        start_time_s: Start time for ramped/pulsed/scheduled injection (s).
        ramp_duration_s: Duration of ramp-up transition (s).
        pulse_period_s: Period of pulsed bursts in seconds.
        pulse_duty_cycle: Active fraction of pulse period (0.0 to 1.0).
    """
    enabled: bool = False
    injection_mode: str = "immediate"  # 'immediate', 'ramped', 'pulsed', 'scheduled'
    start_time_s: float = 0.0
    ramp_duration_s: float = 1.0
    pulse_period_s: float = 2.0
    pulse_duty_cycle: float = 0.5


# =============================================================================
# Aggregate Disturbance Configuration
# =============================================================================

@dataclass(frozen=True)
class DisturbanceConfig:
    """Aggregate disturbance pipeline configuration."""
    enabled: bool = True
    salt_pepper: SaltPepperConfig = field(default_factory=SaltPepperConfig)
    gaussian: GaussianNoiseConfig = field(default_factory=GaussianNoiseConfig)
    poisson: PoissonNoiseConfig = field(default_factory=PoissonNoiseConfig)
    camera_jitter: CameraJitterConfig = field(default_factory=CameraJitterConfig)
    platform_motion: PlatformMotionConfig = field(default_factory=PlatformMotionConfig)
    atmosphere: AtmosphereConfig = field(default_factory=AtmosphereConfig)
    beam_wander: BeamWanderConfig = field(default_factory=BeamWanderConfig)
    # Phase 3 Extensions
    intensity_fluctuation: IntensityFluctuationConfig = field(default_factory=IntensityFluctuationConfig)
    occlusion: OcclusionConfig = field(default_factory=OcclusionConfig)
    distractors: DistractorConfig = field(default_factory=DistractorConfig)
    correlation: DisturbanceCorrelationConfig = field(default_factory=DisturbanceCorrelationConfig)
    injection_schedule: InjectionScheduleConfig = field(default_factory=InjectionScheduleConfig)


# =============================================================================
# Validation Function
# =============================================================================

def validate_disturbance_config(config: DisturbanceConfig) -> None:
    """Validate all disturbance parameters against official SIH26169 limits and Phase 3 specifications.

    Raises:
        ValueError: If any parameter violates specifications.
    """
    errors: list[str] = []

    # 1. Salt & Pepper
    if not (0.0 <= config.salt_pepper.probability <= 1.0):
        errors.append(
            f"salt_pepper.probability must be in [0.0, 1.0], got {config.salt_pepper.probability}"
        )

    # 2. Gaussian Noise — OFFICIAL LIMIT: max sigma = 20 pixels
    if config.gaussian.sigma < 0.0 or config.gaussian.sigma > 20.0:
        errors.append(
            f"gaussian.sigma must be in [0.0, 20.0] pixels per official SIH specification, "
            f"got {config.gaussian.sigma}"
        )

    # 3. Poisson Noise
    if config.poisson.peak_photons <= 0.0:
        errors.append(
            f"poisson.peak_photons must be > 0.0, got {config.poisson.peak_photons}"
        )

    # 4. Camera Jitter — OFFICIAL LIMIT: max ±20 pixels/frame
    if not (0.0 <= config.camera_jitter.max_x_px <= 20.0):
        errors.append(
            f"camera_jitter.max_x_px must be in [0.0, 20.0] pixels per official SIH specification, "
            f"got {config.camera_jitter.max_x_px}"
        )
    if not (0.0 <= config.camera_jitter.max_y_px <= 20.0):
        errors.append(
            f"camera_jitter.max_y_px must be in [0.0, 20.0] pixels per official SIH specification, "
            f"got {config.camera_jitter.max_y_px}"
        )
    if config.camera_jitter.distribution not in {"uniform", "normal"}:
        errors.append(
            f"camera_jitter.distribution must be 'uniform' or 'normal', "
            f"got '{config.camera_jitter.distribution}'"
        )

    # 5. Platform Motion — OFFICIAL LIMIT: max ±20 pixels/frame
    valid_platform_models = {"linear", "circular", "random", "spiral", "figure8"}
    if config.platform_motion.model not in valid_platform_models:
        errors.append(
            f"platform_motion.model must be one of {valid_platform_models}, "
            f"got '{config.platform_motion.model}'"
        )
    if not (0.0 <= config.platform_motion.max_dx_px_per_frame <= 20.0):
        errors.append(
            f"platform_motion.max_dx_px_per_frame must be in [0.0, 20.0] pixels per official SIH specification, "
            f"got {config.platform_motion.max_dx_px_per_frame}"
        )
    if not (0.0 <= config.platform_motion.max_dy_px_per_frame <= 20.0):
        errors.append(
            f"platform_motion.max_dy_px_per_frame must be in [0.0, 20.0] pixels per official SIH specification, "
            f"got {config.platform_motion.max_dy_px_per_frame}"
        )

    # 6. Atmosphere
    cond = config.atmosphere.condition.lower()
    if cond not in VALID_ATMOSPHERE_CONDITIONS:
        errors.append(
            f"atmosphere.condition must be one of {VALID_ATMOSPHERE_CONDITIONS}, "
            f"got '{config.atmosphere.condition}'"
        )
    if not (0.0 <= config.atmosphere.severity <= 1.0):
        errors.append(
            f"atmosphere.severity must be in [0.0, 1.0], got {config.atmosphere.severity}"
        )
    if config.atmosphere.contrast_factor is not None:
        if config.atmosphere.contrast_factor < 0.0:
            errors.append(
                f"atmosphere.contrast_factor must be >= 0.0, "
                f"got {config.atmosphere.contrast_factor}"
            )
    if config.atmosphere.brightness_factor is not None:
        if not (-1.0 <= config.atmosphere.brightness_factor <= 1.0):
            errors.append(
                f"atmosphere.brightness_factor must be in [-1.0, 1.0], "
                f"got {config.atmosphere.brightness_factor}"
            )

    # 7. Beam Wander
    if config.beam_wander.std_dev_px < 0.0:
        errors.append(
            f"beam_wander.std_dev_px must be >= 0.0, got {config.beam_wander.std_dev_px}"
        )
    if config.beam_wander.correlation_time_s <= 0.0:
        errors.append(
            f"beam_wander.correlation_time_s must be > 0.0, got {config.beam_wander.correlation_time_s}"
        )

    # 8. Intensity Fluctuation
    if config.intensity_fluctuation.mode not in ("slow", "fast", "mixed"):
        errors.append(
            f"intensity_fluctuation.mode must be 'slow', 'fast', or 'mixed', got '{config.intensity_fluctuation.mode}'"
        )
    if not (0.0 <= config.intensity_fluctuation.depth <= 1.0):
        errors.append(
            f"intensity_fluctuation.depth must be in [0.0, 1.0], got {config.intensity_fluctuation.depth}"
        )
    if config.intensity_fluctuation.frequency_hz <= 0.0:
        errors.append(
            f"intensity_fluctuation.frequency_hz must be > 0.0, got {config.intensity_fluctuation.frequency_hz}"
        )

    # 9. Occlusion
    if config.occlusion.type not in ("partial", "complete"):
        errors.append(
            f"occlusion.type must be 'partial' or 'complete', got '{config.occlusion.type}'"
        )
    if config.occlusion.start_time_s < 0.0:
        errors.append(
            f"occlusion.start_time_s must be >= 0.0, got {config.occlusion.start_time_s}"
        )
    if config.occlusion.duration_s <= 0.0:
        errors.append(
            f"occlusion.duration_s must be > 0.0, got {config.occlusion.duration_s}"
        )
    if not (0.0 <= config.occlusion.severity <= 1.0):
        errors.append(
            f"occlusion.severity must be in [0.0, 1.0], got {config.occlusion.severity}"
        )

    # 10. Distractors
    valid_distractor_types = {"small_spot", "large_blob", "multiple_spots", "reflection_like", "noise_cluster"}
    if config.distractors.type not in valid_distractor_types:
        errors.append(
            f"distractors.type must be one of {valid_distractor_types}, got '{config.distractors.type}'"
        )
    if config.distractors.count < 1:
        errors.append(
            f"distractors.count must be >= 1, got {config.distractors.count}"
        )
    if not (0 <= config.distractors.intensity <= 255):
        errors.append(
            f"distractors.intensity must be in 0-255, got {config.distractors.intensity}"
        )

    # 11. Correlation
    if not (0.0 <= config.correlation.platform_jitter_coupling <= 1.0):
        errors.append(
            f"correlation.platform_jitter_coupling must be in [0.0, 1.0], got {config.correlation.platform_jitter_coupling}"
        )
    if not (0.0 <= config.correlation.intensity_atmosphere_coupling <= 1.0):
        errors.append(
            f"correlation.intensity_atmosphere_coupling must be in [0.0, 1.0], got {config.correlation.intensity_atmosphere_coupling}"
        )

    # 12. Injection Schedule
    valid_injection_modes = {"immediate", "ramped", "pulsed", "scheduled"}
    if config.injection_schedule.injection_mode not in valid_injection_modes:
        errors.append(
            f"injection_schedule.injection_mode must be one of {valid_injection_modes}, got '{config.injection_schedule.injection_mode}'"
        )

    if errors:
        raise ValueError("Disturbance configuration validation failed:\n" + "\n".join(f"  - {e}" for e in errors))
