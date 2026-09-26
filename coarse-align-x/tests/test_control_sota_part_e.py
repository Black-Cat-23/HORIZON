"""Unit tests for Phase E: Closed-Loop PAT Control & Predictor Engine SOTA Upgrades."""

import math
import numpy as np
import pytest

from control.camera_controller import PATCameraController
from control.feedforward import SCurveFeedForward, VelocityFeedForward
from control.lqg_controller import LQGConfig, LQGController
from control.smith_predictor import SmithPredictor, SmithPredictorConfig
from pat.state import PATMode, PATState


def test_smith_predictor_delay_compensation():
    """Verify SmithPredictor delay-free error prediction."""
    sp = SmithPredictor(SmithPredictorConfig(latency_seconds=0.05, buffer_dt_s=0.01))
    sp.reset()

    # Step through sequence of pointing errors and control inputs
    err_pan, err_tilt = sp.predict_error(
        measured_pan_error_deg=2.0,
        measured_tilt_error_deg=-1.0,
        cmd_pan_rate_deg_s=5.0,
        cmd_tilt_rate_deg_s=-2.0,
        dt=0.01,
    )

    assert isinstance(err_pan, float)
    assert isinstance(err_tilt, float)
    assert math.isfinite(err_pan)
    assert math.isfinite(err_tilt)


def test_lqg_optimal_state_regulator():
    """Verify LQG Riccati solver convergence and control output."""
    lqg = LQGController(LQGConfig(q_pos_weight=100.0, r_control_cost=0.1))
    u_cmd = lqg.compute(error_pos_deg=1.5, error_vel_deg_s=0.5, dt=0.01)

    assert isinstance(u_cmd, float)
    assert abs(u_cmd) > 0.0
    assert abs(u_cmd) <= 60.0
    assert lqg._k_gain is not None


def test_scurve_jerk_limited_feedforward():
    """Verify 3rd-order S-Curve jerk-limited feedforward profiler."""
    scurve = SCurveFeedForward(kff_pan=1.0, kff_tilt=1.0, max_accel_deg_s2=100.0, max_jerk_deg_s3=500.0)
    scurve.reset()

    # Step input to velocity
    v_pan, v_tilt = scurve.compute(target_pan_vel_deg_s=10.0, target_tilt_vel_deg_s=5.0, dt=0.01)

    # First step velocity should be smooth and limited by jerk
    assert abs(v_pan) < 10.0
    assert abs(v_tilt) < 5.0

    # Step through multiple cycles to reach target velocity smoothly
    for _ in range(50):
        v_pan, v_tilt = scurve.compute(target_pan_vel_deg_s=10.0, target_tilt_vel_deg_s=5.0, dt=0.01)

    assert abs(v_pan - 10.0) < 0.5
    assert abs(v_tilt - 5.0) < 0.5


def test_pat_camera_controller_lqg_adrc_integration():
    """Verify PATCameraController mode execution across PID, ADRC, and LQG controller types."""
    pat_state = PATState(
        mode=PATMode.TRACK,
        pan_error_deg=0.5,
        tilt_error_deg=-0.3,
        track_quality=0.9,
    )

    for ctype in ["PID", "ADRC", "LQG"]:
        ctrl = PATCameraController(controller_type=ctype)
        res = ctrl.compute_control_command(
            dt=0.01,
            pat_state=pat_state,
            search_pan_rate=0.0,
            search_tilt_rate=0.0,
            reacquire_pan_rate=0.0,
            reacquire_tilt_rate=0.0,
            estimated_vx_px_s=10.0,
            estimated_vy_px_s=-5.0,
        )

        actual_pan, actual_tilt, pid_p, pid_t, ff_p, ff_t, sat = res
        assert math.isfinite(actual_pan)
        assert math.isfinite(actual_tilt)
        assert isinstance(sat, bool)
