"""
Unit tests for PAT Mode Manager and state machine transitions.
HORIZON Phase 6
"""

import pytest
from pat.mode_manager import PATModeManager
from pat.state import PATMode


def test_pat_initial_state():
    mgr = PATModeManager()
    assert mgr.state.mode == PATMode.SEARCH
    assert mgr.state.consecutive_hits == 0
    assert mgr.state.consecutive_misses == 0


def test_transition_search_to_acquire():
    mgr = PATModeManager()
    state = mgr.process_step(
        dt=0.016,
        timestamp_s=0.016,
        detection_valid=True,
        detection_confidence=0.8,
        mahalanobis_d2=1.0,
        covariance_trace=50.0,
        estimated_u_px=320.0,
        estimated_v_px=240.0,
        estimated_vx_px_s=0.0,
        estimated_vy_px_s=0.0,
        current_pan_deg=0.0,
        current_tilt_deg=0.0,
    )
    assert state.mode == PATMode.ACQUIRE
    assert mgr.diagnostics.events[-1].event_type == "CANDIDATE_FOUND"


def test_transition_acquire_to_track():
    mgr = PATModeManager()
    # Process 3 consecutive valid frames (acquire_required_frames = 3)
    for i in range(4):
        state = mgr.process_step(
            dt=0.016,
            timestamp_s=0.016 * (i + 1),
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
    assert state.mode == PATMode.TRACK


def test_transition_track_to_degraded_and_recovery():
    mgr = PATModeManager()
    # Lock onto track
    for i in range(4):
        mgr.process_step(
            dt=0.016,
            timestamp_s=0.016 * (i + 1),
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
    assert mgr.state.mode == PATMode.TRACK

    # Miss 2 frames -> DEGRADED
    for i in range(2):
        state = mgr.process_step(
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
    assert state.mode == PATMode.DEGRADED

    # Valid measurement recovered -> TRACK
    state = mgr.process_step(
        dt=0.016,
        timestamp_s=0.2,
        detection_valid=True,
        detection_confidence=0.9,
        mahalanobis_d2=0.2,
        covariance_trace=10.0,
        estimated_u_px=320.0,
        estimated_v_px=240.0,
        estimated_vx_px_s=0.0,
        estimated_vy_px_s=0.0,
        current_pan_deg=0.0,
        current_tilt_deg=0.0,
    )
    assert state.mode == PATMode.TRACK
