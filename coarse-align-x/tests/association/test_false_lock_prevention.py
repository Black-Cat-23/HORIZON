"""
Tests for false-lock defense against distractors, glints, slabs, and noise bursts.
"""

import numpy as np
import pytest
from simulator.perception.config import DetectorConfig
from simulator.perception.hybrid_detector import HybridBeaconDetector


def test_false_lock_defense_glint_distractor():
    detector = HybridBeaconDetector(DetectorConfig(perception_mode="HYBRID"))

    # Synthetic frame: beacon at (320, 240), bright horizontal glint at (380, 260)
    frame = np.full((480, 640), 20, dtype=np.uint8)
    y, x = np.ogrid[:480, :640]
    r2 = (x - 320) ** 2 + (y - 240) ** 2
    beacon = 220 * np.exp(-r2 / (2 * 4.0**2))
    frame = np.clip(frame + beacon, 0, 255).astype(np.uint8)

    # Add 1D bright glint (thin horizontal slit: 40px wide, 2px high)
    frame[259:261, 360:400] = 255

    res = detector.detect(
        frame,
        timestamp=0.0,
        estimator_prediction=(320.0, 240.0),
        prediction_covariance=np.diag([20.0, 20.0]),
    )

    assert res.detected is True
    assert res.centroid is not None
    # Must lock on beacon at (320, 240), NOT on glint at (380, 260)
    assert abs(res.centroid[0] - 320.0) < 5.0
    assert abs(res.centroid[1] - 240.0) < 5.0


def test_false_lock_defense_specular_slab():
    detector = HybridBeaconDetector(DetectorConfig(perception_mode="HYBRID"))

    # Synthetic frame: specular rectangular reflection slab only (no beacon)
    frame = np.full((480, 640), 20, dtype=np.uint8)
    frame[200:230, 300:360] = 255

    res = detector.detect(frame, timestamp=0.0)

    # Specular flat slab must be rejected
    assert res.detected is False or (res.agreement_state in ["REJECTED_LOW_CONFIDENCE", "NO_VALID_CANDIDATE"])
