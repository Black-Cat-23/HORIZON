"""Tests for the configuration system."""

import pytest
import tempfile
from pathlib import Path

from simulator.core.config import (
    AppConfig,
    WorldConfig,
    CameraConfig,
    TargetConfig,
    TargetInitialPosition,
    SimulationConfig,
    TrajectoryConfig,
    StraightTrajectoryConfig,
    LoggingConfig,
    GroundTruthConfig,
    ConfigValidationError,
    validate_config,
    load_config,
)


# =============================================================================
# Default config validation
# =============================================================================

class TestDefaultConfig:
    """Test that default configuration is valid."""

    def test_default_config_validates(self):
        config = AppConfig()
        validate_config(config)  # Should not raise

    def test_default_world_dimensions(self):
        config = AppConfig()
        assert config.world.width == 2000
        assert config.world.height == 2000

    def test_default_camera_dimensions(self):
        config = AppConfig()
        assert config.camera.width == 640
        assert config.camera.height == 480

    def test_default_simulation_frequency(self):
        config = AppConfig()
        assert config.simulation.frequency_hz == 60.0

    def test_default_dt(self):
        config = AppConfig()
        assert abs(config.simulation.dt - 1.0 / 60.0) < 1e-12

    def test_default_total_frames(self):
        config = AppConfig()
        assert config.simulation.total_frames == 600  # 10s * 60Hz

    def test_default_target_size(self):
        config = AppConfig()
        assert config.target.size_px == 10

    def test_default_target_count(self):
        config = AppConfig()
        assert config.target.count == 1

    def test_default_seed(self):
        config = AppConfig()
        assert config.simulation.seed == 42

    def test_default_trajectory_type(self):
        config = AppConfig()
        assert config.trajectory.type == "straight"


# =============================================================================
# Invalid config rejection
# =============================================================================

class TestInvalidConfig:
    """Test that invalid configurations are rejected with clear errors."""

    def test_world_width_zero(self):
        config = AppConfig(world=WorldConfig(width=0))
        with pytest.raises(ConfigValidationError, match="world.width"):
            validate_config(config)

    def test_world_width_negative(self):
        config = AppConfig(world=WorldConfig(width=-100))
        with pytest.raises(ConfigValidationError, match="world.width"):
            validate_config(config)

    def test_world_height_zero(self):
        config = AppConfig(world=WorldConfig(height=0))
        with pytest.raises(ConfigValidationError, match="world.height"):
            validate_config(config)

    def test_background_level_negative(self):
        config = AppConfig(world=WorldConfig(background_level=-1))
        with pytest.raises(ConfigValidationError, match="background_level"):
            validate_config(config)

    def test_background_level_over_255(self):
        config = AppConfig(world=WorldConfig(background_level=256))
        with pytest.raises(ConfigValidationError, match="background_level"):
            validate_config(config)

    def test_camera_width_zero(self):
        config = AppConfig(camera=CameraConfig(width=0))
        with pytest.raises(ConfigValidationError, match="camera.width"):
            validate_config(config)

    def test_camera_height_zero(self):
        config = AppConfig(camera=CameraConfig(height=0))
        with pytest.raises(ConfigValidationError, match="camera.height"):
            validate_config(config)

    def test_camera_fov_h_zero(self):
        config = AppConfig(camera=CameraConfig(fov_horizontal_deg=0))
        with pytest.raises(ConfigValidationError, match="fov_horizontal"):
            validate_config(config)

    def test_camera_fov_v_zero(self):
        config = AppConfig(camera=CameraConfig(fov_vertical_deg=0))
        with pytest.raises(ConfigValidationError, match="fov_vertical"):
            validate_config(config)

    def test_camera_update_rate_zero(self):
        config = AppConfig(camera=CameraConfig(update_rate_hz=0))
        with pytest.raises(ConfigValidationError, match="update_rate"):
            validate_config(config)

    def test_target_count_not_one(self):
        config = AppConfig(target=TargetConfig(count=2))
        with pytest.raises(ConfigValidationError, match="target.count"):
            validate_config(config)

    def test_target_size_too_small(self):
        config = AppConfig(target=TargetConfig(size_px=4))
        with pytest.raises(ConfigValidationError, match="target.size_px"):
            validate_config(config)

    def test_target_size_too_large(self):
        config = AppConfig(target=TargetConfig(size_px=21))
        with pytest.raises(ConfigValidationError, match="target.size_px"):
            validate_config(config)

    def test_target_intensity_negative(self):
        config = AppConfig(target=TargetConfig(intensity=-1))
        with pytest.raises(ConfigValidationError, match="intensity"):
            validate_config(config)

    def test_simulation_frequency_zero(self):
        config = AppConfig(simulation=SimulationConfig(frequency_hz=0))
        with pytest.raises(ConfigValidationError, match="frequency_hz"):
            validate_config(config)

    def test_simulation_duration_zero(self):
        config = AppConfig(simulation=SimulationConfig(duration_seconds=0))
        with pytest.raises(ConfigValidationError, match="duration_seconds"):
            validate_config(config)

    def test_invalid_trajectory_type(self):
        config = AppConfig(
            trajectory=TrajectoryConfig(type="teleport")
        )
        with pytest.raises(ConfigValidationError, match="trajectory.type"):
            validate_config(config)

    def test_invalid_boundary_mode(self):
        config = AppConfig(
            trajectory=TrajectoryConfig(
                straight=StraightTrajectoryConfig(boundary_mode="warp")
            )
        )
        with pytest.raises(ConfigValidationError, match="boundary_mode"):
            validate_config(config)

    def test_multiple_errors_reported(self):
        """Multiple invalid values should all be reported at once."""
        config = AppConfig(
            world=WorldConfig(width=0, height=-1),
            target=TargetConfig(size_px=3),
        )
        with pytest.raises(ConfigValidationError) as exc_info:
            validate_config(config)
        error_msg = str(exc_info.value)
        assert "world.width" in error_msg
        assert "world.height" in error_msg
        assert "target.size_px" in error_msg


