"""
Unit tests for PID controller, anti-windup, rate saturation, gain scheduler, and camera controller.
HORIZON — SIH 2026 PS SIH26169 (PDF Section 6.6)
"""

import pytest
from control.pid import PIDController
from control.saturation import ControllerSaturation
from control.gain_scheduler import GainScheduler, ScheduledGains
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


def test_gain_scheduler_regimes():
    scheduler = GainScheduler()

    # TRACK Mode: high Kp, active Ki, active Kff
    gains_track = scheduler.get_gains(PATMode.TRACK)
    assert gains_track.kp > 1.2
    assert gains_track.ki > 0.05
    assert gains_track.kff > 0.4

    # ACQUIRE Mode: moderate Kp, gentle Ki, higher Kd
    gains_acquire = scheduler.get_gains(PATMode.ACQUIRE)
    assert gains_acquire.kp < gains_track.kp
    assert gains_acquire.kd > gains_track.kd

    # DEGRADED Mode: low Kp, zero Ki (prevents noise windup), heavy Kd damping
    gains_degraded = scheduler.get_gains(PATMode.DEGRADED)
    assert gains_degraded.kp < gains_acquire.kp
    assert gains_degraded.ki == 0.0
    assert gains_degraded.kd > gains_track.kd
    assert gains_degraded.kff == 0.0

    # SEARCH Mode: zero gains (disengaged)
    gains_search = scheduler.get_gains(PATMode.SEARCH)
    assert gains_search.kp == 0.0
    assert gains_search.ki == 0.0


def test_gain_scheduler_continuous_interpolation():
    scheduler = GainScheduler()

    # Quality at degraded boundary
    low_q_gains = scheduler.get_gains(PATMode.TRACK, track_quality=0.3, continuous_interpolation=True)
    assert low_q_gains.kp == pytest.approx(scheduler.gains_degraded.kp, abs=1e-3)
    assert low_q_gains.ki == pytest.approx(0.0, abs=1e-3)

    # Quality at full lock
    high_q_gains = scheduler.get_gains(PATMode.TRACK, track_quality=0.9, continuous_interpolation=True)
    assert high_q_gains.kp >= scheduler.gains_track.kp * 0.95
    assert high_q_gains.ki > 0.05


def test_camera_controller_gain_adaptation():
    ctrl = PATCameraController()

    # 1. TRACK State
    track_state = PATState(mode=PATMode.TRACK, track_quality=0.85, pan_error_deg=0.5, tilt_error_deg=0.0)
    ctrl.compute_control_command(
        dt=0.016,
        pat_state=track_state,
        search_pan_rate=0.0,
        search_tilt_rate=0.0,
        reacquire_pan_rate=0.0,
        reacquire_tilt_rate=0.0,
    )
    assert ctrl.active_gains.kp > 1.2
    assert ctrl.active_gains.ki > 0.0

    # 2. DEGRADED State: gains relax, Ki drops to 0
    degraded_state = PATState(mode=PATMode.DEGRADED, track_quality=0.2, pan_error_deg=0.5, tilt_error_deg=0.0)
    ctrl.compute_control_command(
        dt=0.016,
        pat_state=degraded_state,
        search_pan_rate=0.0,
        search_tilt_rate=0.0,
        reacquire_pan_rate=0.0,
        reacquire_tilt_rate=0.0,
    )
    assert ctrl.active_gains.kp < 0.6
    assert ctrl.active_gains.ki == 0.0
    assert ctrl.active_gains.kd > 0.20


def test_degraded_mode_anti_windup_freezing():
    ctrl = PATCameraController()
    degraded_state = PATState(mode=PATMode.DEGRADED, track_quality=0.2, pan_error_deg=1.0, tilt_error_deg=0.0)

    # In DEGRADED mode, sustained error should not wind up the integral term
    for _ in range(20):
        ctrl.compute_control_command(
            dt=0.016,
            pat_state=degraded_state,
            search_pan_rate=0.0,
            search_tilt_rate=0.0,
            reacquire_pan_rate=0.0,
            reacquire_tilt_rate=0.0,
        )
    assert ctrl.pan_pid.integral == 0.0


def test_direct_angular_velocity_feedforward():
    ctrl = PATCameraController()
    track_state = PATState(mode=PATMode.TRACK, track_quality=0.9, pan_error_deg=0.0, tilt_error_deg=0.0)

    # Target moving at +2.0 deg/s pan, -1.5 deg/s tilt from 6-state IMM estimator
    cmd_pan, cmd_tilt, pid_p, pid_t, ff_p, ff_t, _ = ctrl.compute_control_command(
        dt=0.016,
        pat_state=track_state,
        search_pan_rate=0.0,
        search_tilt_rate=0.0,
        reacquire_pan_rate=0.0,
        reacquire_tilt_rate=0.0,
        estimated_omega_x_deg_s=2.0,
        estimated_omega_y_deg_s=-1.5,
    )
    assert ff_p > 0.5  # Positive feedforward rate commanded
    assert ff_t < -0.5
