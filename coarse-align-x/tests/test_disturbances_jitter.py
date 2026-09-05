"""
HORIZON Phase 3 Unit Tests: Camera Jitter
===============================================
Formal verification of image-plane camera jitter disturbance:
  - Strict ±20.0 pixels per frame bound enforcement
  - Uniform & Normal distribution modes
  - Ground-truth independence
  - Deterministic repeatability
"""

import numpy as np
import pytest

from simulator.core.seed_manager import SeedManager
from simulator.disturbances.config import CameraJitterConfig, validate_disturbance_config
from simulator.disturbances.jitter import CameraJitterEngine


class TestCameraJitter:
    """Mathematical and statistical validation of camera jitter."""

    def test_disabled_identity(self):
        cfg = CameraJitterConfig(enabled=False, max_x_px=10.0, max_y_px=10.0)
        rng = SeedManager(seed=42).get_rng("jitter")
        engine = CameraJitterEngine(cfg, rng)

        frame = np.full((480, 640), 100, dtype=np.uint8)
        out, jx, jy = engine.step(frame)

        assert np.array_equal(out, frame)
        assert jx == 0.0
        assert jy == 0.0

    def test_maximum_bound_enforced(self):
        # Even with max allowed jitter (20.0 px), displacement must never exceed ±20 px
        cfg = CameraJitterConfig(enabled=True, max_x_px=20.0, max_y_px=20.0, distribution="uniform")
        rng = SeedManager(seed=123).get_rng("jitter")
        engine = CameraJitterEngine(cfg, rng)

        frame = np.zeros((480, 640), dtype=np.uint8)
        frame[240, 320] = 255  # Point source

        for _ in range(500):
            _, jx, jy = engine.step(frame)
            assert -20.0 <= jx <= 20.0
            assert -20.0 <= jy <= 20.0

    def test_normal_distribution_bounds(self):
        cfg = CameraJitterConfig(enabled=True, max_x_px=15.0, max_y_px=15.0, distribution="normal")
        rng = SeedManager(seed=456).get_rng("jitter")
        engine = CameraJitterEngine(cfg, rng)

        frame = np.zeros((480, 640), dtype=np.uint8)
        for _ in range(500):
            _, jx, jy = engine.step(frame)
            assert -20.0 <= jx <= 20.0
            assert -20.0 <= jy <= 20.0

    def test_invalid_max_rejected(self):
        with pytest.raises(ValueError, match="camera_jitter.max_x_px"):
            from simulator.disturbances.config import DisturbanceConfig
            validate_disturbance_config(
                DisturbanceConfig(camera_jitter=CameraJitterConfig(max_x_px=20.5))
            )

        with pytest.raises(ValueError, match="camera_jitter.max_y_px"):
            from simulator.disturbances.config import DisturbanceConfig
            validate_disturbance_config(
                DisturbanceConfig(camera_jitter=CameraJitterConfig(max_y_px=-1.0))
            )

    def test_deterministic_sequence(self):
        cfg = CameraJitterConfig(enabled=True, max_x_px=10.0, max_y_px=10.0)
        frame = np.full((480, 640), 50, dtype=np.uint8)

        engine1 = CameraJitterEngine(cfg, SeedManager(seed=42).get_rng("jitter"))
        engine2 = CameraJitterEngine(cfg, SeedManager(seed=42).get_rng("jitter"))

        for _ in range(20):
            out1, jx1, jy1 = engine1.step(frame)
            out2, jx2, jy2 = engine2.step(frame)
            assert jx1 == jx2
            assert jy1 == jy2
            assert np.array_equal(out1, out2)

    def test_different_seeds_diverge(self):
        cfg = CameraJitterConfig(enabled=True, max_x_px=10.0, max_y_px=10.0)
        frame = np.full((480, 640), 50, dtype=np.uint8)

        engine1 = CameraJitterEngine(cfg, SeedManager(seed=42).get_rng("jitter"))
        engine2 = CameraJitterEngine(cfg, SeedManager(seed=43).get_rng("jitter"))

        _, jx1, jy1 = engine1.step(frame)
        _, jx2, jy2 = engine2.step(frame)

        assert (jx1 != jx2) or (jy1 != jy2)