# =============================================================================
# Valid edge cases
# =============================================================================

class TestValidEdgeCases:
    """Test valid boundary values."""

    def test_target_size_min(self):
        config = AppConfig(target=TargetConfig(size_px=5))
        validate_config(config)  # Should not raise

    def test_target_size_max(self):
        config = AppConfig(target=TargetConfig(size_px=20))
        validate_config(config)  # Should not raise

    def test_background_level_zero(self):
        config = AppConfig(world=WorldConfig(background_level=0))
        validate_config(config)

    def test_background_level_255(self):
        config = AppConfig(world=WorldConfig(background_level=255))
        validate_config(config)


# =============================================================================
# YAML Loading
# =============================================================================

class TestYAMLLoading:
    """Test YAML configuration loading."""

    def test_load_default_yaml(self):
        config_path = Path(__file__).parent.parent / "configs" / "default.yaml"
        if config_path.exists():
            config = load_config(config_path)
            assert config.world.width == 2000
            assert config.simulation.seed == 42

    def test_load_nonexistent_file(self):
        with pytest.raises(FileNotFoundError):
            load_config("nonexistent.yaml")

    def test_load_minimal_yaml(self):
        """A minimal YAML with defaults should load and validate."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            f.write("world:\n  width: 2000\n  height: 2000\n")
            f.flush()
            config = load_config(f.name)
            assert config.world.width == 2000

    def test_load_empty_yaml(self):
        """An empty YAML file should produce valid defaults."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            f.write("")
            f.flush()
            config = load_config(f.name)
            validate_config(config)


# =============================================================================
# Config immutability
# =============================================================================

class TestConfigImmutability:
    """Test that config objects are frozen (immutable)."""

    def test_world_config_frozen(self):
        config = WorldConfig()
        with pytest.raises(AttributeError):
            config.width = 500  # type: ignore

    def test_simulation_config_frozen(self):
        config = SimulationConfig()
        with pytest.raises(AttributeError):
            config.frequency_hz = 30.0  # type: ignore
