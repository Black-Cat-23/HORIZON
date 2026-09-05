"""
Formal V&V: Camera Viewport, Target Projection, Subpixel Fidelity, and Size Limits.
Sections 14, 15, 16, 17 of Phase 2 Formal Verification & Validation specification.
"""

import numpy as np
import pytest
from simulator.camera.camera import VirtualCamera
from simulator.camera.gimbal import CameraGimbal
from simulator.camera.intrinsics import CameraIntrinsics
from simulator.world.beacon import Beacon
from simulator.world.world import WorldRenderer


class TestViewportVerification:
    """Section 14: Viewport Verification."""

    @pytest.fixture
    def setup_sim(self):
        renderer = WorldRenderer(width=2000, height=2000, background_level=0)
        beacon = Beacon(size_px=10.0, intensity=255)
        camera = VirtualCamera(world_width=2000, world_height=2000)
        return renderer, beacon, camera

    def test_viewport_dimensions_dtype_and_channel(self, setup_sim):
        renderer, beacon, camera = setup_sim
        world_frame = renderer.render(beacon, target_x=1000.0, target_y=1000.0)

        obs = camera.extract_viewport(world_frame)

        # Must be exactly shape (480, 640), uint8, 2D single channel
        assert obs.shape == (480, 640)
        assert obs.dtype == np.uint8
        assert len(obs.shape) == 2

    def test_viewport_is_not_resize(self, setup_sim):
        renderer, beacon, camera = setup_sim

        # Place target at (1000, 1000). On a simple resize of 2000x2000 -> 640x480,
        # a 10x10 target would shrink to ~3x2 pixels!
        # In a real optical crop, the 10x10 target maintains its exact 10x10 pixel dimensions!
        world_frame = renderer.render(beacon, target_x=1000.0, target_y=1000.0)
        obs = camera.extract_viewport(world_frame)

        # Count bright pixels in target
        target_pixels = np.sum(obs > 200)
        # 10x10 square has 100 pixels
        assert 90 <= target_pixels <= 110, f"Target shrunk or distorted! pixel count = {target_pixels}"

    def test_camera_movement_changes_observation(self, setup_sim):
        renderer, beacon, camera = setup_sim
        world_frame = renderer.render(beacon, target_x=1000.0, target_y=1000.0)

        # Center camera: target is at center of viewport
        obs_center = camera.extract_viewport(world_frame).copy()

        # Pan camera right by 1.0 deg (moves boresight right, target shifts left in image)
        camera.gimbal.reset(pan_deg=1.0, tilt_deg=0.0)
        obs_panned = camera.extract_viewport(world_frame)

        assert not np.array_equal(obs_center, obs_panned)


class TestTargetProjectionVerification:
    """Section 15: Target Projection Verification across known angles."""

    def test_target_projection_and_visibility_limits(self):
        camera = VirtualCamera(world_width=2000, world_height=2000)

        # 1. Target exactly at center (1000, 1000) -> u=320, v=240, visible
        _, _, u, v, visible = camera.project_target(1000.0, 1000.0)
        assert abs(u - 320.0) < 1e-6
        assert abs(v - 240.0) < 1e-6
        assert visible is True

        # 2. Target at horizontal boundary (dx = +320 -> u = 640)
        _, _, u, v, visible = camera.project_target(1320.0, 1000.0)
        assert abs(u - 640.0) < 1e-6
        assert abs(v - 240.0) < 1e-6
        assert visible is True

        # 3. Target outside FOV (dx = +350 -> u = 670, outside 640)
        _, _, u, v, visible = camera.project_target(1350.0, 1000.0)
        assert u > 640.0
        assert visible is False


class TestSubpixelAndSizeVerification:
    """Sections 16 & 17: Subpixel Information & Target Size Limits."""

    def test_subpixel_target_coordinates_preserved(self):
        camera = VirtualCamera(world_width=2000, world_height=2000)

        # Fractional target positions
        frac_positions = [1000.1, 1000.5, 1000.9]
        u_vals = []
        for x_frac in frac_positions:
            _, _, u, _, _ = camera.project_target(x_frac, 1000.0)
            u_vals.append(u)

        # Verify differences between fractional steps are strictly preserved
        assert abs((u_vals[1] - u_vals[0]) - 0.4) < 1e-6
        assert abs((u_vals[2] - u_vals[1]) - 0.4) < 1e-6

    def test_target_size_limits_accepted_and_rejected(self):
        # Valid sizes: 5, 10, 20
        b5 = Beacon(size_px=5.0)
        assert b5.size_px == 5.0
        b10 = Beacon(size_px=10.0)
        assert b10.size_px == 10.0
        b20 = Beacon(size_px=20.0)
        assert b20.size_px == 20.0

        # Invalid sizes: 4.9, 20.1 rejected
        with pytest.raises(ValueError, match="Beacon size must be in range"):
            Beacon(size_px=4.9)
        with pytest.raises(ValueError, match="Beacon size must be in range"):
            Beacon(size_px=20.1)
