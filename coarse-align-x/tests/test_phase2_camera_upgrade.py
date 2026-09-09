"""
HORIZON Phase 2 Virtual Camera Upgrade Unit Tests
=================================================
Verification of:
  1. PSF rendering (box vs gaussian, background pedestal, amplitude scaling)
  2. Motion blur engine (image-velocity derived linear kernel length and direction)
  3. Electronic sensor response (exposure time scaling, gain dB, combined transfer)
  4. Beam-wander disturbance (Ornstein-Uhlenbeck process, determinism with seed)
  5. Immutable SensorFrame (read-only pixels, lineage tracking, metadata)
"""

from __future__ import annotations

import math
import numpy as np
import pytest

from simulator.camera.psf import PointSpreadFunction, PSFConfig, render_psf
from simulator.camera.motion_blur import MotionBlurEngine
from simulator.camera.sensor_response import SensorResponse, apply_sensor_response
from simulator.camera.beam_wander import BeamWanderEngine
from simulator.camera.sensor_frame import SensorFrame, SensorLineage
from simulator.camera.camera import VirtualCamera
from simulator.camera.intrinsics import CameraIntrinsics
from simulator.camera.gimbal import CameraGimbal
from simulator.core.config import AppConfig, CameraConfig, TargetConfig, DisturbanceConfig
from simulator.disturbances.config import BeamWanderConfig
from simulator.core.simulation import SimulationEngine


class TestPointSpreadFunction:
    """Verification of PSF optical rendering model."""

    def test_box_psf_backward_compatibility(self):
        """Box PSF model produces exact subpixel area-overlap rasterization."""
        frame_box = np.zeros((100, 100), dtype=np.uint8)
        psf = PointSpreadFunction(config=PSFConfig(model="box"))
        psf.apply(frame_box, x=50.0, y=50.0, intensity=255, size_px=10.0)

        # 10x10 square centered at 50,50 -> row/col 45..55
        assert np.sum(frame_box > 0) == 100
        assert frame_box[50, 50] == 255

    def test_gaussian_psf_smooth_profile(self):
        """Gaussian PSF model renders a smooth bell curve with configurable sigma."""
        frame_g = np.zeros((100, 100), dtype=np.uint8)
        psf = PointSpreadFunction(config=PSFConfig(model="gaussian", spot_sigma_px=2.0))
        psf.apply(frame_g, x=50.0, y=50.0, intensity=255, size_px=10.0)

        # Center should be peak, intensity should decrease radially
        assert frame_g[50, 50] > 0
        assert frame_g[50, 50] > frame_g[50, 54]
        assert frame_g[50, 54] > frame_g[50, 58]

    def test_psf_background_pedestal(self):
        """Background ADU pedestal is added to rendered region."""
        frame = np.zeros((100, 100), dtype=np.uint8)
        render_psf(frame, center_x=50.0, center_y=50.0, intensity=255, size_px=10.0, model="gaussian", background_adu=10.0)
        assert np.min(frame[45:55, 45:55]) >= 10


class TestMotionBlurEngine:
    """Verification of motion blur engine."""

    def test_motion_blur_length_formula(self):
        """Blur length satisfies blur_px = |v| * (exposure_ms / frame_interval_ms)."""
        engine = MotionBlurEngine(frame_interval_ms=33.333333333333336)
        
        # 10 px/frame velocity, 16.666 ms exposure (half frame) -> 5 px blur
        blur_px = engine.compute_blur_length(
            vel_u_px_per_frame=6.0,
            vel_v_px_per_frame=8.0,  # speed = 10 px/frame
            exposure_ms=16.666666666666668,
        )
        assert pytest.approx(blur_px, rel=1e-3) == 5.0

    def test_subpixel_motion_no_blur(self):
        """Sub-pixel velocity (< 0.5 px blur) leaves frame unchanged."""
        engine = MotionBlurEngine(frame_interval_ms=33.333)
        frame = np.zeros((50, 50), dtype=np.uint8)
        frame[25, 25] = 255
        
        blurred, blur_len, _, _ = engine.apply(
            frame=frame,
            vel_u_px_per_frame=0.2,
            vel_v_px_per_frame=0.0,
            exposure_ms=1.0,
        )
        assert blur_len < 0.5
        np.testing.assert_array_equal(blurred, frame)

    def test_motion_blur_directional_kernel(self):
        """Motion blur spreads intensity along motion direction."""
        engine = MotionBlurEngine(frame_interval_ms=33.333)
        frame = np.zeros((50, 50), dtype=np.uint8)
        frame[25, 25] = 255
        
        # Pure horizontal motion
        blurred = engine.apply_motion_blur(
            frame=frame,
            vx_px_s=300.0,  # 10 px/frame at 30Hz
            vy_px_s=0.0,
            exposure_ms=33.333,
        )
        # Intensity should spread horizontally (row 25)
        assert np.sum(blurred[25, :]) > 200
        assert np.count_nonzero(blurred[25, :]) > 1


