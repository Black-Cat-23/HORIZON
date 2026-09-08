"""
HORIZON Disturbance Configuration
========================================
Typed configuration dataclasses and validation for the Phase 3 disturbance engine.
Enforces official SIH26169 parameters and bounds:
  - Gaussian noise sigma max: 20 pixels
  - Camera jitter max: ±20 pixels/frame
  - Platform motion max: ±20 pixels/frame
  - Atmospheric conditions: CLEAR, HAZE, FOG, RAIN, LOW_LIGHT
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Optional
from disturbance.turbulence import TurbulenceConfig


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

# Project engineering baseline parameters for atmospheric conditions
# All values are labelled PROJECT DEFAULT.
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
    """
    enabled: bool = False
    condition: str = "clear"  # OFFICIAL: clear, haze, fog, rain, low_light
    contrast_factor: Optional[float] = None     # PROJECT DEFAULT
    brightness_factor: Optional[float] = None   # PROJECT DEFAULT


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
    turbulence: TurbulenceConfig = field(default_factory=TurbulenceConfig)


# =============================================================================
# Validation Function
# =============================================================================

def validate_disturbance_config(config: DisturbanceConfig) -> None:
    """Validate all disturbance parameters against official SIH26169 limits.

    Raises:
        ValueError: If any parameter violates official specifications.
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

    if errors:
        raise ValueError("Disturbance configuration validation failed:\n" + "\n".join(f"  - {e}" for e in errors))
