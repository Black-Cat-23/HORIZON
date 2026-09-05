"""Tests for StraightLineTrajectory."""

import pytest
from simulator.trajectories.straight import StraightLineTrajectory


class TestStraightLineTrajectory:
    def test_linear_motion_without_bounds(self):
        traj = StraightLineTrajectory(
            x0=1000.0,
            y0=1000.0,
            vx0=50.0,
            vy0=-30.0,
            world_width=2000.0,
            world_height=2000.0,
        )
        x, y, vx, vy, ax, ay = traj.state_at(2.0)
        assert abs(x - 1100.0) < 1e-9
        assert abs(y - 940.0) < 1e-9
        assert abs(vx - 50.0) < 1e-9
        assert abs(vy - (-30.0)) < 1e-9
        assert ax == 0.0
        assert ay == 0.0

    def test_bounce_behavior(self):
        # Target at x=1980, heading right at 50 px/s with max_x = 1995 (2000 - 10/2)
        traj = StraightLineTrajectory(
            x0=1980.0,
            y0=1000.0,
            vx0=50.0,
            vy0=0.0,
            world_width=2000.0,
            world_height=2000.0,
            target_size_px=10.0,
            boundary_mode="bounce",
        )
        # At t=0.3: unbounded would be 1980 + 15 = 1995 (boundary hit)
        x_hit, _, vx_hit, _, _, _ = traj.state_at(0.3)
        assert abs(x_hit - 1995.0) < 1e-9

        # At t=0.5: hits at 0.3, bounces back for 0.2s at 50 px/s -> 1995 - 10 = 1985
        x_after, _, vx_after, _, _, _ = traj.state_at(0.5)
        assert abs(x_after - 1985.0) < 1e-9
        assert abs(vx_after - (-50.0)) < 1e-9

    def test_clamp_behavior(self):
        traj = StraightLineTrajectory(
            x0=1980.0,
            y0=1000.0,
            vx0=50.0,
            vy0=0.0,
            world_width=2000.0,
            world_height=2000.0,
            target_size_px=10.0,
            boundary_mode="clamp",
        )
        # At t=1.0: would exceed 1995, clamped to 1995, velocity goes to 0
        x, _, vx, _, _, _ = traj.state_at(1.0)
        assert abs(x - 1995.0) < 1e-9
        assert vx == 0.0

    def test_within_bounds_guarantee(self):
        traj = StraightLineTrajectory(
            x0=500.0,
            y0=500.0,
            vx0=300.0,
            vy0=400.0,
            world_width=2000.0,
            world_height=2000.0,
            target_size_px=10.0,
            boundary_mode="bounce",
        )
        for step in range(1000):
            t = step * 0.1
            x, y, vx, vy, _, _ = traj.state_at(t)
            assert 5.0 <= x <= 1995.0
            assert 5.0 <= y <= 1995.0

    def test_deterministic_repeatability(self):
        traj = StraightLineTrajectory(
            x0=300.0, y0=400.0, vx0=80.0, vy0=-70.0
        )
        s1 = [traj.state_at(t * 0.05) for t in range(100)]
        s2 = [traj.state_at(t * 0.05) for t in range(100)]
        assert s1 == s2
