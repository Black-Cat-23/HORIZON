"""
Tests for detector disagreement handling, fallback states, and decision trace explanations.
"""

import numpy as np
import pytest
from simulator.perception.config import DetectorConfig
from simulator.perception.hybrid_detector import HybridBeaconDetector


def test_detector_disagreement_explanation_and_fallback():
    detector = HybridBeaconDetector(DetectorConfig(perception_mode="HYBRID"))

    # Frame with faint target that classical might see or reject
    frame = np.full((480, 640), 25, dtype=np.uint8)
    y, x = np.ogrid[:480, :640]
    r2 = (x - 200) ** 2 + (y - 150) ** 2
    beacon = 180 * np.exp(-r2 / (2 * 5.0**2))
    frame = np.clip(frame + beacon, 0, 255).astype(np.uint8)

    res = detector.detect(frame, timestamp=0.0)

    # Explanation must be non-empty and describe decision
    assert res.decision_reason != ""
    assert res.agreement_state in [
        "AGREEMENT",
        "PARTIAL_AGREEMENT",
        "DISAGREEMENT",
        "SINGLE_SOURCE_CLASSICAL",
        "SINGLE_SOURCE_NEURAL",
        "REJECTED_LOW_CONFIDENCE",
        "NO_VALID_CANDIDATE",
    ]
    if res.detected:
        assert res.centroid is not None
        assert abs(res.centroid[0] - 200.0) < 5.0
        assert abs(res.centroid[1] - 150.0) < 5.0
