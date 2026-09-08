"""
HORIZON Phase 3 Disturbance Engine Upgrade Unit Tests
=====================================================
Verification of Phase 3 Extensions & Adversarial Laboratory:
  1. Temporal intensity fluctuation (slow, fast, mixed profiles)
  2. Temporary target occlusion (partial, complete, start/duration)
  3. False optical distractors (small spot, blob, multiple spots, reflection streak, noise cluster)
  4. Cross-channel disturbance correlation engine
  5. Dynamic disturbance injection scheduler (ramped, pulsed, scheduled)
  6. Adversarial scenario presets loading
  7. Counterfactual ablation equivalence & replayability
"""

from __future__ import annotations

import math
import numpy as np
import pytest

from simulator.core.seed_manager import SeedManager
from simulator.disturbances.config import (
    AtmosphereConfig,
    CameraJitterConfig,
    DistractorConfig,
    DisturbanceConfig,
    DisturbanceCorrelationConfig,
    GaussianNoiseConfig,
    InjectionScheduleConfig,
    IntensityFluctuationConfig,
    OcclusionConfig,
    PlatformMotionConfig,
    SaltPepperConfig,
    validate_disturbance_config,
)
from simulator.disturbances.correlation import DisturbanceCorrelationEngine
from simulator.disturbances.distractor import FalseTargetDistractorEngine
from simulator.disturbances.injection_scheduler import InjectionSchedulerEngine
from simulator.disturbances.intensity_fluctuation import IntensityFluctuationEngine
from simulator.disturbances.occlusion import TemporaryOcclusionEngine
from simulator.disturbances.pipeline import DisturbancePipeline
from simulator.disturbances.presets import get_preset_config


class TestTemporalIntensityFluctuation:
    """Verification of temporal beacon intensity fluctuation."""

    def test_slow_fast_mixed_modes(self):
        rng = np.random.default_rng(42)
        cfg_slow = IntensityFluctuationConfig(enabled=True, mode="slow", depth=0.5, frequency_hz=1.0)
        cfg_fast = IntensityFluctuationConfig(enabled=True, mode="fast", depth=0.5, frequency_hz=10.0)
        cfg_mixed = IntensityFluctuationConfig(enabled=True, mode="mixed", depth=0.5, frequency_hz=5.0)

        eng_slow = IntensityFluctuationEngine(cfg_slow, rng)
        eng_fast = IntensityFluctuationEngine(cfg_fast, rng)
        eng_mixed = IntensityFluctuationEngine(cfg_mixed, rng)

        mults_slow = [eng_slow.compute_multiplier(t) for t in np.linspace(0, 2.0, 50)]
        mults_fast = [eng_fast.compute_multiplier(t) for t in np.linspace(0, 2.0, 50)]
        mults_mixed = [eng_mixed.compute_multiplier(t) for t in np.linspace(0, 2.0, 50)]

        # Multipliers must remain bounded in [0.0, 1.0]
        assert all(0.0 <= m <= 1.0 for m in mults_slow)
        assert all(0.0 <= m <= 1.0 for m in mults_fast)
        assert all(0.0 <= m <= 1.0 for m in mults_mixed)


class TestTemporaryOcclusion:
    """Verification of temporary target occlusion."""

    def test_complete_and_partial_occlusion_window(self):
        cfg_complete = OcclusionConfig(enabled=True, type="complete", start_time_s=1.0, duration_s=2.0, severity=1.0)
        eng_complete = TemporaryOcclusionEngine(cfg_complete)

        # Before event window: 1.0 transmission
        assert eng_complete.compute_attenuation(0.5) == 1.0
        # During event window: 0.0 transmission (complete occlusion)
        assert eng_complete.compute_attenuation(2.0) == 0.0
        # After event window: 1.0 transmission
        assert eng_complete.compute_attenuation(3.5) == 1.0


