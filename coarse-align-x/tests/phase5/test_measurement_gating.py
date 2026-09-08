"""
Phase 5 Gating, NIS, Covariance, Dropout & Closed-Loop Integration Tests
"""

import math
import numpy as np
import pytest
from tracking.estimation.imm_kalman import InteractingMultipleModelFilter
from tracking.estimation.kalman import TargetKalmanFilter, KalmanFilterConfig
from tracking.estimation.state import EstimatorStatus
from tracking.association.track import Track
from control.camera_controller import PATCameraController
from pat import PATModeManager, PATMode


def test_mahalanobis_gating_outlier_rejection():
    kf = TargetKalmanFilter(KalmanFilterConfig(gate_chi2_threshold=16.0))
    kf.initialize((100.0, 100.0), timestamp=0.0, initial_velocity=(10.0, 0.0))
    kf.update((100.5, 100.0), timestamp=0.05)

    # Extreme 500px outlier spike
    est_outlier = kf.update((600.0, 100.0), timestamp=0.10, confidence=0.3)
    assert est_outlier.filter_status == EstimatorStatus.REJECTED_MEASUREMENT
    assert est_outlier.estimated_x < 200.0


def test_nis_calculation_and_estimator_health():
    imm = InteractingMultipleModelFilter()
    imm.initialize((100.0, 100.0), timestamp=0.0)

    est = imm.step((102.0, 101.0), confidence=0.9, timestamp=0.05)
    assert est.nis >= 0.0
    assert est.estimator_health is not None
    assert est.estimator_health.nis == est.nis
    assert len(est.estimator_health.model_probabilities) == 3


def test_measurement_dropout_30_frames_prediction():
    track = Track(filter_type="IMM_ADAPTIVE_EKF")
    track.step((100.0, 100.0), confidence=1.0, timestamp=0.0)

    for i in range(1, 10):
        track.step((100.0 + i * 5.0, 100.0), confidence=1.0, timestamp=i * 0.05)

    # 30 frames measurement loss
    for i in range(10, 40):
        t = i * 0.05
        est = track.step(None, confidence=0.0, timestamp=t)
        assert est.filter_status == EstimatorStatus.PREDICTING
        assert est.consecutive_misses == (i - 9)
        assert est.estimated_x > 100.0


def test_high_speed_sinusoidal_tracking_closed_loop():
    track = Track(filter_type="IMM_ADAPTIVE_EKF")
    pat_ctrl = PATCameraController()
    pat_mgr = PATModeManager()

    track.step((320.0, 240.0), timestamp=0.0)
    
    # 50 frames high speed sinusoidal movement
    for i in range(1, 50):
        t = i * 0.05
        true_x = 320.0 + 150.0 * math.sin(2.0 * math.pi * 0.5 * t)
        true_y = 240.0 + 80.0 * math.cos(2.0 * math.pi * 0.5 * t)

        est = track.step((true_x, true_y), timestamp=t)
        assert est.estimated_x is not None
        assert not np.isnan(est.estimated_x)
        assert est.processing_time_ms < 5.0
