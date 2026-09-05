"""Tests for SimulationEngine."""

import numpy as np
import pytest
from simulator.core.config import AppConfig, SimulationConfig, TrajectoryConfig
from simulator.core.simulation import SimulationEngine


class TestSimulationEngine:
    def test_initialization(self):
        config = AppConfig()
        engine = SimulationEngine(config, experiment_id="EXP_TEST_01")
        engine.initialize()

        assert engine.is_initialized
        assert engine.clock.current_frame == 0
        assert engine.clock.current_time == 0.0

        state = engine.get_current_state()
        assert state.target_id == 1
        assert state.timestamp == 0.0

        frame = engine.get_current_frame()
        assert frame.shape == (2000, 2000)
        assert frame.dtype == np.uint8

        # Ground truth recorded initial frame 0
        assert engine.recorder.record_count == 1

    def test_step_advances_simulation(self):
        config = AppConfig(
            simulation=SimulationConfig(frequency_hz=60.0, duration_seconds=1.0)
        )
        engine = SimulationEngine(config)
        engine.initialize()

        frame = engine.step()
        assert engine.clock.current_frame == 1
        assert abs(engine.clock.current_time - (1.0 / 60.0)) < 1e-9

        state = engine.get_current_state()
        assert abs(state.timestamp - (1.0 / 60.0)) < 1e-9
        assert frame.shape == (2000, 2000)
        assert engine.recorder.record_count == 2  # frame 0 + frame 1

    def test_run_to_completion(self):
        # 0.5s at 60Hz = 30 frames
        config = AppConfig(
            simulation=SimulationConfig(frequency_hz=60.0, duration_seconds=0.5)
        )
        engine = SimulationEngine(config)
        frames_seen = []

        def frame_hook(f_idx, s, img):
            frames_seen.append(f_idx)

        engine.run(callback=frame_hook)

        assert engine.clock.current_frame == 30
        assert len(frames_seen) == 31  # frame 0 to 30 inclusive
        assert engine.recorder.record_count == 31

    def test_reset(self):
        config = AppConfig(
            simulation=SimulationConfig(frequency_hz=60.0, duration_seconds=0.5)
        )
        engine = SimulationEngine(config)
        engine.initialize()

        s0 = engine.get_current_state()
        for _ in range(10):
            engine.step()
        assert engine.clock.current_frame == 10

        engine.reset()
        assert engine.clock.current_frame == 0
        assert engine.clock.current_time == 0.0
        s_reset = engine.get_current_state()
        assert abs(s0.x - s_reset.x) < 1e-9
        assert abs(s0.y - s_reset.y) < 1e-9
