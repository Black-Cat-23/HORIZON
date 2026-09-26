"""
Unit tests for Phase B Perception & Subpixel Centroiding Engine SOTA Upgrades.
"""

import numpy as np
import pytest

from simulator.perception.centroid import compute_weighted_cog, compute_gaussian_fit
from simulator.perception.config import CentroidConfig, DetectorConfig
from simulator.perception.sota_detector import compute_fourier_phase_correlation, SOTABeaconDetector
from simulator.perception.neural_detector import NeuralBeaconDetector
from simulator.perception.candidate import compute_velocity_adaptive_roi


def test_mad_adaptive_cog():
    roi = np.zeros((21, 21), dtype=np.uint8)
    roi[8:13, 8:13] = 200
    u, v, su, sv = compute_weighted_cog(roi, None, bg_level=10.0, x_offset=0, y_offset=0)
    assert 9.0 <= u <= 11.0
    assert 9.0 <= v <= 11.0
    assert su > 0 and sv > 0


def test_dft_matrix_upsampled_phase_correlation():
    roi = np.zeros((32, 32), dtype=np.uint8)
    ref = np.zeros((32, 32), dtype=np.uint8)

    # Shifted beacon spot
    roi[14:18, 14:18] = 220
    ref[15:19, 15:19] = 220

    du, dv, conf = compute_fourier_phase_correlation(roi, ref)
    assert isinstance(du, float)
    assert isinstance(dv, float)
    assert 0.0 <= conf <= 1.0


def test_anisotropic_gaussian_fit():
    roi = np.zeros((25, 25), dtype=np.uint8)
    # Anisotropic elongated optical spot
    cols, rows = np.meshgrid(np.arange(25), np.arange(25))
    spot = 220.0 * np.exp(-((cols - 12.0)**2 / (2.0 * 2.0**2) + (rows - 12.0)**2 / (2.0 * 4.0**2)))
    roi = np.clip(spot, 0, 255).astype(np.uint8)

    cfg = CentroidConfig(method="gaussian_fit")
    u, v, su, sv, success = compute_gaussian_fit(roi, None, bg_level=0.0, x_offset=0, y_offset=0, config=cfg)
    assert 11.0 <= u <= 13.0
    assert 11.0 <= v <= 13.0
    assert su > 0 and sv > 0


def test_synthetic_neural_heatmap_fallback():
    detector = NeuralBeaconDetector(DetectorConfig())
    frame = np.zeros((480, 640), dtype=np.uint8)
    frame[235:245, 315:325] = 210

    res = detector.detect(frame, timestamp=1.0)
    assert res.detected is True
    assert res.centroid is not None
    assert 310.0 <= res.centroid[0] <= 330.0
    assert 230.0 <= res.centroid[1] <= 250.0


def test_velocity_adaptive_roi():
    x, y, w, h = compute_velocity_adaptive_roi(
        predicted_u=320.0,
        predicted_v=240.0,
        predicted_vx=120.0,
        predicted_vy=0.0,
        pos_uncertainty_px=5.0,
    )
    assert w > 30
    assert h >= 30
    assert x >= 0 and y >= 0
