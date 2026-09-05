"""Tests for RandomMotionTrajectory."""

import math
import numpy as np
import pytest
from simulator.trajectories.random_motion import RandomMotionTrajectory


class TestRandomMotionTrajectory:
    def test_reproducibility_with_same_seed(self):
        rng1 = np.random.default_rng(42)
        rng2 = np.random.default_rng(42)

        traj1 = RandomMotionTrajectory(rng=rng1, x0=1000.0, y0=1000.0)
        traj2 = RandomMotionTrajectory(rng=rng2, x0=1000.0, y0=1000.0)

        for step in range(120):
            t = step * (1.0 / 60.0)
            s1 = traj1.state_at(t)
            s2 = traj2.state_at(t)
            for v1, v2 in zip(s1, s2):
                assert abs(v1 - v2) < 1e-9

    def test_different_seeds_diverge(self):
        rng1 = np.random.default_rng(101)
        rng2 = np.random.default_rng(202)

        traj1 = RandomMotionTrajectory(rng=rng1, x0=1000.0, y0=1000.0)
        traj2 = RandomMotionTrajectory(rng=rng2, x0=1000.0, y0=1000.0)

        # After 2 seconds, trajectories should be in different positions
        s1 = traj1.state_at(2.0)
        s2 = traj2.state_at(2.0)
        dist = math.hypot(s1[0] - s2[0], s1[1] - s2[1])
        assert dist > 1.0

    def test_no_teleportation_and_continuity(self):
        rng = np.random.default_rng(777)
        max_speed = 150.0
        traj = RandomMotionTrajectory(rng=rng, x0=1000.0, y0=1000.0, max_speed=max_speed)

        dt = 1.0 / 60.0
        prev_x, prev_y = 1000.0, 1000.0

        for step in range(1, 300):
            t = step * dt
            x, y, _, _, _, _ = traj.state_at(t)
            step_dist = math.hypot(x - prev_x, y - prev_y)
            # Distance moved in one step cannot exceed max_speed * dt + margin for acceleration
            # With max_speed=150 and dt=1/60, max displacement per step is ~2.5 px
            assert step_dist < (max_speed * dt * 2.0), f"Teleportation detected at step {step}!"
            prev_x, prev_y = x, y

    def test_kinematic_bounds(self):
        rng = np.random.default_rng(999)
        max_speed = 120.0
        max_acc = 180.0
        traj = RandomMotionTrajectory(
            rng=rng, max_speed=max_speed, max_acceleration=max_acc
        )

        for step in range(300):
            t = step * (1.0 / 60.0)
            x, y, vx, vy, ax, ay = traj.state_at(t)

            speed = math.hypot(vx, vy)
            acc = math.hypot(ax, ay)

            assert speed <= max_speed + 1e-6
            assert acc <= max_acc + 1e-6
            assert 5.0 <= x <= 1995.0
            assert 5.0 <= y <= 1995.0

    def test_reset_reproducibility(self):
        rng = np.random.default_rng(555)
        traj = RandomMotionTrajectory(rng=rng, x0=500.0, y0=500.0)

        states_run1 = [traj.state_at(t * 0.05) for t in range(50)]
        traj.reset()
        states_run2 = [traj.state_at(t * 0.05) for t in range(50)]

        for s1, s2 in zip(states_run1, states_run2):
            for v1, v2 in zip(s1, s2):
                assert abs(v1 - v2) < 1e-9
