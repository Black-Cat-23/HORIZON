"""Tests for Beacon model and subpixel rasterization."""

import numpy as np
import pytest
from simulator.world.beacon import Beacon


class TestBeacon:
    def test_default_construction(self):
        b = Beacon()
        assert b.target_id == 1
        assert b.size_px == 10.0
        assert b.intensity == 255
        assert b.shape == "square"

    def test_valid_size_limits(self):
        b_min = Beacon(size_px=5.0)
        assert b_min.size_px == 5.0
        b_max = Beacon(size_px=20.0)
        assert b_max.size_px == 20.0

    def test_invalid_sizes_rejected(self):
        with pytest.raises(ValueError, match="Beacon size must be in range"):
            Beacon(size_px=4.9)
        with pytest.raises(ValueError, match="Beacon size must be in range"):
            Beacon(size_px=20.1)

    def test_invalid_intensity_rejected(self):
        with pytest.raises(ValueError, match="Beacon intensity must be in range"):
            Beacon(intensity=-1)
        with pytest.raises(ValueError, match="Beacon intensity must be in range"):
            Beacon(intensity=256)

    def test_invalid_shape_rejected(self):
        with pytest.raises(ValueError, match="Only 'square' shape supported"):
            Beacon(shape="circle")

    def test_rasterization_exact_integer_alignment(self):
        # Place a 10x10 beacon at center (50, 50) on a 100x100 black frame
        frame = np.zeros((100, 100), dtype=np.uint8)
        b = Beacon(size_px=10.0, intensity=255)
        b.render_into(frame, x=50.0, y=50.0)

        # Pixels [45:55, 45:55] should be fully white (255)
        beacon_region = frame[45:55, 45:55]
        assert np.all(beacon_region == 255)

        # Surrounding pixels should be 0
        assert frame[44, 50] == 0
        assert frame[55, 50] == 0
        assert frame[50, 44] == 0
        assert frame[50, 55] == 0

    def test_subpixel_rasterization_area_conservation(self):
        # A 10x10 beacon has total area 100.0 px^2
        # Moving by fractional offset (e.g. 50.3, 50.7) should conserve total integrated energy
        frame = np.zeros((100, 100), dtype=np.uint8)
        b = Beacon(size_px=10.0, intensity=255)
        b.render_into(frame, x=50.3, y=50.7)

        total_intensity = np.sum(frame)
        # Expected total intensity = 100.0 px * 255 = 25500
        # Allow slight integer discretization error across ~4 boundary pixels
        assert abs(total_intensity - (100.0 * 255)) < 150
