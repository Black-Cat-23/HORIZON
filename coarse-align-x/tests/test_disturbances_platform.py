"""
HORIZON Phase 3 Unit Tests: Platform Motion
==================================================
Formal verification of continuous platform motion disturbance:
  - Strict ±20.0 px/frame limit enforcement
  - Continuous kinematic displacement (no random teleports)
  - Mandatory Linear platform motion
  - Optional platform models (circular, figure8, spiral, random)
  - Telemetry fidelity and reset reproducibility
"""

import numpy as np
import pytest

from simulator.core.seed_manager import SeedManager
from simulator.disturbances.config import PlatformMotionConfig, validate_disturbance_config
from simulator.disturbances.platform import PlatformMotionEngine


class TestPlatformMotion:
    """Formal validation of continuous platform motion disturbance."""

    def test_disabled_identity(self):
        cfg = PlatformMotionConfig(enabled=False, velocity_x=50.0, velocity_y=30.0)
        rng = SeedManager(seed=42).get_rng("platform")
        engine = PlatformMotionEngine(cfg, rng)

        frame = np.full((480, 640), 100, dtype=np.uint8)
        out, ox, oy, vx, vy = engine.step(frame, dt=1/60.0, sim_time=0.0)

        assert np.array_equal(out, frame)
        assert ox == 0.0
        assert oy == 0.0

    def test_linear_continuity_and_per_frame_bound(self):
        # Configure high velocity
        cfg = PlatformMotionConfig(
            enabled=True,
            model="linear",
            velocity_x=300.0,  # 300 * (1/60) = 5.0 px/frame
            velocity_y=120.0,  # 120 * (1/60) = 2.0 px/frame
            max_dx_px_per_frame=20.0,
            max_dy_px_per_frame=20.0,
            boundary_limit_px=100.0,
        )
        rng = SeedManager(seed=42).get_rng("platform")
        engine = PlatformMotionEngine(cfg, rng)

        frame = np.full((480, 640), 100, dtype=np.uint8)
        dt = 1.0 / 60.0

        prev_ox, prev_oy = 0.0, 0.0
        for i in range(120):
            t = i * dt
            out, ox, oy, vx, vy = engine.step(frame, dt=dt, sim_time=t)

            delta_x = abs(ox - prev_ox)
            delta_y = abs(oy - prev_oy)

            # Strict check: per-frame delta must NEVER exceed 20 px/frame
            assert delta_x <= 20.0
            assert delta_y <= 20.0
            assert abs(ox) <= 100.0
            assert abs(oy) <= 100.0

            prev_ox, prev_oy = ox, oy

    def test_linear_velocity_clamp_to_official_twenty_pixels_per_frame(self):
        # Configure excessive velocity: 2000 px/s at 60Hz would be 33.3 px/frame
        cfg = PlatformMotionConfig(
            enabled=True,
            model="linear",
            velocity_x=2000.0,
            velocity_y=2000.0,
            max_dx_px_per_frame=20.0,  # Clamp must cap at 20.0 px/frame
            max_dy_px_per_frame=20.0,
            boundary_limit_px=500.0,
        )
        rng = SeedManager(seed=42).get_rng("platform")
        engine = PlatformMotionEngine(cfg, rng)

        frame = np.full((480, 640), 100, dtype=np.uint8)
        dt = 1.0 / 60.0

        out, ox, oy, vx, vy = engine.step(frame, dt=dt, sim_time=0.0)

        # First step from 0.0 offset must be exactly clamped to 20.0 px
        assert pytest.approx(20.0, abs=1e-6) == abs(ox)
        assert pytest.approx(20.0, abs=1e-6) == abs(oy)

    def test_optional_platform_models(self):
        frame = np.full((480, 640), 100, dtype=np.uint8)
        dt = 1.0 / 60.0

        for model in ["circular", "figure8", "spiral", "random"]:
            cfg = PlatformMotionConfig(enabled=True, model=model, max_dx_px_per_frame=20.0, max_dy_px_per_frame=20.0)
            rng = SeedManager(seed=77).get_rng("platform")
            engine = PlatformMotionEngine(cfg, rng)

            prev_ox, prev_oy = 0.0, 0.0
            for i in range(60):
                t = i * dt
                out, ox, oy, vx, vy = engine.step(frame, dt=dt, sim_time=t)
                delta_x = abs(ox - prev_ox)
                delta_y = abs(oy - prev_oy)
                assert delta_x <= 20.0
                assert delta_y <= 20.0
                assert out.shape == (480, 640)
                assert out.dtype == np.uint8
                prev_ox, prev_oy = ox, oy

    def test_reset_reproducibility(self):
        cfg = PlatformMotionConfig(enabled=True, model="linear", velocity_x=50.0, velocity_y=30.0)
        dt = 1.0 / 60.0
        frame = np.full((480, 640), 80, dtype=np.uint8)

        engine = PlatformMotionEngine(cfg, SeedManager(seed=42).get_rng("platform"))

        # Run 10 steps
        traj1 = []
        for i in range(10):
            _, ox, oy, _, _ = engine.step(frame, dt=dt, sim_time=i * dt)
            traj1.append((ox, oy))

        # Reset
        engine.reset()
        assert engine.offset_x == 0.0
        assert engine.offset_y == 0.0

        # Run 10 steps again
        traj2 = []
        for i in range(10):
            _, ox, oy, _, _ = engine.step(frame, dt=dt, sim_time=i * dt)
            traj2.append((ox, oy))

        assert traj1 == traj2
