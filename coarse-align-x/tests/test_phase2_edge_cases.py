"""
Formal V&V: Phase 2 Edge Cases and Robustness Verification.
Section 24 of Phase 2 Formal Verification & Validation specification.
"""

import numpy as np
import pytest
from simulator.camera.camera import VirtualCamera
from simulator.camera.gimbal import CameraGimbal
from simulator.camera.intrinsics import CameraIntrinsics
from simulator.core.config import (
    AppConfig,
    CameraConfig,
    ConfigValidationError,
    SimulationConfig,
    TargetConfig,
    WorldConfig,
    validate_config,
)
from simulator.core.simulation import SimulationEngine
from simulator.world.beacon import Beacon
from simulator.world.world import WorldRenderer


class TestPhase2EdgeCases:
    """Section 24: Exhaustive Edge-Case Testing."""

    def test_target_at_world_origin(self):
        renderer = WorldRenderer(width=2000, height=2000)
        beacon = Beacon(size_px=10.0)
        frame = renderer.render(beacon, target_x=0.0, target_y=0.0)
        assert frame[0, 0] > 0

    def test_target_at_world_far_corner(self):
        renderer = WorldRenderer(width=2000, height=2000)
        beacon = Beacon(size_px=10.0)
        frame = renderer.render(beacon, target_x=1999.0, target_y=1999.0)
        assert frame[1999, 1999] > 0

    def test_camera_near_world_boundary_padding(self):
        renderer = WorldRenderer(width=2000, height=2000)
        beacon = Beacon(size_px=10.0)
        world_frame = renderer.render(beacon, target_x=100.0, target_y=100.0)

        camera = VirtualCamera(world_width=2000, world_height=2000)
        # Pan camera far left so viewport extends beyond world x=0
        camera.gimbal.reset(pan_deg=-5.0, tilt_deg=-5.0)

        obs = camera.extract_viewport(world_frame)
        assert obs.shape == (480, 640)
        assert obs.dtype == np.uint8

    def test_extreme_camera_rate_commands(self):
        gimbal = CameraGimbal(rate_limit_deg_s=5.0)
        # Extreme command +/- 1000 deg/s
        gimbal.set_rate_command(1000.0, -1000.0)
        gimbal.step(0.1)

        assert abs(gimbal.actual_pan_rate - 5.0) < 1e-9
        assert abs(gimbal.actual_tilt_rate - (-5.0)) < 1e-9

    def test_repeated_start_reset_cycles(self):
        config = AppConfig(
            simulation=SimulationConfig(frequency_hz=60.0, duration_seconds=0.2)
        )
        engine = SimulationEngine(config)

        for cycle in range(5):
            engine.initialize()
            engine.run()
            assert engine.clock.current_frame == 12
            engine.reset()
            assert engine.clock.current_frame == 0

    def test_invalid_camera_configurations_rejected(self):
        with pytest.raises(ConfigValidationError, match="camera.fov_horizontal"):
            validate_config(AppConfig(camera=CameraConfig(fov_horizontal_deg=0.0)))

        with pytest.raises(ConfigValidationError, match="camera.width"):
            validate_config(AppConfig(camera=CameraConfig(width=0)))

        with pytest.raises(ConfigValidationError, match="camera.rate_limit_deg_s"):
            validate_config(AppConfig(camera=CameraConfig(rate_limit_deg_s=-5.0)))

    def test_invalid_world_and_target_size_rejected(self):
        with pytest.raises(ConfigValidationError, match="world.width"):
            validate_config(AppConfig(world=WorldConfig(width=0)))

        with pytest.raises(ConfigValidationError, match="target.size_px"):
            validate_config(AppConfig(target=TargetConfig(size_px=3)))
