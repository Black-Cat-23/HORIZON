"""
Unit and Integration Tests for Predictive Pointing & Delay Compensation.
HORIZON Phase 6
"""

import pytest
from pat.state import PATMode, PATState
from control.camera_controller import PATCameraController


def test_predictive_pointing_leads_error():
    """Verifies that forward extrapolation anticipates moving target position."""
    ctrl_standard = PATCameraController(lead_time_s=0.0, max_rate_change_deg_s2=1000.0)
    ctrl_predictive = PATCameraController(lead_time_s=0.1, max_rate_change_deg_s2=1000.0)

    state = PATState(
        mode=PATMode.TRACK,
        pan_error_deg=0.5,
        tilt_error_deg=0.2,
        track_quality=1.0,
    )

    # Moderate target velocity moving along pan (+1 deg/s)
    pan_vel_deg_s = 1.0
    tilt_vel_deg_s = 0.5
    est_vx_px = pan_vel_deg_s * (640.0 / 4.0)
    est_vy_px = tilt_vel_deg_s * (480.0 / 3.0)

    cmd_std, _, _, _, _, _, _ = ctrl_standard.compute_control_command(
        dt=0.016,
        pat_state=state,
        search_pan_rate=0.0,
        search_tilt_rate=0.0,
        reacquire_pan_rate=0.0,
        reacquire_tilt_rate=0.0,
        estimated_vx_px_s=est_vx_px,
        estimated_vy_px_s=est_vy_px,
    )

    cmd_pred, _, _, _, _, _, _ = ctrl_predictive.compute_control_command(
        dt=0.016,
        pat_state=state,
        search_pan_rate=0.0,
        search_tilt_rate=0.0,
        reacquire_pan_rate=0.0,
        reacquire_tilt_rate=0.0,
        estimated_vx_px_s=est_vx_px,
        estimated_vy_px_s=est_vy_px,
    )

    # Predictive controller command should be larger to anticipate lead distance
    assert cmd_pred > cmd_std


def test_predictive_pointing_degraded_suppression():
    """Verifies that lead extrapolation is suppressed when track quality is low."""
    ctrl = PATCameraController(lead_time_s=0.1, max_rate_change_deg_s2=1000.0)

    state_good = PATState(mode=PATMode.TRACK, pan_error_deg=0.5, tilt_error_deg=0.0, track_quality=1.0)
    state_bad = PATState(mode=PATMode.DEGRADED, pan_error_deg=0.5, tilt_error_deg=0.0, track_quality=0.0)

    est_vx_px = 1.0 * (640.0 / 4.0)

    cmd_good, _, _, _, _, _, _ = ctrl.compute_control_command(
        dt=0.016, pat_state=state_good, search_pan_rate=0.0, search_tilt_rate=0.0,
        reacquire_pan_rate=0.0, reacquire_tilt_rate=0.0, estimated_vx_px_s=est_vx_px,
    )

    cmd_bad, _, _, _, _, _, _ = ctrl.compute_control_command(
        dt=0.016, pat_state=state_bad, search_pan_rate=0.0, search_tilt_rate=0.0,
        reacquire_pan_rate=0.0, reacquire_tilt_rate=0.0, estimated_vx_px_s=est_vx_px,
    )

    assert cmd_good > cmd_bad
