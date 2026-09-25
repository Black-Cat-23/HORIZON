"""
Integration Tests for PAT Recovery State Transitions.
HORIZON Phase 6
"""

import pytest
from pat.mode_manager import PATModeManager
from pat.state import PATMode
from pat.thresholds import PATThresholds


def test_full_recovery_transition_cycle():
    """
    Verifies full state machine transitions under optical dropout:
    SEARCH -> ACQUIRE -> TRACK -> DEGRADED -> REACQUIRE -> ACQUIRE -> TRACK
    """
    thresholds = PATThresholds(
        acquire_required_frames=2,
        degraded_miss_frames=2,
        reacquire_trigger_frames=4,
    )
    mgr = PATModeManager(thresholds=thresholds)

    # 1. Start in SEARCH
    assert mgr.state.mode == PATMode.SEARCH

    # 2. Candidate observed -> ACQUIRE
    mgr.process_step(
        dt=0.016, timestamp_s=0.016, detection_valid=True, detection_confidence=0.9,
        mahalanobis_d2=0.2, covariance_trace=5.0, estimated_u_px=320, estimated_v_px=240,
        estimated_vx_px_s=0, estimated_vy_px_s=0, current_pan_deg=0, current_tilt_deg=0
    )
    assert mgr.state.mode == PATMode.ACQUIRE

    # 3. Candidate confirmed across 2 acquire frames -> TRACK
    for i in range(2):
        mgr.process_step(
            dt=0.016, timestamp_s=0.032 + i * 0.016, detection_valid=True, detection_confidence=0.9,
            mahalanobis_d2=0.2, covariance_trace=5.0, estimated_u_px=320, estimated_v_px=240,
            estimated_vx_px_s=0, estimated_vy_px_s=0, current_pan_deg=0, current_tilt_deg=0
        )
    assert mgr.state.mode == PATMode.TRACK

    # 4. Target loss for 2 frames -> DEGRADED
    for i in range(2):
        mgr.process_step(
            dt=0.016, timestamp_s=0.064 + i * 0.016, detection_valid=False, detection_confidence=0.0,
            mahalanobis_d2=0.0, covariance_trace=20.0, estimated_u_px=320, estimated_v_px=240,
            estimated_vx_px_s=0, estimated_vy_px_s=0, current_pan_deg=0, current_tilt_deg=0
        )
    assert mgr.state.mode == PATMode.DEGRADED

    # 5. Persistent loss for 2 more frames -> REACQUIRE
    for i in range(2):
        mgr.process_step(
            dt=0.016, timestamp_s=0.096 + i * 0.016, detection_valid=False, detection_confidence=0.0,
            mahalanobis_d2=0.0, covariance_trace=50.0, estimated_u_px=320, estimated_v_px=240,
            estimated_vx_px_s=0, estimated_vy_px_s=0, current_pan_deg=0, current_tilt_deg=0
        )
    assert mgr.state.mode == PATMode.REACQUIRE

    # 6. Target re-detected -> ACQUIRE -> TRACK
    mgr.process_step(
        dt=0.016, timestamp_s=0.128, detection_valid=True, detection_confidence=0.95,
        mahalanobis_d2=0.1, covariance_trace=5.0, estimated_u_px=320, estimated_v_px=240,
        estimated_vx_px_s=0, estimated_vy_px_s=0, current_pan_deg=0, current_tilt_deg=0
    )
    assert mgr.state.mode == PATMode.ACQUIRE

    for i in range(2):
        mgr.process_step(
            dt=0.016, timestamp_s=0.144 + i * 0.016, detection_valid=True, detection_confidence=0.95,
            mahalanobis_d2=0.1, covariance_trace=5.0, estimated_u_px=320, estimated_v_px=240,
            estimated_vx_px_s=0, estimated_vy_px_s=0, current_pan_deg=0, current_tilt_deg=0
        )
    assert mgr.state.mode == PATMode.TRACK
