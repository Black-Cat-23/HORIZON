"""
False Target & Distractor Defense Tests for HORIZON Perception Engines.
Phase 7 Upgrade: Defense against glints, specular slabs, and noise blobs.
"""

import numpy as np
import pytest

from simulator.perception.detector import ClassicalBeaconDetector
from benchmarks.run_phase7_audit import apply_sp_noise


def test_reject_all_black_frame():
    """Verify clean rejection of black/empty frames without false triggers."""
    detector = ClassicalBeaconDetector()
    black_frame = np.full((480, 640), 20, dtype=np.uint8)
    res = detector.detect(black_frame)
    assert not res.detected
    assert res.centroid is None
    assert res.confidence == 0.0


def test_reject_specular_slab():
    """Verify non-Gaussian rectangular specular slab is rejected as a valid beacon candidate."""
    detector = ClassicalBeaconDetector()
    frame = np.full((480, 640), 20, dtype=np.uint8)
    # Flat rectangular 50x50 block with sharp non-Gaussian edges
    frame[200:250, 280:330] = 240

    res = detector.detect(frame)
    # Candidate should fail Gaussian radial consistency or compactness gate
    assert not res.detected or res.confidence < 0.40


def test_reject_pure_impulse_noise():
    """Verify rejection of pure impulse noise field without true optical beacon."""
    detector = ClassicalBeaconDetector()
    frame = np.full((480, 640), 20, dtype=np.uint8)
    noisy_frame = apply_sp_noise(frame, 0.03)

    res = detector.detect(noisy_frame)
    assert not res.detected
