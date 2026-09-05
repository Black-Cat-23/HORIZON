"""
HORIZON Phase 3 Unit Tests: Atmospheric Degradation
==========================================================
Validation of the 5 official atmospheric conditions:
  - CLEAR (Identity)
  - HAZE
  - FOG
  - RAIN
  - LOW_LIGHT
"""

import numpy as np
import pytest

from simulator.disturbances.atmosphere import apply_atmospheric_degradation
from simulator.disturbances.config import AtmosphereConfig, DisturbanceConfig, validate_disturbance_config


class TestAtmosphericDegradation:
    """Mathematical validation of atmospheric degradation models."""

    def test_clear_condition_exact_identity(self):
        frame = np.random.default_rng(42).integers(0, 256, size=(480, 640), dtype=np.uint8)
        cfg = AtmosphereConfig(enabled=True, condition="clear")

        out, c, b = apply_atmospheric_degradation(frame, cfg)
        assert np.array_equal(out, frame)
        assert c == 1.0
        assert b == 0.0

    def test_disabled_identity(self):
        frame = np.full((480, 640), 120, dtype=np.uint8)
        cfg = AtmosphereConfig(enabled=False, condition="fog")

        out, c, b = apply_atmospheric_degradation(frame, cfg)
        assert np.array_equal(out, frame)

    def test_all_five_official_conditions_produce_valid_uint8(self):
        frame = np.random.default_rng(99).integers(0, 256, size=(480, 640), dtype=np.uint8)

        for condition in ["clear", "haze", "fog", "rain", "low_light"]:
            cfg = AtmosphereConfig(enabled=True, condition=condition)
            out, c, b = apply_atmospheric_degradation(frame, cfg)
            assert out.shape == (480, 640)
            assert out.dtype == np.uint8
            assert out.min() >= 0
            assert out.max() <= 255

    def test_contrast_monotonicity(self):
        # High contrast image: alternating 0 and 255
        frame = np.zeros((100, 100), dtype=np.uint8)
        frame[::2, ::2] = 255

        var_clean = np.var(frame.astype(np.float64))

        cfg_haze = AtmosphereConfig(enabled=True, condition="haze")
        out_haze, _, _ = apply_atmospheric_degradation(frame, cfg_haze)
        var_haze = np.var(out_haze.astype(np.float64))

        cfg_fog = AtmosphereConfig(enabled=True, condition="fog")
        out_fog, _, _ = apply_atmospheric_degradation(frame, cfg_fog)
        var_fog = np.var(out_fog.astype(np.float64))

        # Fog has lower contrast factor than haze
        assert var_clean > var_haze > var_fog

    def test_low_light_reduces_brightness_without_noise(self):
        frame = np.full((100, 100), 150, dtype=np.uint8)
        cfg = AtmosphereConfig(enabled=True, condition="low_light")

        out, c, b = apply_atmospheric_degradation(frame, cfg)

        # In low light with flat input, output must remain flat (NO silent noise injection!)
        assert np.all(out == out[0, 0])
        assert out[0, 0] < 150

    def test_invalid_condition_rejected(self):
        with pytest.raises(ValueError, match="atmosphere.condition"):
            validate_disturbance_config(
                DisturbanceConfig(atmosphere=AtmosphereConfig(condition="sandstorm"))
            )
