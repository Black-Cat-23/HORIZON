"""Tests for the FixedTimestepClock."""

import pytest
from simulator.core.clock import FixedTimestepClock


class TestFixedTimestepClock:
    """Validate deterministic behavior of the fixed timestep clock."""

    def test_initial_state(self):
        clock = FixedTimestepClock(frequency_hz=60.0)
        assert clock.frequency_hz == 60.0
        assert abs(clock.dt - 1.0 / 60.0) < 1e-12
        assert clock.current_frame == 0
        assert clock.current_time == 0.0

    def test_invalid_frequency_rejected(self):
        with pytest.raises(ValueError, match="frequency_hz must be > 0"):
            FixedTimestepClock(frequency_hz=0.0)

        with pytest.raises(ValueError, match="frequency_hz must be > 0"):
            FixedTimestepClock(frequency_hz=-10.0)

    def test_single_step(self):
        clock = FixedTimestepClock(frequency_hz=60.0)
        clock.step()
        assert clock.current_frame == 1
        assert abs(clock.current_time - 1.0 / 60.0) < 1e-12

    def test_multi_step_accuracy(self):
        clock = FixedTimestepClock(frequency_hz=60.0)
        for _ in range(60):
            clock.step()
        assert clock.current_frame == 60
        # Exactly 1.0 second after 60 steps at 60 Hz
        assert abs(clock.current_time - 1.0) < 1e-12

    def test_no_float_drift_over_10k_steps(self):
        clock = FixedTimestepClock(frequency_hz=100.0)
        for _ in range(10000):
            clock.step()
        assert clock.current_frame == 10000
        expected_time = 10000 * (1.0 / 100.0)
        assert abs(clock.current_time - expected_time) < 1e-12

    def test_reset(self):
        clock = FixedTimestepClock(frequency_hz=30.0)
        for _ in range(15):
            clock.step()
        assert clock.current_frame == 15
        assert clock.current_time > 0.0

        clock.reset()
        assert clock.current_frame == 0
        assert clock.current_time == 0.0
