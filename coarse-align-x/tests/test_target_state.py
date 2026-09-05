"""Tests for TargetState dataclass."""

from simulator.world.state import TargetState


class TestTargetState:
    def test_construction_and_attributes(self):
        state = TargetState(
            target_id=1,
            timestamp=0.5,
            x=500.25,
            y=600.75,
            vx=10.0,
            vy=-20.0,
            ax=0.5,
            ay=-1.5,
            visible=True,
        )
        assert state.target_id == 1
        assert state.timestamp == 0.5
        assert state.x == 500.25
        assert state.y == 600.75
        assert state.vx == 10.0
        assert state.vy == -20.0
        assert state.ax == 0.5
        assert state.ay == -1.5
        assert state.visible is True

    def test_speed_and_acceleration_properties(self):
        state = TargetState(
            target_id=1,
            timestamp=0.0,
            x=0.0,
            y=0.0,
            vx=3.0,
            vy=4.0,
            ax=6.0,
            ay=8.0,
        )
        assert abs(state.speed - 5.0) < 1e-12
        assert abs(state.acceleration_magnitude - 10.0) < 1e-12

    def test_immutability(self):
        state = TargetState(
            target_id=1,
            timestamp=0.0,
            x=100.0,
            y=100.0,
            vx=0.0,
            vy=0.0,
            ax=0.0,
            ay=0.0,
        )
        import pytest
        with pytest.raises(AttributeError):
            state.x = 200.0  # type: ignore
