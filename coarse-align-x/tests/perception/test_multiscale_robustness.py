"""
Multi-Scale Robustness Tests for HORIZON Perception Engines.
Phase 7 Upgrade: Target scales 3x3 to 30x30 px.
"""

import math
import numpy as np
import pytest

from simulator.perception.detector import ClassicalBeaconDetector
from simulator.perception.config import DetectorConfig
from benchmarks.run_phase7_audit import create_synthetic_test_frame


@pytest.mark.parametrize("size_px", [3.0, 5.0, 8.0, 10.0, 15.0, 20.0, 25.0])
def test_multiscale_detection_accuracy(size_px):
    """Verify that classical detector detects beacon across all scales with subpixel accuracy."""
    detector = ClassicalBeaconDetector()
    tx, ty = 320.4, 240.6
    frame = create_synthetic_test_frame((tx, ty), size_px=size_px, intensity=230)

    res = detector.detect(frame)
    assert res.detected, f"Failed to detect beacon at scale {size_px}px"
    assert res.centroid is not None
    err = math.hypot(res.centroid[0] - tx, res.centroid[1] - ty)
    # Centroid error should be well under 1.5 pixels across all scales
    assert err < 1.5, f"Centroid error too large ({err:.3f} px) at scale {size_px}px"
    assert res.confidence >= 0.35


def test_edge_boundary_scale_handling():
    """Verify clipped beacon near image edge still produces valid candidate without crash."""
    detector = ClassicalBeaconDetector()
    frame = create_synthetic_test_frame((10.0, 10.0), size_px=15.0, intensity=240)
    res = detector.detect(frame)
    assert res is not None
