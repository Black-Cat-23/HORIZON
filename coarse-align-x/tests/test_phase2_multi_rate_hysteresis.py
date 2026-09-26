"""
Phase 2 Multi-Rate Sensor Synchronization & Hysteresis PAT State Machine Tests
================================================================================
Verifies:
1. 30 Hz camera sensor in 60 Hz simulation executes without false miss accumulation.
2. Multi-frame PAT hysteresis prevents premature drop to SEARCH during transient noise blackouts.
3. Velocity-projected reacquisition origin centers search spiral on target flight vector.
"""

import pytest
import numpy as np

from simulator.core.config import AppConfig, SimulationConfig, CameraConfig
from simulator.core.simulation import SimulationEngine
from tracking.association.track import Track
from pat.mode_manager import PATModeManager
from pat.state import PATMode, PATState
from pat.recovery.reacquisition import ReacquisitionManager


def test_multi_rate_sensor_decoupled_prediction() -> None:
    """Verify 30 Hz camera sensor in 60 Hz simulation does not accumulate false misses."""
    cfg = AppConfig(
        simulation=SimulationConfig(frequency_hz=60.0, duration_seconds=1.0, seed=42),
        camera=CameraConfig(update_rate_hz=30.0),
    )
    engine = SimulationEngine(cfg)
    engine.initialize()

    track = Track(track_id=1, filter_type="IMM_ADAPTIVE_EKF")

    # Step through 10 simulation frames (5 sensor capture steps, 5 intermediate predict ticks)
    for _ in range(10):
        engine.step()
        camera = engine.camera
        state = engine.get_current_state()

        if camera.is_new_observation:
            # Sensor frame step: update with true measurement
            est = track.step(
                measurement=(320.0, 240.0),
                confidence=0.9,
                timestamp=state.timestamp,
                is_sensor_step=True,
            )
        else:
            # Intermediate simulation tick: prediction only
            est = track.step(
                measurement=None,
                confidence=0.0,
                timestamp=state.timestamp,
                is_sensor_step=False,
            )

    # Misses should be 0 because all sensor steps were valid
    assert est.consecutive_misses == 0, f"Expected 0 consecutive misses, got {est.consecutive_misses}"


def test_transient_blackout_hysteresis_resilience() -> None:
    """Verify 2-frame optical blackout does not drop PAT mode from TRACK to SEARCH."""
    pat_mgr = PATModeManager()
    pat_mgr.state.mode = PATMode.TRACK
    pat_mgr.state.track_quality = 1.0

    # Frame 1: Valid detection
    pat_mgr.process_step(
        dt=0.0167,
        timestamp_s=1.0,
        detection_valid=True,
        detection_confidence=0.95,
        mahalanobis_d2=1.0,
        covariance_trace=2.0,
        estimated_u_px=320.0,
        estimated_v_px=240.0,
        estimated_vx_px_s=10.0,
        estimated_vy_px_s=0.0,
        current_pan_deg=0.0,
        current_tilt_deg=0.0,
        is_new_frame=True,
    )
    assert pat_mgr.state.mode == PATMode.TRACK

    # Frame 2 & 3: Transient 2-frame optical blackout (missed detection)
    for t in [1.0167, 1.0333]:
        pat_mgr.process_step(
            dt=0.0167,
            timestamp_s=t,
            detection_valid=False,
            detection_confidence=0.0,
            mahalanobis_d2=0.0,
            covariance_trace=2.0,
            estimated_u_px=320.0,
            estimated_v_px=240.0,
            estimated_vx_px_s=10.0,
            estimated_vy_px_s=0.0,
            current_pan_deg=0.0,
            current_tilt_deg=0.0,
            is_new_frame=True,
        )

    # State should remain in TRACK or DEGRADED, NOT SEARCH
    assert pat_mgr.state.mode != PATMode.SEARCH, "Transient 2-frame blackout must NOT cause drop to SEARCH mode"


def test_velocity_projected_reacquisition_origin() -> None:
    """Verify ReacquisitionManager projects search center along velocity vector."""
    rm = ReacquisitionManager()

    # Start reacquisition at pan=1.0°, tilt=0.5° with vx=5.0 deg/s, vy=-2.0 deg/s over lead_time=0.2s
    rm.start_reacquisition(
        center_pan_deg=1.0,
        center_tilt_deg=0.5,
        estimated_vx_deg_s=5.0,
        estimated_vy_deg_s=-2.0,
        lead_time_s=0.2,
    )

    assert rm.active is True
    # Projected pan = 1.0 + 5.0 * 0.2 = 2.0°
    # Projected tilt = 0.5 + (-2.0) * 0.2 = 0.1°
    assert abs(rm.search_strategy.center_pan_deg - 2.0) < 1e-4
    assert abs(rm.search_strategy.center_tilt_deg - 0.1) < 1e-4
