"""Tests for FigureEightTrajectory."""

import math
import pytest
from simulator.trajectories.figure8 import FigureEightTrajectory


class TestFigureEightTrajectory:
    def test_center_crossing(self):
        # At t=0 with phase=0, x = cx, y = cy
        cx, cy = 1000.0, 1000.0
        traj = FigureEightTrajectory(center_x=cx, center_y=cy, amplitude_x=400.0, amplitude_y=300.0)
        x, y, _, _, _, _ = traj.state_at(0.0)
        assert abs(x - cx) < 1e-9
        assert abs(y - cy) < 1e-9

    def test_analytical_derivatives(self):
        cx, cy, ax_val, ay_val, omega = 1000.0, 1000.0, 350.0, 250.0, 0.8
        traj = FigureEightTrajectory(
            center_x=cx, center_y=cy, amplitude_x=ax_val, amplitude_y=ay_val, angular_velocity=omega
        )
        t = 2.468
        x, y, vx, vy, ax, ay = traj.state_at(t)

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

    def test_boundedness(self):
        cx, cy, ax_val, ay_val = 1000.0, 1000.0, 400.0, 300.0
        traj = FigureEightTrajectory(center_x=cx, center_y=cy, amplitude_x=ax_val, amplitude_y=ay_val)
        for step in range(200):
            t = step * 0.05
            x, y, _, _, _, _ = traj.state_at(t)
            assert cx - ax_val - 1e-9 <= x <= cx + ax_val + 1e-9
            assert cy - ay_val - 1e-9 <= y <= cy + ay_val + 1e-9

    def test_periodicity(self):
        omega = 1.0
        # Common period of sin(omega*t) and sin(2*omega*t) is 2*pi / omega
        period = 2.0 * math.pi / omega
        traj = FigureEightTrajectory(angular_velocity=omega)

        s0 = traj.state_at(0.0)
        sp = traj.state_at(period)
        for v0, vp in zip(s0, sp):
            assert abs(v0 - vp) < 1e-9
