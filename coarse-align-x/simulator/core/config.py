"""
HORIZON Configuration System
====================================
Typed configuration dataclasses with YAML loading and full validation.
All parameters from SIH26169 are validated on load — invalid values
produce clear, actionable error messages.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml

from simulator.disturbances.config import (
    AtmosphereConfig,
    CameraJitterConfig,
    DisturbanceConfig,
    GaussianNoiseConfig,
    PlatformMotionConfig,
    PoissonNoiseConfig,
    SaltPepperConfig,
    validate_disturbance_config,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Configuration Dataclasses
# =============================================================================

@dataclass(frozen=True)
class WorldConfig:
    """World/environment configuration."""
    width: int = 2000
    height: int = 2000
    background_level: int = 0


@dataclass(frozen=True)
class CameraConfig:
    """Virtual camera base parameters and actuator constraints.

    Initial Pointing:
        By default the camera starts at (0°, 0°) — boresight centered.
        Use ``initial_pan_deg`` / ``initial_tilt_deg`` for an explicit offset.
        Use ``max_initial_offset_deg > 0`` for a seed-derived random offset
        within ±max_initial_offset_deg on each axis.
        Explicit values take precedence over seed-derived values.

    Optical Parameters:
        pixel_pitch_um: Physical pixel size in micrometres. None = not modeled.
        exposure_ms: Sensor integration time (>0 ms). Enables motion blur when set.
        gain_db: Electronic gain in dB. 0.0 = unity. Range [-60, +60] dB.
    """
    width: int = 640
    height: int = 480
    fov_horizontal_deg: float = 4.0
    fov_vertical_deg: float = 3.0
    update_rate_hz: float = 30.0
    rate_limit_deg_s: float = 5.0
    # Initial camera pointing (all three default to 0.0 = boresight centered)
    initial_pan_deg: float = 0.0
    initial_tilt_deg: float = 0.0
    max_initial_offset_deg: float = 0.0  # 0 = always start at (0°,0°)
    # Optical sensor parameters (Phase 2)
    pixel_pitch_um: Optional[float] = None  # Physical pixel size (µm); None = not modeled
    exposure_ms: float = 1.0               # Integration time (ms); enables motion blur
    gain_db: float = 0.0                   # Electronic gain (dB); 0 = unity


@dataclass(frozen=True)
class TargetInitialPosition:
    """Optional explicit initial position. None values = determined by seed."""
    x: Optional[float] = None
    y: Optional[float] = None


@dataclass(frozen=True)
class TargetConfig:
    """Target/beacon configuration.

    PSF Parameters (Phase 2):
        psf_model: Beacon rendering model: 'box' (default) or 'gaussian'.
        psf_sigma_px: Gaussian sigma in pixels. Only used with psf_model='gaussian'.
        psf_background_adu: Constant background ADU added to PSF region.
    """
    count: int = 1
    size_px: int = 10
    intensity: int = 255
    initial_position: TargetInitialPosition = field(
        default_factory=TargetInitialPosition
    )
    # PSF rendering model (Phase 2)
    psf_model: str = "box"              # 'box' (legacy) or 'gaussian'
    psf_sigma_px: float = 1.5           # Gaussian sigma (px); only used with psf_model='gaussian'
    psf_background_adu: float = 0.0     # Background pedestal (ADU)


@dataclass(frozen=True)
class SimulationConfig:
    """Core simulation timing configuration."""
    frequency_hz: float = 60.0
    seed: int = 42
    duration_seconds: float = 10.0

    @property
    def dt(self) -> float:
        """Fixed simulation timestep in seconds."""
        return 1.0 / self.frequency_hz

    @property
    def total_frames(self) -> int:
        """Total number of simulation frames for the configured duration."""
        return int(self.duration_seconds * self.frequency_hz)


@dataclass(frozen=True)
class StraightTrajectoryConfig:
    velocity_x: float = 80.0
    velocity_y: float = 60.0
    boundary_mode: str = "bounce"


@dataclass(frozen=True)
class CircularTrajectoryConfig:
    center_x: float = 1000.0
    center_y: float = 1000.0
    radius: float = 300.0
    angular_velocity: float = 1.0
    phase: float = 0.0


@dataclass(frozen=True)
class FigureEightTrajectoryConfig:
    center_x: float = 1000.0
    center_y: float = 1000.0
    amplitude_x: float = 400.0
    amplitude_y: float = 300.0
    angular_velocity: float = 0.8
    phase: float = 0.0


@dataclass(frozen=True)
class RandomTrajectoryConfig:
    max_speed: float = 150.0
    max_acceleration: float = 200.0
    acceleration_change_rate: float = 5.0
    boundary_mode: str = "bounce"


@dataclass(frozen=True)
class SpiralTrajectoryConfig:
    center_x: float = 1000.0
    center_y: float = 1000.0
    initial_radius: float = 50.0
    expansion_rate: float = 20.0
    angular_velocity: float = 1.5
    phase: float = 0.0


@dataclass(frozen=True)
class SinusoidalTrajectoryConfig:
    center_x: float = 1000.0
    center_y: float = 1000.0
    amplitude_x: float = 400.0
    amplitude_y: float = 300.0
    frequency_x: float = 0.5
    frequency_y: float = 0.7
    phase_x: float = 0.0
    phase_y: float = 0.0


VALID_TRAJECTORY_TYPES = {
    "straight", "circular", "figure8", "random", "spiral", "sinusoidal"
}

VALID_BOUNDARY_MODES = {"bounce", "clamp"}


@dataclass(frozen=True)
class TrajectoryConfig:
    """Trajectory selection and per-type parameters."""
    type: str = "straight"
    straight: StraightTrajectoryConfig = field(
        default_factory=StraightTrajectoryConfig
    )
    circular: CircularTrajectoryConfig = field(
        default_factory=CircularTrajectoryConfig
    )
    figure8: FigureEightTrajectoryConfig = field(
        default_factory=FigureEightTrajectoryConfig
    )
    random: RandomTrajectoryConfig = field(
        default_factory=RandomTrajectoryConfig
    )
    spiral: SpiralTrajectoryConfig = field(
        default_factory=SpiralTrajectoryConfig
    )
    sinusoidal: SinusoidalTrajectoryConfig = field(
        default_factory=SinusoidalTrajectoryConfig
    )


@dataclass(frozen=True)
class LoggingConfig:
    enabled: bool = True
    level: str = "INFO"
    output_directory: str = "logs"


@dataclass(frozen=True)
class GroundTruthConfig:
    enabled: bool = True
    format: str = "csv"
    output_directory: str = "data/ground_truth"


@dataclass(frozen=True)
class AppConfig:
    """Root application configuration — aggregates all sub-configs."""
    world: WorldConfig = field(default_factory=WorldConfig)
    camera: CameraConfig = field(default_factory=CameraConfig)
    target: TargetConfig = field(default_factory=TargetConfig)
    simulation: SimulationConfig = field(default_factory=SimulationConfig)
    trajectory: TrajectoryConfig = field(default_factory=TrajectoryConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    ground_truth: GroundTruthConfig = field(default_factory=GroundTruthConfig)
    disturbance: DisturbanceConfig = field(default_factory=DisturbanceConfig)


# =============================================================================
# Validation
# =============================================================================

class ConfigValidationError(Exception):
    """Raised when configuration validation fails."""
    pass


def validate_config(config: AppConfig) -> None:
    """Validate all configuration parameters. Raises ConfigValidationError
    with a clear message for any invalid value."""
    errors: list[str] = []

    # World
    if config.world.width <= 0:
        errors.append(f"world.width must be > 0, got {config.world.width}")
    if config.world.height <= 0:
        errors.append(f"world.height must be > 0, got {config.world.height}")
    if not (0 <= config.world.background_level <= 255):
        errors.append(
            f"world.background_level must be 0–255, "
            f"got {config.world.background_level}"
        )

    # Camera
    if config.camera.width <= 0:
        errors.append(f"camera.width must be > 0, got {config.camera.width}")
    if config.camera.height <= 0:
        errors.append(f"camera.height must be > 0, got {config.camera.height}")
    if config.camera.fov_horizontal_deg <= 0:
        errors.append(
            f"camera.fov_horizontal_deg must be > 0, "
            f"got {config.camera.fov_horizontal_deg}"
        )
    if config.camera.fov_vertical_deg <= 0:
        errors.append(
            f"camera.fov_vertical_deg must be > 0, "
            f"got {config.camera.fov_vertical_deg}"
        )
    if config.camera.update_rate_hz <= 0:
        errors.append(
            f"camera.update_rate_hz must be > 0, "
            f"got {config.camera.update_rate_hz}"
        )
    if config.camera.rate_limit_deg_s <= 0:
        errors.append(
            f"camera.rate_limit_deg_s must be > 0, "
            f"got {config.camera.rate_limit_deg_s}"
        )
    if config.camera.max_initial_offset_deg < 0:
        errors.append(
            f"camera.max_initial_offset_deg must be >= 0, "
            f"got {config.camera.max_initial_offset_deg}"
        )
    if config.camera.exposure_ms <= 0:
        errors.append(
            f"camera.exposure_ms must be > 0, got {config.camera.exposure_ms}"
        )
    if not (-60.0 <= config.camera.gain_db <= 60.0):
        errors.append(
            f"camera.gain_db must be in [-60, +60] dB, got {config.camera.gain_db}"
        )
    if config.camera.pixel_pitch_um is not None and config.camera.pixel_pitch_um <= 0:
        errors.append(
            f"camera.pixel_pitch_um must be > 0 when set, got {config.camera.pixel_pitch_um}"
        )

    # Target
    if config.target.count != 1:
        errors.append(
            f"target.count must be 1 in Phase 1, got {config.target.count}"
        )
    if not (5 <= config.target.size_px <= 20):
        errors.append(
            f"target.size_px must be 5–20, got {config.target.size_px}"
        )
    if not (0 <= config.target.intensity <= 255):
        errors.append(
            f"target.intensity must be 0–255, got {config.target.intensity}"
        )
    if config.target.psf_model not in ("box", "gaussian"):
        errors.append(
            f"target.psf_model must be 'box' or 'gaussian', got '{config.target.psf_model}'"
        )
    if config.target.psf_sigma_px < 0:
        errors.append(
            f"target.psf_sigma_px must be >= 0, got {config.target.psf_sigma_px}"
        )
    if config.target.psf_background_adu < 0:
        errors.append(
            f"target.psf_background_adu must be >= 0, got {config.target.psf_background_adu}"
        )

    # Simulation
    if config.simulation.frequency_hz <= 0:
        errors.append(
            f"simulation.frequency_hz must be > 0, "
            f"got {config.simulation.frequency_hz}"
        )
    if config.simulation.duration_seconds <= 0:
        errors.append(
            f"simulation.duration_seconds must be > 0, "
            f"got {config.simulation.duration_seconds}"
        )

    # Trajectory
    if config.trajectory.type not in VALID_TRAJECTORY_TYPES:
        errors.append(
            f"trajectory.type must be one of {VALID_TRAJECTORY_TYPES}, "
            f"got '{config.trajectory.type}'"
        )

    # Boundary mode validation for straight and random
    if config.trajectory.straight.boundary_mode not in VALID_BOUNDARY_MODES:
        errors.append(
            f"trajectory.straight.boundary_mode must be one of "
            f"{VALID_BOUNDARY_MODES}, "
            f"got '{config.trajectory.straight.boundary_mode}'"
        )
    if config.trajectory.random.boundary_mode not in VALID_BOUNDARY_MODES:
        errors.append(
            f"trajectory.random.boundary_mode must be one of "
            f"{VALID_BOUNDARY_MODES}, "
            f"got '{config.trajectory.random.boundary_mode}'"
        )

    # Circular radius validation
    if config.trajectory.circular.radius <= 0:
        errors.append(
            f"trajectory.circular.radius must be > 0, "
            f"got {config.trajectory.circular.radius}"
        )

    # Random motion constraints
    if config.trajectory.random.max_speed <= 0:
        errors.append(
            f"trajectory.random.max_speed must be > 0, "
            f"got {config.trajectory.random.max_speed}"
        )
    if config.trajectory.random.max_acceleration <= 0:
        errors.append(
            f"trajectory.random.max_acceleration must be > 0, "
            f"got {config.trajectory.random.max_acceleration}"
        )

    # Ground truth format
    if config.ground_truth.format not in {"csv", "json"}:
        errors.append(
            f"ground_truth.format must be 'csv' or 'json', "
            f"got '{config.ground_truth.format}'"
        )

    # Logging level
    valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR"}
    if config.logging.level not in valid_levels:
        errors.append(
            f"logging.level must be one of {valid_levels}, "
            f"got '{config.logging.level}'"
        )

    # Disturbance validation (Phase 3)
    try:
        validate_disturbance_config(config.disturbance)
    except ValueError as ve:
        errors.append(str(ve))

    if errors:
        error_msg = "Configuration validation failed:\n" + "\n".join(
            f"  - {e}" for e in errors
        )
        raise ConfigValidationError(error_msg)

    logger.info("Configuration validated successfully.")


# =============================================================================
# YAML Loading
# =============================================================================

def _build_target_initial_position(raw: dict | None) -> TargetInitialPosition:
    """Build TargetInitialPosition from raw dict, handling None values."""
    if raw is None:
        return TargetInitialPosition()
    return TargetInitialPosition(
        x=raw.get("x"),
        y=raw.get("y"),
    )


def _build_config_from_dict(data: dict) -> AppConfig:
    """Build a typed AppConfig from a raw dictionary (parsed YAML)."""
    world_raw = data.get("world", {})
    camera_raw = data.get("camera", {})
    target_raw = data.get("target", {})
    sim_raw = data.get("simulation", {})
    traj_raw = data.get("trajectory", {})
    log_raw = data.get("logging", {})
    gt_raw = data.get("ground_truth", {})

    # Build initial position separately to handle None
    initial_pos = _build_target_initial_position(
        target_raw.get("initial_position")
    )

    # Build target config without initial_position, then override
    target_fields = {k: v for k, v in target_raw.items()
                     if k != "initial_position"}

    return AppConfig(
        world=WorldConfig(**world_raw) if world_raw else WorldConfig(),
        camera=CameraConfig(**camera_raw) if camera_raw else CameraConfig(),
        target=TargetConfig(
            **target_fields,
            initial_position=initial_pos,
        ) if target_fields else TargetConfig(initial_position=initial_pos),
        simulation=SimulationConfig(**sim_raw) if sim_raw else SimulationConfig(),
        trajectory=TrajectoryConfig(
            type=traj_raw.get("type", "straight"),
            straight=StraightTrajectoryConfig(
                **traj_raw.get("straight", {})
            ),
            circular=CircularTrajectoryConfig(
                **traj_raw.get("circular", {})
            ),
            figure8=FigureEightTrajectoryConfig(
                **traj_raw.get("figure8", {})
            ),
            random=RandomTrajectoryConfig(
                **traj_raw.get("random", {})
            ),
            spiral=SpiralTrajectoryConfig(
                **traj_raw.get("spiral", {})
            ),
            sinusoidal=SinusoidalTrajectoryConfig(
                **traj_raw.get("sinusoidal", {})
            ),
        ) if traj_raw else TrajectoryConfig(),
        logging=LoggingConfig(**log_raw) if log_raw else LoggingConfig(),
        ground_truth=GroundTruthConfig(
            **gt_raw
        ) if gt_raw else GroundTruthConfig(),
        disturbance=DisturbanceConfig(
            enabled=data.get("disturbance", {}).get("enabled", True),
            salt_pepper=SaltPepperConfig(**data.get("disturbance", {}).get("salt_pepper", {})) if "salt_pepper" in data.get("disturbance", {}) else SaltPepperConfig(),
            gaussian=GaussianNoiseConfig(**data.get("disturbance", {}).get("gaussian", {})) if "gaussian" in data.get("disturbance", {}) else GaussianNoiseConfig(),
            poisson=PoissonNoiseConfig(**data.get("disturbance", {}).get("poisson", {})) if "poisson" in data.get("disturbance", {}) else PoissonNoiseConfig(),
            camera_jitter=CameraJitterConfig(**data.get("disturbance", {}).get("camera_jitter", {})) if "camera_jitter" in data.get("disturbance", {}) else CameraJitterConfig(),
            platform_motion=PlatformMotionConfig(**data.get("disturbance", {}).get("platform_motion", {})) if "platform_motion" in data.get("disturbance", {}) else PlatformMotionConfig(),
            atmosphere=AtmosphereConfig(**data.get("disturbance", {}).get("atmosphere", {})) if "atmosphere" in data.get("disturbance", {}) else AtmosphereConfig(),
        ) if "disturbance" in data else DisturbanceConfig(),
    )


def load_config(config_path: Path | str) -> AppConfig:
    """Load and validate configuration from a YAML file.

    Args:
        config_path: Path to the YAML configuration file.

    Returns:
        Validated AppConfig instance.

    Raises:
        FileNotFoundError: If the config file does not exist.
        ConfigValidationError: If any parameter is invalid.
    """
    config_path = Path(config_path)
    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    with open(config_path, "r", encoding="utf-8") as f:
        raw_data = yaml.safe_load(f)

    if raw_data is None:
        raw_data = {}

    config = _build_config_from_dict(raw_data)
    validate_config(config)

    logger.info("Configuration loaded from %s", config_path)
    return config
