"""Tests for CircularTrajectory."""

import math
import pytest
from simulator.trajectories.circular import CircularTrajectory


class TestCircularTrajectory:
    def test_radius_and_center(self):
        cx, cy, r = 1000.0, 1000.0, 300.0
        traj = CircularTrajectory(center_x=cx, center_y=cy, radius=r, angular_velocity=1.0)
        for step in range(50):
            t = step * 0.1
            x, y, _, _, _, _ = traj.state_at(t)
            dist_to_center = math.hypot(x - cx, y - cy)
            assert abs(dist_to_center - r) < 1e-9

    def test_analytical_derivatives(self):
        cx, cy, r, omega = 1000.0, 1000.0, 200.0, 1.5
        traj = CircularTrajectory(
            center_x=cx, center_y=cy, radius=r, angular_velocity=omega
        )
        t = 1.234
        x, y, vx, vy, ax, ay = traj.state_at(t)

        # Numerical differentiation check
        eps = 1e-6
        x_plus, y_plus, vx_plus, vy_plus, _, _ = traj.state_at(t + eps)
        x_minus, y_minus, vx_minus, vy_minus, _, _ = traj.state_at(t - eps)

        num_vx = (x_plus - x_minus) / (2 * eps)
        num_vy = (y_plus - y_minus) / (2 * eps)
        num_ax = (vx_plus - vx_minus) / (2 * eps)
        num_ay = (vy_plus - vy_minus) / (2 * eps)

        assert abs(vx - num_vx) < 1e-4
        assert abs(vy - num_vy) < 1e-4
        assert abs(ax - num_ax) < 1e-4
        assert abs(ay - num_ay) < 1e-4

    def test_periodicity(self):
        omega = 2.0
        period = 2.0 * math.pi / omega
        traj = CircularTrajectory(center_x=1000.0, center_y=1000.0, radius=200.0, angular_velocity=omega)

        s0 = traj.state_at(0.0)
        s_period = traj.state_at(period)
        for v0, vp in zip(s0, s_period):
            assert abs(v0 - vp) < 1e-9

    def test_invalid_radius_rejected(self):
        with pytest.raises(ValueError, match="Radius must be positive"):
            CircularTrajectory(radius=0.0)
        with pytest.raises(ValueError, match="Radius must be positive"):
            CircularTrajectory(radius=-50.0)

    def test_out_of_bounds_rejected(self):
        with pytest.raises(ValueError, match="exceeds world"):
            CircularTrajectory(center_x=100.0, radius=200.0, world_width=2000.0)