class TestSensorResponse:
    """Verification of electronic sensor exposure and gain models."""

    def test_exposure_time_scaling(self):
        """Exposure time scales pixel intensity linearly with baseline reference."""
        sr = SensorResponse(exposure_ms=2.0, gain_db=0.0, baseline_exposure_ms=1.0)
        frame = np.array([[50, 100]], dtype=np.uint8)
        out = sr.apply(frame)
        np.testing.assert_array_equal(out, np.array([[100, 200]], dtype=np.uint8))

    def test_gain_db_scaling(self):
        """+6 dB gain doubles linear amplitude."""
        sr = SensorResponse(exposure_ms=1.0, gain_db=6.0205999, baseline_exposure_ms=1.0)
        frame = np.array([[50, 100]], dtype=np.uint8)
        out = sr.apply(frame)
        np.testing.assert_array_equal(out, np.array([[100, 200]], dtype=np.uint8))

    def test_saturation_clipping(self):
        """Over-exposure and high gain saturate at 255 uint8 ceiling."""
        sr = SensorResponse(exposure_ms=10.0, gain_db=20.0)
        frame = np.array([[100, 200]], dtype=np.uint8)
        out = sr.apply(frame)
        np.testing.assert_array_equal(out, np.array([[255, 255]], dtype=np.uint8))


class TestBeamWanderEngine:
    """Verification of optical beam-centroid wander."""

    def test_beam_wander_determinism(self):
        """Beam-wander trajectory is identical for same random seed."""
        rng_a = np.random.default_rng(42)
        rng_b = np.random.default_rng(42)
        bw_a = BeamWanderEngine(std_dev_px=3.0, correlation_time_s=0.5, rng=rng_a)
        bw_b = BeamWanderEngine(std_dev_px=3.0, correlation_time_s=0.5, rng=rng_b)

        offsets_a = [bw_a.step(0.016) for _ in range(50)]
        offsets_b = [bw_b.step(0.016) for _ in range(50)]

        np.testing.assert_allclose(offsets_a, offsets_b)

    def test_beam_wander_smoothness(self):
        """Ornstein-Uhlenbeck process produces correlated continuous drift (not white noise)."""
        rng = np.random.default_rng(123)
        bw = BeamWanderEngine(std_dev_px=5.0, correlation_time_s=1.0, rng=rng)
        offsets = [bw.step(0.001) for _ in range(100)]
        
        # Increments should be small for tiny dt = 1ms
        dx = np.diff([o[0] for o in offsets])
        assert np.max(np.abs(dx)) < 2.0


class TestSensorFrameLineage:
    """Verification of immutable SensorFrame container and lineage metadata."""

    def test_sensor_frame_immutability(self):
        """SensorFrame pixel array is read-only and throws ValueError on modification."""
        pixels = np.zeros((480, 640), dtype=np.uint8)
        sf = SensorFrame(frame_id=1, timestamp=0.1, pixels=pixels)
        
        assert sf.pixels.flags.writeable is False
        with pytest.raises(ValueError, match="assignment destination is read-only"):
            sf.pixels[0, 0] = 255

    def test_sensor_frame_with_disturbed_pixels(self):
        """with_disturbed_pixels preserves original clean frame metadata and updates status."""
        sf_clean = SensorFrame(frame_id=5, clean_frame_id=5, timestamp=0.166, exposure_ms=2.0)
        disturbed_px = np.full((480, 640), 50, dtype=np.uint8)
        sf_dist = sf_clean.with_disturbed_pixels(disturbed_px, disturbance_flags='{"gaussian": true}')

        assert sf_dist.is_disturbed is True
        assert sf_dist.clean_frame_id == 5
        assert sf_dist.exposure_ms == 2.0
        assert sf_dist.pixels[0, 0] == 50
