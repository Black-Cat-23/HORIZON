"""
Performance and Timing Invariant Tests for PAT Loop Execution.
HORIZON Phase 6
"""

import time
import numpy as np
import pytest
from pat.mode_manager import PATModeManager
from pat.state import PATMode, PATState
from control.camera_controller import PATCameraController


def test_pat_mode_manager_cycle_latency():
    """Verifies that PATModeManager cycle executes in < 0.5 ms."""
    mgr = PATModeManager()
    
    latencies_ms = []
    for _ in range(100):
        t0 = time.perf_counter()
        mgr.process_step(
            dt=0.016, timestamp_s=0.016, detection_valid=True, detection_confidence=0.9,
            mahalanobis_d2=0.5, covariance_trace=10.0, estimated_u_px=320, estimated_v_px=240,
            estimated_vx_px_s=0, estimated_vy_px_s=0, current_pan_deg=0, current_tilt_deg=0
        )
        t1 = time.perf_counter()
        latencies_ms.append((t1 - t0) * 1000.0)

    avg_lat = float(np.mean(latencies_ms))
    assert avg_lat < 0.5, f"PAT Mode Manager average latency {avg_lat:.4f} ms exceeds 0.5 ms limit"


def test_controller_command_computation_latency():
    """Verifies that PATCameraController computation executes in < 0.2 ms."""
    ctrl = PATCameraController()
    state = PATState(mode=PATMode.TRACK, pan_error_deg=1.5, tilt_error_deg=-0.8, track_quality=0.85)

    latencies_ms = []
    for _ in range(100):
        t0 = time.perf_counter()
        ctrl.compute_control_command(
            dt=0.016, pat_state=state, search_pan_rate=0.0, search_tilt_rate=0.0,
            reacquire_pan_rate=0.0, reacquire_tilt_rate=0.0,
            estimated_vx_px_s=50.0, estimated_vy_px_s=-30.0,
        )
        t1 = time.perf_counter()
        latencies_ms.append((t1 - t0) * 1000.0)

    avg_lat = float(np.mean(latencies_ms))
    assert avg_lat < 0.2, f"Controller compute latency {avg_lat:.4f} ms exceeds 0.2 ms limit"
