"""
Unit and integration tests for Phase 8 HybridBeaconDetector.
"""

import numpy as np
import pytest
from simulator.perception.config import DetectorConfig
from simulator.perception.hybrid_detector import HybridBeaconDetector


def test_hybrid_detector_initialization():
    cfg = DetectorConfig(perception_mode="HYBRID")
    detector = HybridBeaconDetector(cfg)

    assert detector.config.perception_mode == "HYBRID"
    assert detector.classical_detector is not None
    assert detector.neural_detector is not None


def test_hybrid_detector_clean_synthetic_frame():
    cfg = DetectorConfig(perception_mode="HYBRID")
    detector = HybridBeaconDetector(cfg)

    # Synthetic optical frame 640x480 with synthetic Gaussian beacon at (320, 240)
    frame = np.full((480, 640), 20, dtype=np.uint8)
    y, x = np.ogrid[:480, :640]
    r2 = (x - 320) ** 2 + (y - 240) ** 2
    beacon = 220 * np.exp(-r2 / (2 * 4.0**2))
    frame = np.clip(frame + beacon, 0, 255).astype(np.uint8)

    res = detector.detect(frame, timestamp=0.0)

    assert res.detector_source in ["CLASSICAL", "NEURAL", "HYBRID"]
    assert res.detected is True
    assert res.centroid is not None
    assert abs(res.centroid[0] - 320.0) < 3.0
    assert abs(res.centroid[1] - 240.0) < 3.0
    assert res.fused_confidence > 0.0
