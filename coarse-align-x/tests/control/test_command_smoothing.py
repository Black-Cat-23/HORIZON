"""
Unit Tests for Anti-Hunting Command Smoothing and Rate-of-Change Limiting.
HORIZON Phase 6
"""

import numpy as np
import pytest
from pat.state import PATMode, PATState
from control.camera_controller import PATCameraController


def test_command_smoothing_rate_of_change_clamping():
    """Verifies that acceleration step changes are clamped within max_rate_change_deg_s2."""
    max_accel = 20.0
    dt = 0.02
    ctrl = PATCameraController(max_rate_change_deg_s2=max_accel)

    # Initial zero state
    state = PATState(mode=PATMode.TRACK, pan_error_deg=0.0, tilt_error_deg=0.0, track_quality=1.0)
    ctrl.compute_control_command(dt, state, 0, 0, 0, 0)

    # Sudden jump in error requiring high rate
    state.pan_error_deg = 5.0
    cmd_pan, _, _, _, _, _, _ = ctrl.compute_control_command(dt, state, 0, 0, 0, 0)

    # Commanded change must not exceed max_accel * dt
    assert abs(cmd_pan) <= max_accel * dt + 1e-5


def test_command_smoothing_eliminates_noise_hunting():
    """Verifies that high-frequency noise oscillations are smoothed out."""
    ctrl_unsmoothed = PATCameraController(max_rate_change_deg_s2=1000.0)
    ctrl_smoothed = PATCameraController(max_rate_change_deg_s2=30.0)

    dt = 0.016
    np.random.seed(42)
    noise_sequence = np.random.normal(0, 0.5, size=50)

    cmds_raw = []
    cmds_smooth = []

    for n in noise_sequence:
        state = PATState(mode=PATMode.TRACK, pan_error_deg=float(n), tilt_error_deg=0.0, track_quality=0.8)
        c_raw, _, _, _, _, _, _ = ctrl_unsmoothed.compute_control_command(dt, state, 0, 0, 0, 0)
        c_smooth, _, _, _, _, _, _ = ctrl_smoothed.compute_control_command(dt, state, 0, 0, 0, 0)
        cmds_raw.append(c_raw)
        cmds_smooth.append(c_smooth)

    # Variation of smoothed commands should be significantly less than raw
    var_raw = np.std(np.diff(cmds_raw))
    var_smooth = np.std(np.diff(cmds_smooth))

    assert var_smooth < var_raw
