"""
HORIZON Phase 3 Unit Tests: Determinism & Seed Reproducibility
=====================================================================
Verification of bit-for-bit reproducibility:
  - Exp A (seed=42) vs Exp B (seed=42) => bit-for-bit identical
  - Exp C (seed=43) => divergent stochastic sequences
"""

import numpy as np
import pytest

from simulator.core.config import AppConfig, SimulationConfig, TrajectoryConfig
from simulator.core.simulation import SimulationEngine
from simulator.disturbances.presets import get_preset_config


class TestDisturbanceDeterminism:
    """Rigorous verification of deterministic disturbance generation."""

    def test_identical_seed_produces_identical_disturbed_frames(self):
        cfg42 = AppConfig(
            simulation=SimulationConfig(seed=42, duration_seconds=0.5, frequency_hz=60.0),
            trajectory=TrajectoryConfig(type="circular"),
            disturbance=get_preset_config("SEVERE"),
        )

        engine_a = SimulationEngine(cfg42, experiment_id="EXP_A")
        engine_a.initialize()

        frames_a = []
        for _ in range(30):
            engine_a.step()
            frames_a.append(engine_a.get_camera_frame().copy())

        engine_b = SimulationEngine(cfg42, experiment_id="EXP_B")
        engine_b.initialize()

        frames_b = []
        for _ in range(30):
            engine_b.step()
            frames_b.append(engine_b.get_camera_frame().copy())

        # Exact bit-for-bit identity across all frames
        for idx, (fa, fb) in enumerate(zip(frames_a, frames_b)):
            assert np.array_equal(fa, fb), f"Frame {idx} differed between identical seeds"

    def test_different_seed_diverges(self):
        cfg42 = AppConfig(
            simulation=SimulationConfig(seed=42, duration_seconds=0.5, frequency_hz=60.0),
            trajectory=TrajectoryConfig(type="circular"),
            disturbance=get_preset_config("SEVERE"),
        )
        cfg43 = AppConfig(
            simulation=SimulationConfig(seed=43, duration_seconds=0.5, frequency_hz=60.0),
            trajectory=TrajectoryConfig(type="circular"),
            disturbance=get_preset_config("SEVERE"),
        )

        engine_a = SimulationEngine(cfg42)
        engine_a.initialize()
        engine_a.step()
        frame_a = engine_a.get_camera_frame()

        engine_c = SimulationEngine(cfg43)
        engine_c.initialize()
        engine_c.step()
        frame_c = engine_c.get_camera_frame()

        # Disturbed frames must differ
        assert not np.array_equal(frame_a, frame_c)
