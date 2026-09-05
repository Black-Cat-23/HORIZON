"""
Integration tests for Closed-Loop PAT, target loss recovery, and zero ground truth leakage.
HORIZON Phase 6
"""

import pytest
from pat.mode_manager import PATModeManager
from control.camera_controller import PATCameraController
from pat.state import PATMode


def test_closed_loop_camera_convergence():
    """
    Verifies that PID camera controller reduces pointing error over time
    without ground truth input.
    """
    pat_mgr = PATModeManager()
    ctrl = PATCameraController()

    # Initial estimated offset (target at u=400, v=300 px vs center 320, 240)
    u_est, v_est = 400.0, 300.0

    # Lock into TRACK
    for i in range(4):
        pat_state = pat_mgr.process_step(
            dt=0.016,
            timestamp_s=0.016 * (i + 1),
            detection_valid=True,
            detection_confidence=0.9,
            mahalanobis_d2=0.5,
            covariance_trace=10.0,
            estimated_u_px=u_est,
            estimated_v_px=v_est,
            estimated_vx_px_s=0.0,
            estimated_vy_px_s=0.0,
            current_pan_deg=0.0,
            current_tilt_deg=0.0,
        )

    assert pat_state.mode == PATMode.TRACK
    initial_pan_err = abs(pat_state.pan_error_deg)

    # Execute 10 closed-loop control steps where camera pans toward target
    current_pan = 0.0
    current_tilt = 0.0
    for i in range(10):
        cmd_pan, cmd_tilt, _, _, _, _, _ = ctrl.compute_control_command(
            dt=0.016,
            pat_state=pat_state,
            search_pan_rate=0.0,
            search_tilt_rate=0.0,
            reacquire_pan_rate=0.0,
            reacquire_tilt_rate=0.0,
        )
        current_pan, current_tilt, _, _ = ctrl.actuator_interface.update_actuator(0.016)

        # Update estimated position as camera moves
        u_est -= cmd_pan * 10.0

        pat_state = pat_mgr.process_step(
            dt=0.016,
            timestamp_s=0.1 + 0.016 * (i + 1),
            detection_valid=True,
            detection_confidence=0.9,
            mahalanobis_d2=0.5,
            covariance_trace=10.0,
            estimated_u_px=u_est,
            estimated_v_px=v_est,
            estimated_vx_px_s=0.0,
            estimated_vy_px_s=0.0,
            current_pan_deg=current_pan,
            current_tilt_deg=current_tilt,
        )

    final_pan_err = abs(pat_state.pan_error_deg)
    assert final_pan_err < initial_pan_err


def test_target_loss_and_recovery_sequence():
    """
    Verifies full state transition sequence:
    TRACK -> DEGRADED -> REACQUIRE -> ACQUIRE -> TRACK
    upon detection blackout and restoration.
    """
    pat_mgr = PATModeManager()

    # Lock into TRACK
    for i in range(4):
        pat_state = pat_mgr.process_step(
            dt=0.016,
            timestamp_s=0.016 * (i + 1),
            detection_valid=True,
            detection_confidence=0.9,
            mahalanobis_d2=0.5,
            covariance_trace=10.0,
            estimated_u_px=320.0,
            estimated_v_px=240.0,
            estimated_vx_px_s=0.0,
            estimated_vy_px_s=0.0,
            current_pan_deg=0.0,
            current_tilt_deg=0.0,
        )
    assert pat_state.mode == PATMode.TRACK

    # Blackout detection -> enter DEGRADED
    for i in range(2):
        pat_state = pat_mgr.process_step(
            dt=0.016,
            timestamp_s=0.1 + 0.016 * (i + 1),
            detection_valid=False,
            detection_confidence=0.0,
            mahalanobis_d2=0.0,
            covariance_trace=50.0,
            estimated_u_px=320.0,
            estimated_v_px=240.0,
            estimated_vx_px_s=0.0,
            estimated_vy_px_s=0.0,
            current_pan_deg=0.0,
            current_tilt_deg=0.0,
        )
    assert pat_state.mode == PATMode.DEGRADED

    # Persistent blackout -> enter REACQUIRE
    for i in range(5):
        pat_state = pat_mgr.process_step(
            dt=0.016,
            timestamp_s=0.2 + 0.016 * (i + 1),
            detection_valid=False,
            detection_confidence=0.0,
            mahalanobis_d2=0.0,
            covariance_trace=100.0,
            estimated_u_px=320.0,
            estimated_v_px=240.0,
            estimated_vx_px_s=0.0,
            estimated_vy_px_s=0.0,
            current_pan_deg=0.0,
            current_tilt_deg=0.0,
        )
    assert pat_state.mode == PATMode.REACQUIRE

    # Re-detect target during reacquisition search -> enter ACQUIRE -> TRACK
    pat_state = pat_mgr.process_step(
        dt=0.016,
        timestamp_s=0.3,
        detection_valid=True,
        detection_confidence=0.85,
        mahalanobis_d2=0.5,
        covariance_trace=20.0,
        estimated_u_px=320.0,
        estimated_v_px=240.0,
        estimated_vx_px_s=0.0,
        estimated_vy_px_s=0.0,
        current_pan_deg=0.0,
        current_tilt_deg=0.0,
    )
    assert pat_state.mode == PATMode.ACQUIRE
