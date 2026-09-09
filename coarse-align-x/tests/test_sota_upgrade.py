"""
Unit and Integration Tests for Phase 12 SOTA Tracking & Control Upgrade.
Verifies Fourier-GMM perception, IMM-EKF estimation, and ADRC control.
"""

import numpy as np
import pytest

from simulator.perception.sota_detector import SOTABeaconDetector
from simulator.perception.config import DetectorConfig, CentroidConfig
from tracking.estimation.imm_kalman import InteractingMultipleModelFilter
from tracking.estimation.kalman import KalmanFilterConfig
from control.adrc_controller import ADRCAxisController, DualAxisADRCController
from control.camera_controller import PATCameraController
from tracking.association.track import Track
from pat.state import PATMode, PATState


class TestSOTABeaconDetector:
    def test_detection_on_synthetic_frame(self):
        detector = SOTABeaconDetector()
        frame = np.zeros((480, 640), dtype=np.uint8)

        # Draw a synthetic Gaussian beacon at (320, 240)
        yy, xx = np.ogrid[:480, :640]
        dist_sq = (xx - 320)**2 + (yy - 240)**2
        frame = (255 * np.exp(-dist_sq / (2 * 5.0**2))).astype(np.uint8)

        res = detector.detect(frame, timestamp=1.0)
        assert res.detected is True
        assert res.centroid is not None
        u, v = res.centroid
        assert abs(u - 320.0) < 1.0
        assert abs(v - 240.0) < 1.0
        assert res.confidence > 0.5

    def test_noise_resilience(self):
        detector = SOTABeaconDetector()
        np.random.seed(42)
        noise = np.random.normal(20, 10, (480, 640)).astype(np.uint8)

        yy, xx = np.ogrid[:480, :640]
        dist_sq = (xx - 400)**2 + (yy - 150)**2
        beacon = (200 * np.exp(-dist_sq / (2 * 4.0**2))).astype(np.uint8)
        frame = cv2_add = np.clip(noise.astype(int) + beacon.astype(int), 0, 255).astype(np.uint8)

        res = detector.detect(frame, timestamp=2.0)
        assert res.detected is True
        assert res.centroid is not None
        u, v = res.centroid
        assert abs(u - 400.0) < 5.0
        assert abs(v - 150.0) < 5.0


class TestIMMEKFEstimator:
    def test_imm_initialization_and_update(self):
        imm = InteractingMultipleModelFilter()
        assert not imm.is_initialized

        est0 = imm.initialize((100.0, 100.0), timestamp=0.0)
        assert imm.is_initialized
        assert est0.estimated_x == 100.0
        assert est0.estimated_y == 100.0

        # Step forward with measurements moving at constant velocity (10 px/s)
        dt = 0.1
        for i in range(1, 10):
            meas = (100.0 + i * 1.0, 100.0 + i * 0.5)
            est = imm.update(meas, confidence=0.9, timestamp=i * dt)
            assert est.estimated_x is not None
            assert est.estimated_y is not None

        # Confirm mode probabilities updated and sum to 1
        probs = imm.mode_probabilities
        assert len(probs) == 3
        assert abs(sum(probs) - 1.0) < 1e-5

    def test_imm_missing_measurement_coasting(self):
        imm = InteractingMultipleModelFilter()
        imm.initialize((50.0, 50.0), timestamp=0.0)

        # Single step update to set velocity
        imm.update((52.0, 51.0), confidence=0.9, timestamp=0.1)

        # Missing measurement step
        est = imm.update_missing(timestamp=0.2)
        assert est.filter_status is not None


class TestADRCController:
    def test_adrc_axis_step(self):
        adrc = ADRCAxisController(b0=10.0, omega_o=30.0, omega_c=10.0, output_limit=5.0)
        error = 1.0  # 1 degree pointing error
        dt = 0.033

        cmd = adrc.compute(error, dt)
        assert abs(cmd) > 0.0
        assert abs(cmd) <= 5.0

    def test_dual_axis_adrc(self):
        controller = DualAxisADRCController(max_pan_rate_deg_s=5.0, max_tilt_rate_deg_s=5.0)
        cmd_pan, cmd_tilt = controller.compute(pan_error_deg=0.5, tilt_error_deg=-0.8, dt=0.033)
        assert abs(cmd_pan) <= 5.0
        assert abs(cmd_tilt) <= 5.0

    def test_pat_camera_controller_adrc_mode(self):
        pat_ctrl = PATCameraController(controller_type="ADRC")
        state = PATState()
        state.mode = PATMode.TRACK
        state.pan_error_deg = 0.2
        state.tilt_error_deg = -0.3

        cmd_pan, cmd_tilt, pid_pan, pid_tilt, ff_pan, ff_tilt, sat = pat_ctrl.compute_control_command(
            dt=0.033,
            pat_state=state,
            search_pan_rate=0.0,
            search_tilt_rate=0.0,
            reacquire_pan_rate=0.0,
            reacquire_tilt_rate=0.0,
        )
        assert abs(cmd_pan) <= 20.0
        assert abs(cmd_tilt) <= 20.0


class TestTrackIntegration:
    def test_track_with_imm_ekf(self):
        track = Track(track_id=1, filter_type="IMM_ADAPTIVE_EKF")
        est = track.step(measurement=(200.0, 150.0), confidence=0.95, timestamp=0.1)
        assert est is not None
        assert est.estimated_x is not None
