"""
Tests for confidence calibration, probability mapping, and ECE calculation in association context.
"""

import numpy as np
import pytest
from simulator.perception.confidence_calibration import ConfidenceCalibrator


def test_confidence_calibration_monotonicity():
    calibrator = ConfidenceCalibrator()

    raw_scores = [0.1, 0.3, 0.5, 0.7, 0.9]
    cal_scores = [calibrator.calibrate(s) for s in raw_scores]

    # Monotonically increasing
    for i in range(len(cal_scores) - 1):
        assert cal_scores[i] < cal_scores[i + 1]


def test_confidence_calibration_ece_computation():
    calibrator = ConfidenceCalibrator()

    # Generate synthetic validation predictions
    np.random.seed(42)
    confidences = np.random.uniform(0.5, 1.0, size=100)
    labels = np.array([1 if c > 0.6 else 0 for c in confidences])

    metrics = calibrator.evaluate_reliability(confidences, labels, n_bins=5)

    assert 0.0 <= metrics.expected_calibration_error <= 1.0
    assert 0.0 <= metrics.brier_score <= 1.0
    assert len(metrics.bin_counts) == 5
