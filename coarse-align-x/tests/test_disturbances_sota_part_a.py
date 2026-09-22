"""
Tests for Phase A Synthetic Physics & Optical Disturbance Engine Upgrades.
"""

import numpy as np
import pytest

from simulator.camera.psf import PointSpreadFunction, PSFConfig
from simulator.disturbances.config import CameraJitterConfig, PlatformMotionConfig, DistractorConfig
from simulator.disturbances.jitter import CameraJitterEngine
from simulator.disturbances.atmosphere import KolmogorovPhaseScreenEngine
from simulator.disturbances.platform import PlatformMotionEngine
from simulator.disturbances.distractor import FalseTargetDistractorEngine


def test_psf_airy_and_zernike():
    frame = np.zeros((100, 100), dtype=np.uint8)
    
    # Test Airy PSF
    cfg_airy = PSFConfig(model="airy", spot_sigma_px=2.0, amplitude=1.0)
    psf_airy = PointSpreadFunction(cfg_airy)
    frame_airy = frame.copy()
    psf_airy.apply(frame_airy, 50.0, 50.0, 200, 10.0)
    assert np.max(frame_airy) > 0

    # Test Zernike PSF
    cfg_zernike = PSFConfig(
        model="zernike",
        spot_sigma_px=2.0,
        zernike_defocus=0.2,
        zernike_astigmatism=0.1,
        zernike_coma=0.15,
        zernike_spherical=0.05,
    )
    psf_zernike = PointSpreadFunction(cfg_zernike)
    frame_zernike = frame.copy()
    psf_zernike.apply(frame_zernike, 50.0, 50.0, 200, 10.0)
    assert np.max(frame_zernike) > 0


def test_jitter_sota_distributions():
    rng = np.random.default_rng(123)
    frame = np.zeros((480, 640), dtype=np.uint8)

    # Test Harmonic
    cfg_h = CameraJitterConfig(enabled=True, distribution="harmonic", max_x_px=5.0, max_y_px=5.0)
    eng_h = CameraJitterEngine(cfg_h, rng)
    out_h, jx, jy = eng_h.step(frame, dt=0.016)
    assert abs(jx) <= 20.0 and abs(jy) <= 20.0

    # Test Colored
    cfg_c = CameraJitterConfig(enabled=True, distribution="colored", max_x_px=5.0, max_y_px=5.0)
    eng_c = CameraJitterEngine(cfg_c, rng)
    out_c, jx, jy = eng_c.step(frame, dt=0.016)
    assert abs(jx) <= 20.0 and abs(jy) <= 20.0

    # Test MIL-STD-810G
    cfg_m = CameraJitterConfig(enabled=True, distribution="mil_std_810g", max_x_px=5.0, max_y_px=5.0)
    eng_m = CameraJitterEngine(cfg_m, rng)
    out_m, jx, jy = eng_m.step(frame, dt=0.016)
    assert abs(jx) <= 20.0 and abs(jy) <= 20.0


def test_kolmogorov_phase_screen():
    frame = np.ones((100, 100), dtype=np.uint8) * 128
    rng = np.random.default_rng(42)
    eng = KolmogorovPhaseScreenEngine(r0_m=0.10, grid_size=64, rng=rng)
    out = eng.apply_speckle_boiling(frame, time_s=0.5, wind_speed_m_s=5.0)
    assert out.shape == frame.shape
    assert np.max(out) > 0


def test_cwh_orbital_motion():
    rng = np.random.default_rng(42)
    frame = np.zeros((480, 640), dtype=np.uint8)
    cfg = PlatformMotionConfig(enabled=True, model="cwh_orbital", max_dx_px_per_frame=20.0, max_dy_px_per_frame=20.0)
    eng = PlatformMotionEngine(cfg, rng)
    out, ox, oy, vx, vy = eng.step(frame, dt=0.016, sim_time=1.0)
    assert out.shape == frame.shape


def test_sota_distractors():
    rng = np.random.default_rng(42)
    frame = np.zeros((480, 640), dtype=np.uint8)

    cfg_glint = DistractorConfig(enabled=True, type="sun_glint", count=2, intensity=250, sun_phase_angle_deg=20.0)
    eng_glint = FalseTargetDistractorEngine(cfg_glint, rng)
    out_glint, count = eng_glint.apply(frame, sim_dt=0.033)
    assert count == 2
    assert np.max(out_glint) > 0

    cfg_clutter = DistractorConfig(enabled=True, type="cloud_edge_clutter", count=2, intensity=200)
    eng_clutter = FalseTargetDistractorEngine(cfg_clutter, rng)
    out_clutter, count = eng_clutter.apply(frame, sim_dt=0.033)
    assert count == 2
    assert np.max(out_clutter) > 0
