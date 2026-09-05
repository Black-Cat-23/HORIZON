"""
Formal V&V: Camera Actuator Rate Limit, Motion Smoothness, and State Separation.
Sections 11, 12, 13 of Phase 2 Formal Verification & Validation specification.
"""

import pytest
from simulator.camera.gimbal import CameraGimbal


class TestCameraRateLimitVerification:
    """Section 11: Camera Rate-Limit Verification."""

    @pytest.mark.parametrize(
        "cmd_pan, cmd_tilt",
        [
            (0.0, 0.0),
            (+1.0, +1.0),
            (-1.0, -1.0),
            (+5.0, +5.0),
            (-5.0, -5.0),
            (+10.0, +10.0),
            (-10.0, -10.0),
            (+100.0, +100.0),
            (-100.0, -100.0),
        ],
    )
    def test_rate_limiting_across_command_spectrum(self, cmd_pan: float, cmd_tilt: float):
        gimbal = CameraGimbal(rate_limit_deg_s=5.0, accel_limit_deg_s2=None)
        gimbal.set_rate_command(cmd_pan, cmd_tilt)
        gimbal.step(dt=0.1)

        # Actual slew rates must NEVER exceed 5.0 deg/s
        assert abs(gimbal.actual_pan_rate) <= 5.0 + 1e-9
        assert abs(gimbal.actual_tilt_rate) <= 5.0 + 1e-9


class TestCameraMotionVerification:
    """Section 12: Camera Motion Verification (No Teleportation & Acceleration Bounded)."""

    def test_no_teleportation_smooth_progression(self):
        dt = 1.0 / 60.0
        accel_limit = 50.0  # deg/s²
        gimbal = CameraGimbal(rate_limit_deg_s=5.0, accel_limit_deg_s2=accel_limit)
        gimbal.set_rate_command(5.0, 0.0)

        prev_pan = gimbal.pan_deg
        prev_rate = gimbal.actual_pan_rate

        for step in range(120):  # 2 seconds
            gimbal.step(dt)

            delta_pan = abs(gimbal.pan_deg - prev_pan)
            # Max displacement in one step cannot exceed 5.0 deg/s * dt
            assert delta_pan <= (5.0 * dt) + 1e-9, f"Teleportation detected at step {step}!"

            # Acceleration verification: |Delta rate / dt| <= accel_limit
            delta_rate = abs(gimbal.actual_pan_rate - prev_rate)
            accel_measured = delta_rate / dt
            assert accel_measured <= accel_limit + 1e-6, f"Accel limit exceeded: {accel_measured}"

            prev_pan = gimbal.pan_deg
            prev_rate = gimbal.actual_pan_rate


class TestCameraCommandVsActualState:
    """Section 13: Camera Command vs Actual State Separation."""

    def test_commanded_vs_actual_separation(self):
        gimbal = CameraGimbal(rate_limit_deg_s=5.0, accel_limit_deg_s2=None)

        # Issue command exceeding rate limit (15.0 deg/s > 5.0 deg/s)
        gimbal.set_rate_command(15.0, -20.0)
        gimbal.step(dt=0.1)

        # 1. Commanded rate != actual rate
        assert gimbal.commanded_pan_rate == 15.0
        assert gimbal.commanded_tilt_rate == -20.0
        assert gimbal.actual_pan_rate != gimbal.commanded_pan_rate
        assert gimbal.actual_tilt_rate != gimbal.commanded_tilt_rate

        # 2. Actual rate == limited rate
        assert abs(gimbal.actual_pan_rate - 5.0) < 1e-9
        assert abs(gimbal.actual_tilt_rate - (-5.0)) < 1e-9
