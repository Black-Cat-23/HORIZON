"""
Phase 1 Optical Kinematics & Boresight Auto-Alignment Verification Tests
========================================================================
Verifies:
1. Boresight auto-alignment at t=0 across all 6 trajectory types (target centered within FOV).
2. Pinhole inverse tangent angle mapping accuracy vs. linear bounds.
3. Gimbal rate command scaling and closed-loop pointing error convergence.
"""

import math
import pytest
import numpy as np

from simulator.core.config import (
    AppConfig,
    SimulationConfig,
    TrajectoryConfig,
    CameraConfig,
    TargetConfig,
    TargetInitialPosition,
    CircularTrajectoryConfig,
    FigureEightTrajectoryConfig,
    SpiralTrajectoryConfig,
    SinusoidalTrajectoryConfig,
    RandomTrajectoryConfig,
    StraightTrajectoryConfig,
)
from simulator.core.simulation import SimulationEngine
from pat.tracking.track_manager import PATTrackManager
from control.camera_controller import PATCameraController
from pat.state import PATState, PATMode


@pytest.mark.parametrize(
    "traj_type", ["straight", "circular", "figure8", "random", "spiral", "sinusoidal"]
)
def test_boresight_auto_alignment_at_t0(traj_type: str) -> None:
    """Verify target projects inside FOV (near center) at t=0 for all trajectory types."""
    cfg = AppConfig(
        simulation=SimulationConfig(duration_seconds=2.0, seed=42),
        trajectory=TrajectoryConfig(
            type=traj_type,
            straight=StraightTrajectoryConfig(),
            circular=CircularTrajectoryConfig(),
            figure8=FigureEightTrajectoryConfig(),
            random=RandomTrajectoryConfig(),
            spiral=SpiralTrajectoryConfig(),
            sinusoidal=SinusoidalTrajectoryConfig(),
        ),
        target=TargetConfig(initial_position=TargetInitialPosition(x=1200.0, y=800.0)),
        camera=CameraConfig(max_initial_offset_deg=0.0, auto_align_boresight=True),
    )

    engine = SimulationEngine(cfg)
    engine.initialize()

    state = engine.get_current_state()
    camera = engine.camera
    theta_x, theta_y, u, v, in_fov = camera.project_target(state.x, state.y)

    assert in_fov is True, f"Target at t=0 must be inside camera FOV for trajectory '{traj_type}'"
    assert abs(u - 320.0) < 5.0, f"Target pixel u ({u:.2f}) must be near center (320) for '{traj_type}'"
    assert abs(v - 240.0) < 5.0, f"Target pixel v ({v:.2f}) must be near center (240) for '{traj_type}'"


def test_pinhole_optical_angle_trigonometry() -> None:
    """Verify PATTrackManager pinhole arctan angle computation accuracy."""
    tm = PATTrackManager(image_width_px=640, image_height_px=480, fov_pan_deg=4.0, fov_tilt_deg=3.0)

    # 1. Boresight center (320, 240) -> 0.0 error
    pan_err, tilt_err = tm.compute_pointing_error(320.0, 240.0)
    assert abs(pan_err) < 1e-6
    assert abs(tilt_err) < 1e-6

    # 2. Right edge (640, 240) -> pan_err == +2.0 deg
    pan_err, tilt_err = tm.compute_pointing_error(640.0, 240.0)
    assert abs(pan_err - 2.0) < 1e-4

    # 3. Top edge (320, 0) -> tilt_err == -1.5 deg
    pan_err, tilt_err = tm.compute_pointing_error(320.0, 0.0)
    assert abs(tilt_err - (-1.5)) < 1e-4


def test_gimbal_closed_loop_rate_convergence() -> None:
    """Verify PATCameraController computes non-saturating control rates for small errors."""
    ctrl = PATCameraController(controller_type="PID")
    pat_state = PATState(mode=PATMode.TRACK, pan_error_deg=0.5, tilt_error_deg=-0.3, track_quality=1.0)

    cmd_pan, cmd_tilt, _, _, _, _, is_sat = ctrl.compute_control_command(
        dt=0.0167,
        pat_state=pat_state,
        search_pan_rate=0.0,
        search_tilt_rate=0.0,
        reacquire_pan_rate=0.0,
        reacquire_tilt_rate=0.0,
        estimated_vx_px_s=10.0,
        estimated_vy_px_s=-5.0,
    )

    assert not is_sat, "Control command should not be saturated for 0.5 deg pointing error"
    assert cmd_pan > 0.0, "Pan command rate should be positive for positive pan error"
    assert cmd_tilt < 0.0, "Tilt command rate should be negative for negative tilt error"