class TestFalseOpticalDistractors:
    """Verification of false target distractor generation."""

    def test_distractor_rasterization_types(self):
        types = ["small_spot", "large_blob", "multiple_spots", "reflection_like", "noise_cluster"]
        rng = np.random.default_rng(123)

        for d_type in types:
            cfg = DistractorConfig(enabled=True, type=d_type, count=2, intensity=200)
            engine = FalseTargetDistractorEngine(cfg, rng)
            frame = np.zeros((480, 640), dtype=np.uint8)
            out, cnt = engine.apply(frame, sim_dt=0.033)

            assert cnt >= 1
            assert np.sum(out > 0) > 0  # Distractors actually rasterized into canvas


class TestDisturbanceCorrelation:
    """Verification of cross-channel stochastic correlation."""

    def test_coupled_noise_sampling(self):
        rng = np.random.default_rng(42)
        cfg = DisturbanceCorrelationConfig(enabled=True, platform_jitter_coupling=0.8)
        engine = DisturbanceCorrelationEngine(cfg, rng)

        samples = [engine.sample_coupled_noise(0.8) for _ in range(500)]
        z1 = [s[0] for s in samples]
        z2 = [s[1] for s in samples]

        # Empirical correlation should match ~0.8
        corr = float(np.corrcoef(z1, z2)[0, 1])
        assert pytest.approx(corr, abs=0.15) == 0.8


class TestInjectionScheduler:
    """Verification of dynamic disturbance gain scheduler."""

    def test_ramped_and_pulsed_gain(self):
        cfg_ramped = InjectionScheduleConfig(enabled=True, injection_mode="ramped", start_time_s=1.0, ramp_duration_s=2.0)
        eng_ramped = InjectionSchedulerEngine(cfg_ramped)

        assert eng_ramped.compute_gain(0.5) == 0.0
        assert eng_ramped.compute_gain(2.0) == 0.5
        assert eng_ramped.compute_gain(3.0) == 1.0

        cfg_pulsed = InjectionScheduleConfig(enabled=True, injection_mode="pulsed", start_time_s=0.0, pulse_period_s=2.0, pulse_duty_cycle=0.5)
        eng_pulsed = InjectionSchedulerEngine(cfg_pulsed)

        assert eng_pulsed.compute_gain(0.5) == 1.0  # inside duty cycle (50% of 2s = 1s)
        assert eng_pulsed.compute_gain(1.5) == 0.0  # outside duty cycle


class TestAdversarialScenarioPresets:
    """Verification of adversarial scenario presets loading."""

    def test_load_all_adversarial_presets(self):
        presets = [
            "DISTRACTOR_BURST",
            "OCCLUSION_EVENT",
            "BRIGHTNESS_FADE",
            "JITTER_BURST",
            "PLATFORM_SWING",
            "COMBINED_TURBULENCE",
        ]
        for preset_name in presets:
            cfg = get_preset_config(preset_name)
            validate_disturbance_config(cfg)
            assert cfg.enabled is True


class TestCounterfactualAblation:
    """Verification of seed-exact counterfactual ablation."""

    def test_ablation_single_channel(self):
        seed_mgr1 = SeedManager(seed=42)
        seed_mgr2 = SeedManager(seed=42)

        cfg = DisturbanceConfig(
            enabled=True,
            gaussian=GaussianNoiseConfig(enabled=True, sigma=10.0),
            salt_pepper=SaltPepperConfig(enabled=True, probability=0.05),
        )

        pipeline1 = DisturbancePipeline(cfg, seed_mgr1)
        pipeline2 = DisturbancePipeline(cfg, seed_mgr2)

        clean = np.full((480, 640), 100, dtype=np.uint8)

        frame_full, telem1 = pipeline1.apply(clean, sim_time=0.1, sim_dt=0.033)
        frame_ablated, telem2 = pipeline2.apply(clean, sim_time=0.1, sim_dt=0.033, ablate_module="gaussian")

        assert telem2.ablated_module == "gaussian"
        assert not np.array_equal(frame_full, frame_ablated)
