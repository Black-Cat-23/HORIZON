"""
Unit tests for Raster and Spiral search strategies.
HORIZON Phase 6
"""

import pytest
from pat.search.raster import RasterSearchStrategy
from pat.search.spiral import SpiralSearchStrategy


def test_raster_search_generation():
    raster = RasterSearchStrategy(scan_width_deg=4.0, scan_height_deg=3.0, scan_speed_deg_s=2.0)
    raster.reset(center_pan_deg=0.0, center_tilt_deg=0.0)

    cmd_pan, cmd_tilt = raster.next_command(dt=0.1, current_pan_deg=0.0, current_tilt_deg=0.0)
    assert cmd_pan > 0.0  # Moving right
    assert cmd_tilt == 0.0


def test_spiral_search_generation():
    spiral = SpiralSearchStrategy(initial_radius_deg=0.2, radius_step_deg=0.4, max_radius_deg=2.0)
    spiral.reset(center_pan_deg=0.0, center_tilt_deg=0.0)

    cmd_pan, cmd_tilt = spiral.next_command(dt=0.1, current_pan_deg=0.0, current_tilt_deg=0.0)
    assert abs(cmd_pan) > 0.0 or abs(cmd_tilt) > 0.0

    history = spiral.get_trajectory_history()
    assert len(history) > 5
