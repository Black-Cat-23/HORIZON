"""
Unit tests for PID controller, anti-windup, rate saturation, and camera controller.
HORIZON Phase 6
"""

import pytest
from control.pid import PIDController
from control.saturation import ControllerSaturation
from control.camera_controller import PATCameraController
from pat.state import PATState, PATMode


def test_pid_proportional_response():
    pid = PIDController(kp=2.0, ki=0.0, kd=0.0, output_limit=5.0)
    out = pid.compute(error=1.0, dt=0.1)
    assert out == pytest.approx(2.0)


def test_pid_anti_windup_clamping():
    pid = PIDController(kp=0.0, ki=1.0, kd=0.0, max_integral=1.5, output_limit=5.0)
    for _ in range(100):
        pid.compute(error=1.0, dt=0.1)
    assert pid.integral == pytest.approx(1.5)


def test_controller_saturation_clamping():
    sat = ControllerSaturation(max_pan_rate_deg_s=5.0, max_tilt_rate_deg_s=5.0)
    c_pan, c_tilt, is_sat = sat.apply(10.0, -8.0)
    assert c_pan == pytest.approx(5.0)
    assert c_tilt == pytest.approx(-5.0)
    assert is_sat is True


def test_camera_controller_mode_switch():
    ctrl = PATCameraController()
    state = PATState(mode=PATMode.TRACK, pan_error_deg=0.5, tilt_error_deg=-0.2)

    cmd_pan, cmd_tilt, pid_p, pid_t, ff_p, ff_t, sat = ctrl.compute_control_command(
        dt=0.016,
        pat_state=state,
        search_pan_rate=0.0,
        search_tilt_rate=0.0,
        reacquire_pan_rate=0.0,
        reacquire_tilt_rate=0.0,
    )
    assert cmd_pan > 0.0
    assert cmd_tilt < 0.0
