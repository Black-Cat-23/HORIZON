"""
Initial-State Randomization Tests
=====================================
Verifies that initial camera pointing can be:
  1. Fixed at (0°, 0°) when max_initial_offset_deg = 0.0 (backward compat)
  2. Deterministically randomized from seed when max_initial_offset_deg > 0
  3. Explicitly set via initial_pan_deg / initial_tilt_deg
  4. Reproducible: identical seeds → identical pointing
  5. Divergent: different seeds → different pointing
"""

from __future__ import annotations

import pytest
from simulator.core.config import AppConfig, CameraConfig, SimulationConfig
from simulator.core.simulation import SimulationEngine


def _make_engine(
    seed: int = 42,
    initial_pan_deg: float = 0.0,
    initial_tilt_deg: float = 0.0,
    max_initial_offset_deg: float = 0.0,
) -> SimulationEngine:
    config = AppConfig(
        camera=CameraConfig(
            initial_pan_deg=initial_pan_deg,
            initial_tilt_deg=initial_tilt_deg,
            max_initial_offset_deg=max_initial_offset_deg,
        ),
        simulation=SimulationConfig(seed=seed, duration_seconds=0.1),
    )
    engine = SimulationEngine(config)
    engine.initialize()
    return engine


class TestDefaultInitialPointing:
    """When max_initial_offset_deg=0.0, camera must always start at (0°, 0°)."""

    def test_default_config_starts_at_boresight(self):
        """Default config: pan=0°, tilt=0°."""
        engine = _make_engine()
        assert engine.camera.gimbal.pan_deg == 0.0
        assert engine.camera.gimbal.tilt_deg == 0.0

    def test_zero_offset_ignores_seed(self):
        """With max_offset=0, different seeds must all give (0°, 0°)."""
        for seed in [1, 42, 100, 999]:
            engine = _make_engine(seed=seed, max_initial_offset_deg=0.0)
            assert engine.camera.gimbal.pan_deg == 0.0
            assert engine.camera.gimbal.tilt_deg == 0.0


class TestExplicitInitialPointing:
    """Explicit initial_pan_deg / initial_tilt_deg override must be applied exactly."""

    def test_explicit_pan_is_applied(self):
        engine = _make_engine(initial_pan_deg=1.5)
        assert abs(engine.camera.gimbal.pan_deg - 1.5) < 1e-9

    def test_explicit_tilt_is_applied(self):
        engine = _make_engine(initial_tilt_deg=-0.8)
        assert abs(engine.camera.gimbal.tilt_deg - (-0.8)) < 1e-9

    def test_explicit_pan_and_tilt_together(self):
        engine = _make_engine(initial_pan_deg=2.0, initial_tilt_deg=-1.5)
        assert abs(engine.camera.gimbal.pan_deg - 2.0) < 1e-9
        assert abs(engine.camera.gimbal.tilt_deg - (-1.5)) < 1e-9


class TestSeedDerivedInitialPointing:
    """Seed-derived initial pointing must be deterministic and within bounds."""

    def test_same_seed_gives_same_pointing(self):
        """Identical seeds must produce identical initial pan/tilt."""
        engine_a = _make_engine(seed=42, max_initial_offset_deg=1.0)
        engine_b = _make_engine(seed=42, max_initial_offset_deg=1.0)

        assert engine_a.camera.gimbal.pan_deg == engine_b.camera.gimbal.pan_deg
        assert engine_a.camera.gimbal.tilt_deg == engine_b.camera.gimbal.tilt_deg

    def test_different_seeds_give_different_pointing(self):
        """Different seeds must produce different initial pan/tilt."""
        engine_a = _make_engine(seed=42, max_initial_offset_deg=1.0)
        engine_b = _make_engine(seed=100, max_initial_offset_deg=1.0)

        # Different seeds should give different values (statistically certain)
        different = (
            engine_a.camera.gimbal.pan_deg != engine_b.camera.gimbal.pan_deg
            or engine_a.camera.gimbal.tilt_deg != engine_b.camera.gimbal.tilt_deg
        )
        assert different, "Seed 42 and seed 100 produced identical initial pointing!"

    def test_initial_pointing_within_offset_bounds(self):
        """Seed-derived pan/tilt must stay within ±max_initial_offset_deg."""
        max_offset = 1.5
        for seed in [1, 2, 3, 42, 100, 999, 12345]:
            engine = _make_engine(seed=seed, max_initial_offset_deg=max_offset)
            pan = engine.camera.gimbal.pan_deg
            tilt = engine.camera.gimbal.tilt_deg
            assert abs(pan) <= max_offset + 1e-9, (
                f"seed={seed}: pan={pan:.4f}° exceeds ±{max_offset}°"
            )
            assert abs(tilt) <= max_offset + 1e-9, (
                f"seed={seed}: tilt={tilt:.4f}° exceeds ±{max_offset}°"
            )

    def test_reset_reproduces_same_initial_pointing(self):
        """After reset(), initial pan/tilt must be reproduced exactly."""
        engine = _make_engine(seed=42, max_initial_offset_deg=1.0)

        pan_first = engine.camera.gimbal.pan_deg
        tilt_first = engine.camera.gimbal.tilt_deg

        # Advance simulation
        for _ in range(10):
            engine.step()

        # Reset
        engine.reset()

        assert abs(engine.camera.gimbal.pan_deg - pan_first) < 1e-9, (
            f"Pan after reset: {engine.camera.gimbal.pan_deg:.6f} != {pan_first:.6f}"
        )
        assert abs(engine.camera.gimbal.tilt_deg - tilt_first) < 1e-9

    def test_nonzero_offset_changes_initial_position(self):
        """With max_offset>0, at least some seeds give non-zero pointing."""
        found_nonzero = False
        for seed in range(50):
            engine = _make_engine(seed=seed, max_initial_offset_deg=1.0)
            if abs(engine.camera.gimbal.pan_deg) > 1e-6 or abs(engine.camera.gimbal.tilt_deg) > 1e-6:
                found_nonzero = True
                break
        assert found_nonzero, "No seed gave non-zero initial pointing with max_offset=1.0°"


class TestInitialPointingConfigValidation:
    """Validation of initial pointing config parameters."""

    def test_negative_max_offset_rejected(self):
        """max_initial_offset_deg < 0 must raise ConfigValidationError."""
        from simulator.core.config import ConfigValidationError
        config = AppConfig(
            camera=CameraConfig(max_initial_offset_deg=-0.5),
        )
        from simulator.core.config import validate_config
        with pytest.raises(ConfigValidationError):
            validate_config(config)
