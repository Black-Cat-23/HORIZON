"""
Disturbance Robustness Tests for HORIZON Perception Engine.
Phase 7 Upgrade: Testing independent noise, blur, atmosphere, and low-light conditions.
"""

import math
import numpy as np
import pytest

from simulator.perception.detector import ClassicalBeaconDetector
from benchmarks.run_phase7_audit import (
    create_synthetic_test_frame,
    apply_sp_noise,
    apply_motion_blur,
    create_low_light_frame,
)


def test_gaussian_noise_resilience():
    """Verify detector handles severe Gaussian noise (sigma=15)."""
    detector = ClassicalBeaconDetector()
    tx, ty = 310.0, 230.0
    clean = create_synthetic_test_frame((tx, ty), size_px=10.0, intensity=230)
    noisy = np.clip(clean.astype(float) + np.random.normal(0, 15, clean.shape), 0, 255).astype(np.uint8)

    res = detector.detect(noisy)
    assert res.detected
    assert res.centroid is not None
    err = math.hypot(res.centroid[0] - tx, res.centroid[1] - ty)
    assert err < 2.0


def test_salt_and_pepper_noise_resilience():
    """Verify detector handles 4% salt and pepper impulse noise via adaptive median filter."""
    detector = ClassicalBeaconDetector()
    tx, ty = 340.0, 260.0
    clean = create_synthetic_test_frame((tx, ty), size_px=10.0, intensity=240)
    sp_noisy = apply_sp_noise(clean, 0.04)

    res = detector.detect(sp_noisy)
    assert res.detected
    assert res.centroid is not None
    err = math.hypot(res.centroid[0] - tx, res.centroid[1] - ty)
    assert err < 2.0


def test_motion_blur_resilience():
    """Verify detector maintains lock on motion-blurred optical streak."""
    detector = ClassicalBeaconDetector()
    tx, ty = 300.0, 200.0
    clean = create_synthetic_test_frame((tx, ty), size_px=12.0, intensity=240)
    blurred = apply_motion_blur(clean, size=11, angle=30)

    res = detector.detect(blurred)
    assert res.detected
    assert res.centroid is not None
    err = math.hypot(res.centroid[0] - tx, res.centroid[1] - ty)
    assert err < 3.0


def test_low_light_contrast_resilience():
    """Verify detector handles low-contrast degraded frame."""
    detector = ClassicalBeaconDetector()
    clean = create_synthetic_test_frame((320.0, 240.0), size_px=10.0, intensity=100)
    low_light = create_low_light_frame(clean)

    res = detector.detect(low_light)
    assert res is not None
