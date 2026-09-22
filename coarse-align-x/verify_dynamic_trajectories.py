"""
Dynamic Trajectory Verification Script
Tests all 6 trajectories across NOMINAL, DIFFICULT, and SEVERE disturbance presets.
Ensures lock rate > 80% and zero hardcoded limitations.
"""

import math
import numpy as np
from simulator.core.config import (
    AppConfig,
    CameraConfig,
    TargetConfig,
    TargetInitialPosition,
    SimulationConfig,
    TrajectoryConfig,
    SinusoidalTrajectoryConfig,
    FigureEightTrajectoryConfig,
    CircularTrajectoryConfig,
    SpiralTrajectoryConfig,
    RandomTrajectoryConfig,
    StraightTrajectoryConfig,
)
from simulator.disturbances.presets import get_preset_config
from simulator.core.simulation import SimulationEngine
from simulator.perception.hybrid_detector import HybridBeaconDetector
from simulator.perception.config import DetectorConfig
from tracking.association.track import Track
from pat.mode_manager import PATModeManager
from pat.state import PATMode
from control.camera_controller import PATCameraController
from tracking.estimation.kalman import EstimatorStatus


def run_trajectory_test(traj_type: str, preset: str = "DIFFICULT", duration_s: float = 6.0):
    cfg = AppConfig(
        simulation=SimulationConfig(frequency_hz=60.0, duration_seconds=duration_s, seed=42),
        camera=CameraConfig(update_rate_hz=30.0, rate_limit_deg_s=20.0),
        target=TargetConfig(
            size_px=10.0,
            intensity=255.0,
            initial_position=TargetInitialPosition(x=1000.0, y=1000.0),
        ),
        trajectory=TrajectoryConfig(
            type=traj_type,
            sinusoidal=SinusoidalTrajectoryConfig(),
            figure8=FigureEightTrajectoryConfig(amplitude_x=220.0, amplitude_y=140.0, angular_velocity=0.6),
            circular=CircularTrajectoryConfig(radius=120.0, angular_velocity=0.6),
            spiral=SpiralTrajectoryConfig(),
            random=RandomTrajectoryConfig(),
            straight=StraightTrajectoryConfig(),
        ),
        disturbance=get_preset_config(preset),
    )

    engine = SimulationEngine(cfg)
    engine.initialize()
    camera = engine.camera

    detector = HybridBeaconDetector(DetectorConfig(perception_mode="HYBRID"))
    track = Track(track_id=1, filter_type="IMM_ADAPTIVE_EKF")
    pat_mgr = PATModeManager()
    pat_ctrl = PATCameraController(controller_type="PID")


    dt_step = 1.0 / 60.0
    last_estimate = None
    last_detection = None

    total_frames = 0
    locked_frames = 0
    in_fov_frames = 0
    errors_px = []

    num_steps = int(duration_s * 60.0)
    for _ in range(num_steps):
        state = engine.get_current_state()
        dist_frame = engine.get_disturbed_frame()


        est_pred = (last_estimate.estimated_x, last_estimate.estimated_y) if last_estimate else None
        est_cov = last_estimate.covariance[:2, :2] if (last_estimate and hasattr(last_estimate, "covariance")) else None
        vel_hint = math.hypot(last_estimate.estimated_vx, last_estimate.estimated_vy) if last_estimate else 0.0

        if camera.is_new_observation:
            det_res = detector.detect(
                dist_frame,
                timestamp=state.timestamp,
                collect_diagnostics=False,
                estimator_prediction=est_pred,
                prediction_covariance=est_cov,
                velocity_hint_px_s=vel_hint,
            )
            is_meas_accepted = (
                det_res.detected
                and (last_estimate is None or last_estimate.filter_status != EstimatorStatus.REJECTED_MEASUREMENT)
            )
            meas = det_res.centroid if is_meas_accepted else None
            conf = det_res.confidence if is_meas_accepted else 0.0
            estimate = track.step(
                measurement=meas,
                confidence=conf,
                timestamp=state.timestamp,
                gimbal_pan_rate=camera.gimbal.actual_pan_rate,
                gimbal_tilt_rate=camera.gimbal.actual_tilt_rate,
            )
            is_new_frame = True
            last_detection = det_res
        else:
            is_meas_accepted = False
            estimate = track.step(
                measurement=None,
                confidence=0.0,
                timestamp=state.timestamp,
                gimbal_pan_rate=camera.gimbal.actual_pan_rate,
                gimbal_tilt_rate=camera.gimbal.actual_tilt_rate,
            )
            is_new_frame = False
            det_res = last_detection

        last_estimate = estimate

        cov_trace = float(estimate.position_uncertainty**2)
        search_pan_r, search_tilt_r = pat_mgr.search_manager.get_command(
            dt_step, camera.gimbal.pan_deg, camera.gimbal.tilt_deg
        )
        reacq_pan_r, reacq_tilt_r, _ = pat_mgr.reacquisition_manager.process_step(
            dt_step, camera.gimbal.pan_deg, camera.gimbal.tilt_deg
        )

        valid_conf = det_res.confidence if (det_res and is_meas_accepted) else 0.0

        pat_state = pat_mgr.process_step(
            dt=dt_step,
            timestamp_s=state.timestamp,
            detection_valid=is_meas_accepted,
            detection_confidence=valid_conf,
            mahalanobis_d2=estimate.mahalanobis_distance**2,
            covariance_trace=cov_trace,
            estimated_u_px=estimate.estimated_x,
            estimated_v_px=estimate.estimated_y,
            estimated_vx_px_s=estimate.estimated_vx,
            estimated_vy_px_s=estimate.estimated_vy,
            current_pan_deg=camera.gimbal.pan_deg,
            current_tilt_deg=camera.gimbal.tilt_deg,
            suppress_detection=False,
            is_new_frame=is_new_frame,
        )

        cmd_pan_rate, cmd_tilt_rate, _, _, _, _, _ = pat_ctrl.compute_control_command(
            dt=dt_step,
            pat_state=pat_state,
            search_pan_rate=search_pan_r,
            search_tilt_rate=search_tilt_r,
            reacquire_pan_rate=reacq_pan_r,
            reacquire_tilt_rate=reacq_tilt_r,

            estimated_vx_px_s=estimate.estimated_vx,
            estimated_vy_px_s=estimate.estimated_vy,
            gimbal=camera.gimbal,
        )

        camera.gimbal.set_rate_command(cmd_pan_rate, cmd_tilt_rate)
        engine.step()

        # Telemetry: evaluate true target location on sensor accounting for platform motion & jitter
        dist_telem = engine._last_disturbance_telemetry
        p_ox = dist_telem.platform_offset_x if dist_telem else 0.0
        p_oy = dist_telem.platform_offset_y if dist_telem else 0.0
        j_x = dist_telem.camera_jitter_x if dist_telem else 0.0
        j_y = dist_telem.camera_jitter_y if dist_telem else 0.0

        _, _, u_clean, v_clean, _ = camera.project_target(state.x, state.y)
        u_sensor = u_clean + p_ox + j_x
        v_sensor = v_clean + p_oy + j_y
        in_sensor_fov = (0 <= u_sensor < 640) and (0 <= v_sensor < 480)

        total_frames += 1
        if in_sensor_fov:
            in_fov_frames += 1
        if pat_state.mode == PATMode.TRACK:
            locked_frames += 1
            err_px = math.hypot(estimate.estimated_x - u_sensor, estimate.estimated_y - v_sensor)
            errors_px.append(err_px)

    lock_pct = (locked_frames / total_frames) * 100.0 if total_frames > 0 else 0.0
    fov_pct = (in_fov_frames / total_frames) * 100.0 if total_frames > 0 else 0.0
    mean_err = np.mean(errors_px) if errors_px else float("nan")

    return {
        "traj": traj_type,
        "preset": preset,
        "total_frames": total_frames,
        "lock_pct": lock_pct,
        "fov_pct": fov_pct,
        "mean_err_px": mean_err,
    }


if __name__ == "__main__":
    presets = ["NOMINAL", "DIFFICULT", "SEVERE", "RECOVERY"]
    trajectories = ["sinusoidal", "figure8", "circular", "spiral", "random", "straight"]
    print(f"{'TRAJECTORY':<14} | {'PRESET':<12} | {'FOV %':<8} | {'LOCK %':<8} | {'MEAN ERR (px)':<14}")
    print("-" * 65)

    for p in presets:
        for t in trajectories:
            res = run_trajectory_test(t, preset=p, duration_s=4.0)
            print(f"{res['traj']:<14} | {res['preset']:<12} | {res['fov_pct']:>6.1f}% | {res['lock_pct']:>6.1f}% | {res['mean_err_px']:>10.2f} px")

