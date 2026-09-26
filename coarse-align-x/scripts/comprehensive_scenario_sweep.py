"""
Comprehensive Automated Scenario Sweep for HORIZON Virtual Camera Tracking System
Validates closed-loop tracking performance across:
- Trajectories: straight, circular, figure8, random, sinusoidal, spiral
- Controllers: ADRC, PID, LQG
- Estimators: IMM_ADAPTIVE_EKF, EKF
- Disturbance Presets: NOMINAL, DIFFICULT, SEVERE
- Target Sizes: 5 px, 10 px, 20 px
Produces quantitative SIH26169 benchmark metrics and statistical summaries.
"""

import sys
import os
import math
import time
import json
from typing import Dict, Any, List, Optional
import numpy as np

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

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


def run_scenario(
    traj_type: str,
    controller_type: str = "ADRC",
    filter_type: str = "IMM_ADAPTIVE_EKF",
    preset: str = "NOMINAL",
    target_size_px: float = 10.0,
    duration_s: float = 3.0,
    seed: int = 42,
) -> Dict[str, Any]:
    cfg = AppConfig(
        simulation=SimulationConfig(frequency_hz=60.0, duration_seconds=duration_s, seed=seed),
        camera=CameraConfig(update_rate_hz=30.0, rate_limit_deg_s=20.0),
        target=TargetConfig(
            size_px=target_size_px,
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
    track = Track(track_id=1, filter_type=filter_type)
    pat_mgr = PATModeManager()
    pat_ctrl = PATCameraController(controller_type=controller_type)

    dt_step = 1.0 / 60.0
    last_estimate = None
    last_detection = None

    total_frames = 0
    locked_frames = 0
    in_fov_frames = 0
    errors_px: List[float] = []

    acquisition_time_s: Optional[float] = None
    reacquisition_events: List[float] = []
    reacq_start_time: Optional[float] = None
    prev_mode = None

    num_steps = int(duration_s * 60.0)
    for _ in range(num_steps):
        state = engine.get_current_state()
        dist_frame = engine.get_disturbed_frame()

        if (
            last_estimate
            and last_estimate.track_age > 2
            and pat_mgr.state.mode in (PATMode.TRACK, PATMode.DEGRADED)
        ):
            est_pred = (last_estimate.predicted_x, last_estimate.predicted_y)
            est_cov = last_estimate.covariance[:2, :2] if hasattr(last_estimate, "covariance") else None
            vel_hint = math.hypot(last_estimate.estimated_vx, last_estimate.estimated_vy)
        else:
            est_pred = None
            est_cov = None
            vel_hint = 0.0

        if camera.is_new_observation:
            det_res = detector.detect(
                dist_frame,
                timestamp=state.timestamp,
                collect_diagnostics=False,
                estimator_prediction=est_pred,
                prediction_covariance=est_cov,
                velocity_hint_px_s=vel_hint,
            )
            is_meas_accepted = det_res.detected
            meas = det_res.centroid if is_meas_accepted else None
            conf = det_res.confidence if is_meas_accepted else 0.0
            estimate = track.step(
                measurement=meas,
                confidence=conf,
                timestamp=state.timestamp,
                gimbal_pan_rate=camera.gimbal.actual_pan_rate,
                gimbal_tilt_rate=camera.gimbal.actual_tilt_rate,
                is_sensor_step=True,
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
                is_sensor_step=False,
            )
            is_new_frame = False
            det_res = last_detection

        last_estimate = estimate

        cov_trace = float(estimate.position_uncertainty**2)
        if pat_mgr.state.mode == PATMode.SEARCH:
            search_pan_r, search_tilt_r = pat_mgr.search_manager.get_command(
                dt_step, camera.gimbal.pan_deg, camera.gimbal.tilt_deg
            )
        else:
            search_pan_r, search_tilt_r = 0.0, 0.0

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
            reacquire_pan_rate=pat_state.reacquire_pan_rate,
            reacquire_tilt_rate=pat_state.reacquire_tilt_rate,
            estimated_vx_px_s=estimate.estimated_vx,
            estimated_vy_px_s=estimate.estimated_vy,
            gimbal=camera.gimbal,
        )

        camera.gimbal.set_rate_command(cmd_pan_rate, cmd_tilt_rate)

        # Mode Transition Tracking
        if prev_mode is not None:
            if pat_state.mode == PATMode.TRACK and acquisition_time_s is None:
                acquisition_time_s = state.timestamp
            if prev_mode != PATMode.REACQUIRE and pat_state.mode == PATMode.REACQUIRE:
                reacq_start_time = state.timestamp
            elif prev_mode == PATMode.REACQUIRE and pat_state.mode == PATMode.TRACK and reacq_start_time is not None:
                reacquisition_events.append(state.timestamp - reacq_start_time)
                reacq_start_time = None
        elif pat_state.mode == PATMode.TRACK and acquisition_time_s is None:
            acquisition_time_s = state.timestamp

        prev_mode = pat_state.mode

        # Sensor FOV and Error Telemetry
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
        if pat_state.mode in (PATMode.TRACK, PATMode.DEGRADED):
            locked_frames += 1
            err = math.hypot(u_sensor - 320.0, v_sensor - 240.0)
            errors_px.append(err)

        engine.step()

    fov_pct = (in_fov_frames / total_frames * 100.0) if total_frames > 0 else 0.0
    lock_pct = (locked_frames / total_frames * 100.0) if total_frames > 0 else 0.0

    err_arr = np.array(errors_px) if len(errors_px) > 0 else np.array([float("nan")])
    mean_err = float(np.mean(err_arr))
    rmse_err = float(np.sqrt(np.mean(err_arr**2)))
    p95_err = float(np.percentile(err_arr, 95)) if len(errors_px) > 0 else float("nan")
    p99_err = float(np.percentile(err_arr, 99)) if len(errors_px) > 0 else float("nan")

    avg_reacq_s = float(np.mean(reacquisition_events)) if len(reacquisition_events) > 0 else 0.0

    return {
        "traj": traj_type,
        "controller": controller_type,
        "estimator": filter_type,
        "preset": preset,
        "target_size_px": target_size_px,
        "fov_pct": fov_pct,
        "lock_pct": lock_pct,
        "acq_time_s": acquisition_time_s if acquisition_time_s is not None else duration_s,
        "avg_reacq_s": avg_reacq_s,
        "mean_err_px": mean_err,
        "rmse_err_px": rmse_err,
        "p95_err_px": p95_err,
        "p99_err_px": p99_err,
    }


def main():
    print("=" * 80)
    print("HORIZON VIRTUAL CAMERA TRACKING SYSTEM — COMPREHENSIVE SCENARIO SWEEP")
    print("=" * 80)

    # 1. Primary Trajectory × Controller Matrix (Nominal Disturbance, IMM-EKF, 10px target)
    trajectories = ["straight", "circular", "figure8", "sinusoidal", "random", "spiral"]
    controllers = ["ADRC", "PID", "LQG"]
    estimators = ["IMM_ADAPTIVE_EKF", "EKF"]
    presets = ["NOMINAL", "DIFFICULT", "SEVERE"]
    target_sizes = [5.0, 10.0, 20.0]

    all_results: List[Dict[str, Any]] = []

    print("\n[PART 1/4] TRAJECTORIES × CONTROLLERS (Preset=NOMINAL, Estimator=IMM_ADAPTIVE_EKF, Size=10px)")
    print(f"{'TRAJECTORY':<12} | {'CTRL':<5} | {'FOV %':<7} | {'LOCK %':<7} | {'ACQ (s)':<8} | {'MEAN ERR':<9} | {'RMSE':<9} | {'P95':<9}")
    print("-" * 75)
    for t in trajectories:
        for c in controllers:
            res = run_scenario(traj_type=t, controller_type=c, filter_type="IMM_ADAPTIVE_EKF", preset="NOMINAL", target_size_px=10.0, duration_s=3.0)
            all_results.append(res)
            print(f"{res['traj']:<12} | {res['controller']:<5} | {res['fov_pct']:>6.1f}% | {res['lock_pct']:>6.1f}% | {res['acq_time_s']:>6.3f}s | {res['mean_err_px']:>7.2f}px | {res['rmse_err_px']:>7.2f}px | {res['p95_err_px']:>7.2f}px", flush=True)

    print("\n[PART 2/4] DISTURBANCE ROBUSTNESS SWEEP (Trajectory=figure8 & circular, Controller=ADRC & PID)")
    print(f"{'PRESET':<10} | {'TRAJ':<10} | {'CTRL':<5} | {'FOV %':<7} | {'LOCK %':<7} | {'ACQ (s)':<8} | {'MEAN ERR':<9} | {'RMSE':<9}")
    print("-" * 75)
    for p in ["DIFFICULT", "SEVERE"]:
        for t in ["figure8", "circular"]:
            for c in ["ADRC", "PID"]:
                res = run_scenario(traj_type=t, controller_type=c, filter_type="IMM_ADAPTIVE_EKF", preset=p, target_size_px=10.0, duration_s=3.0)
                all_results.append(res)
                print(f"{res['preset']:<10} | {res['traj']:<10} | {res['controller']:<5} | {res['fov_pct']:>6.1f}% | {res['lock_pct']:>6.1f}% | {res['acq_time_s']:>6.3f}s | {res['mean_err_px']:>7.2f}px | {res['rmse_err_px']:>7.2f}px", flush=True)

    print("\n[PART 3/4] ESTIMATOR COMPARISON (IMM-EKF vs EKF, Trajectory=sinusoidal & random, Controller=ADRC)")
    print(f"{'ESTIMATOR':<18} | {'TRAJ':<12} | {'FOV %':<7} | {'LOCK %':<7} | {'ACQ (s)':<8} | {'MEAN ERR':<9} | {'RMSE':<9}")
    print("-" * 75)
    for est in estimators:
        for t in ["sinusoidal", "random"]:
            res = run_scenario(traj_type=t, controller_type="ADRC", filter_type=est, preset="NOMINAL", target_size_px=10.0, duration_s=3.0)
            all_results.append(res)
            print(f"{res['estimator']:<18} | {res['traj']:<12} | {res['fov_pct']:>6.1f}% | {res['lock_pct']:>6.1f}% | {res['acq_time_s']:>6.3f}s | {res['mean_err_px']:>7.2f}px | {res['rmse_err_px']:>7.2f}px", flush=True)

    print("\n[PART 4/4] TARGET SCALE INVARIANCE (5px, 10px, 20px, Trajectory=figure8, Controller=ADRC)")
    print(f"{'SIZE (px)':<10} | {'TRAJ':<10} | {'FOV %':<7} | {'LOCK %':<7} | {'ACQ (s)':<8} | {'MEAN ERR':<9} | {'RMSE':<9}")
    print("-" * 75)
    for sz in [5.0, 20.0]:
        res = run_scenario(traj_type="figure8", controller_type="ADRC", filter_type="IMM_ADAPTIVE_EKF", preset="NOMINAL", target_size_px=sz, duration_s=3.0)
        all_results.append(res)
        print(f"{res['target_size_px']:<10.1f} | {res['traj']:<10} | {res['fov_pct']:>6.1f}% | {res['lock_pct']:>6.1f}% | {res['acq_time_s']:>6.3f}s | {res['mean_err_px']:>7.2f}px | {res['rmse_err_px']:>7.2f}px", flush=True)

    # Save results to JSON
    out_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "comprehensive_sweep_results.json"))
    with open(out_path, "w") as f:
        json.dump(all_results, f, indent=2)
    print(f"\nSaved {len(all_results)} scenario benchmark results to {out_path}")

    # Summary Statistics
    avg_fov = np.mean([r["fov_pct"] for r in all_results])
    avg_lock = np.mean([r["lock_pct"] for r in all_results])
    valid_errs = [r["mean_err_px"] for r in all_results if not math.isnan(r["mean_err_px"])]
    avg_mean_err = np.mean(valid_errs)
    valid_rmses = [r["rmse_err_px"] for r in all_results if not math.isnan(r["rmse_err_px"])]
    avg_rmse = np.mean(valid_rmses)
    avg_acq = np.mean([r["acq_time_s"] for r in all_results])

    print("\n" + "=" * 80)
    print("GLOBAL BENCHMARK AGGREGATE SUMMARY:")
    print(f"Total Scenarios Tested : {len(all_results)}")
    print(f"Mean FOV Retention     : {avg_fov:.1f}% (Threshold: >= 95.0%)")
    print(f"Mean Lock Retention    : {avg_lock:.1f}% (Threshold: >= 85.0%)")
    print(f"Mean Tracking Error    : {avg_mean_err:.2f} px (Threshold: <= 10.0 px)")
    print(f"Mean Tracking RMSE     : {avg_rmse:.2f} px (Threshold: <= 10.0 px)")
    print(f"Mean Acquisition Time  : {avg_acq:.3f} s (Threshold: <= 2.0 s)")
    print("=" * 80)


if __name__ == "__main__":
    main()
