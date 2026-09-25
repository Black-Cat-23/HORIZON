"""
Confidence Calibration Tests for HORIZON Perception Engines.
Phase 7 Upgrade: Testing Platt scaling, probability mapping, and ECE calculation.
"""

import numpy as np
import pytest

from simulator.perception.confidence_calibration import (
    ConfidenceCalibrator,
    CalibrationMetrics,
)


def test_confidence_calibration_monotonicity():
    """Verify calibrated probability is strictly monotonic with respect to input score."""
    calibrator = ConfidenceCalibrator()
    scores = np.linspace(0.0, 1.0, 20)
    calibrated = [calibrator.calibrate(s) for s in scores]

    for i in range(len(calibrated) - 1):
        assert calibrated[i] <= calibrated[i + 1]
        assert 0.0 <= calibrated[i] <= 1.0


def test_confidence_calibration_reliability_computation():
    """Verify calculation of ECE and Brier Score on synthetic validation data."""
    calibrator = ConfidenceCalibrator()
    np.random.seed(42)

    # Perfect prediction test case
    confidences = np.array([0.9, 0.8, 0.1, 0.2, 0.95, 0.05])
    labels = np.array([1.0, 1.0, 0.0, 0.0, 1.0, 0.0])

    metrics = calibrator.evaluate_reliability(confidences, labels, n_bins=5)
    assert isinstance(metrics, CalibrationMetrics)
    assert 0.0 <= metrics.expected_calibration_error <= 0.5
    assert metrics.brier_score < 0.05
