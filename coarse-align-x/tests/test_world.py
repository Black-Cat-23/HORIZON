"""Tests for WorldRenderer."""

import numpy as np
import pytest
from simulator.world.beacon import Beacon
from simulator.world.world import WorldRenderer


class TestWorldRenderer:
    def test_dimensions_and_dtype(self):
        renderer = WorldRenderer(width=2000, height=2000, background_level=0)
        beacon = Beacon(size_px=10.0, intensity=255)
        frame = renderer.render(beacon, target_x=1000.0, target_y=1000.0)

        assert frame.shape == (2000, 2000)
        assert frame.dtype == np.uint8
        assert renderer.width == 2000
        assert renderer.height == 2000

    def test_background_level(self):
        renderer = WorldRenderer(width=100, height=100, background_level=50)
        beacon = Beacon(size_px=10.0, intensity=255)
        # Render target far away at (50, 50)
        frame = renderer.render(beacon, target_x=50.0, target_y=50.0)

        # Corner pixel should have background level 50
        assert frame[0, 0] == 50

    def test_target_visibility_flag(self):
        renderer = WorldRenderer(width=100, height=100, background_level=0)
        beacon = Beacon(size_px=10.0, intensity=255)

        # Render invisible target
        frame_invisible = renderer.render(beacon, target_x=50.0, target_y=50.0, visible=False)
        assert np.max(frame_invisible) == 0

        # Render visible target
        frame_visible = renderer.render(beacon, target_x=50.0, target_y=50.0, visible=True)
        assert np.max(frame_visible) == 255

    def test_invalid_parameters_rejected(self):
        with pytest.raises(ValueError, match="Dimensions must be positive"):
            WorldRenderer(width=0, height=100)
        with pytest.raises(ValueError, match="background_level must be 0–255"):
            WorldRenderer(width=100, height=100, background_level=-1)
