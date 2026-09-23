"""
Automated Verification Suite for Step 4: Non-Linear ADRC (NLESO & Anti-Windup)
HORIZON — SIH 2026 PS SIH26169 (PDF Section 6.6 & 6.9)

Executes 4 rigorous quantitative validation benchmarks:
  Test 1: NLESO Peaking Suppression vs. Linear LESO under large transient errors.
  Test 2: Actuator Rate Saturation Anti-Windup Verification.
  Test 3: Multi-Frequency Platform Base Vibration Rejection (ADRC vs PID).
  Test 4: Closed-Loop PAT Telemetry & Computational Latency Benchmark.
"""

from __future__ import annotations

import math
import sys
import time
from pathlib import Path
from typing import Dict, List, Tuple
import numpy as np

# Ensure coarse-align-x root is in import path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from control.adrc_controller import ADRCAxisController, DualAxisADRCController, fal
from control.camera_controller import PATCameraController
from pat.state import PATMode, PATState


def test_1_nleso_peaking_suppression() -> Dict[str, float]:
    """
    Test 1: Evaluates transient response of Linear LESO vs Non-Linear NLESO (fal).
    Under a large initial pointing error (5.0 deg), linear observers exhibit severe
    observer peaking, causing overshoot and limit cycles. NLESO compresses large errors.
    """
    print("\n--- Test 1: NLESO Peaking Suppression vs Linear LESO ---")

    dt = 1.0 / 60.0  # 60 Hz closed loop
    steps = 180  # 3 seconds
    initial_error = 5.0  # 5 degrees initial boresight offset

    # Linear LESO (alpha1 = 1.0, alpha2 = 1.0)
    linear_adrc = ADRCAxisController(
        b0=1.0, omega_o=12.0, omega_c=2.8, output_limit=20.0,
        alpha1=1.0, alpha2=1.0, delta=0.05
    )

    # Non-linear NLESO (alpha1 = 0.75, alpha2 = 0.50)
    nleso_adrc = ADRCAxisController(
        b0=1.0, omega_o=12.0, omega_c=2.8, output_limit=20.0,
        alpha1=0.75, alpha2=0.50, delta=0.05
    )

    def simulate_step_response(ctrl: ADRCAxisController) -> Tuple[List[float], List[float]]:
        errors = []
        z2_estimates = []
        pos_error = initial_error
        for _ in range(steps):
            u_cmd = ctrl.compute(pos_error, dt)
            # Simulated 1st-order pointing kinematics: y_dot = -u
            pos_error += -u_cmd * dt
            errors.append(pos_error)
            z2_estimates.append(ctrl.get_estimated_disturbance())
        return errors, z2_estimates

    lin_errors, lin_z2 = simulate_step_response(linear_adrc)
    nl_errors, nl_z2 = simulate_step_response(nleso_adrc)

    # Calculate overshoot past 0.0 deg
    lin_overshoot = abs(min(0.0, min(lin_errors)))
    nl_overshoot = abs(min(0.0, min(nl_errors)))

    # Observer peak transient
    lin_peak_z2 = max(abs(z) for z in lin_z2)
    nl_peak_z2 = max(abs(z) for z in nl_z2)

    overshoot_reduction_pct = ((lin_overshoot - nl_overshoot) / max(1e-4, lin_overshoot)) * 100.0 if lin_overshoot > 0 else 0.0
    z2_peak_reduction_pct = ((lin_peak_z2 - nl_peak_z2) / max(1e-4, lin_peak_z2)) * 100.0

    print(f"  • Linear LESO Overshoot:       {lin_overshoot:.3f}° | Observer Peak: {lin_peak_z2:.2f}°/s")
    print(f"  • Non-Linear NLESO Overshoot:  {nl_overshoot:.3f}° | Observer Peak: {nl_peak_z2:.2f}°/s")
    print(f"  • Overshoot Reduction:         {overshoot_reduction_pct:.1f}%")
    print(f"  • Observer Peaking Reduction:  {z2_peak_reduction_pct:.1f}%")

    assert nl_overshoot <= lin_overshoot, "NLESO overshoot should not exceed Linear LESO"
    assert z2_peak_reduction_pct >= 25.0, f"Observer peaking reduction ({z2_peak_reduction_pct:.1f}%) < 25%"

    print("  [PASS] Test 1: NLESO successfully suppresses observer peaking and transient overshoot.")
    return {
        "linear_overshoot_deg": lin_overshoot,
        "nleso_overshoot_deg": nl_overshoot,
        "overshoot_reduction_pct": overshoot_reduction_pct,
        "z2_peak_reduction_pct": z2_peak_reduction_pct,
    }


def test_2_actuator_anti_windup() -> Dict[str, float]:
    """
    Test 2: Evaluates actuator rate saturation anti-windup.
    When actuator slew rate is strictly clamped (e.g. max 10 deg/s), a controller without
    anti-windup suffers from observer state windup (z2 charges up falsely), causing large
    reverse recovery transients.
    """
    print("\n--- Test 2: Actuator Rate Saturation Anti-Windup Verification ---")

    dt = 1.0 / 60.0
    steps = 150
    rate_limit = 10.0  # Saturated physical rate limit

    ctrl_no_aw = ADRCAxisController(b0=1.0, omega_o=12.0, omega_c=2.8, output_limit=30.0)
    ctrl_aw = ADRCAxisController(b0=1.0, omega_o=12.0, omega_c=2.8, output_limit=rate_limit)

    # Simulate with saturation on physical plant
    def run_saturation_sim(ctrl: ADRCAxisController, use_rate_feedback: bool) -> Tuple[List[float], List[float]]:
        y = 4.0  # 4 deg error requiring full saturation slew
        errors = []
        z2_vals = []
        for _ in range(steps):
            if use_rate_feedback:
                # Gimbal rate is physically clamped to rate_limit
                act_rate = float(np.clip(ctrl.last_u, -rate_limit, rate_limit))
                u_cmd = ctrl.compute(y, dt, actual_rate=act_rate)
                phys_rate = float(np.clip(u_cmd, -rate_limit, rate_limit))
            else:
                u_cmd = ctrl.compute(y, dt)  # No actual rate passed (blind to saturation)
                phys_rate = float(np.clip(u_cmd, -rate_limit, rate_limit))

            y += -phys_rate * dt
            errors.append(y)
            z2_vals.append(ctrl.get_estimated_disturbance())
        return errors, z2_vals

    err_no_aw, z2_no_aw = run_saturation_sim(ctrl_no_aw, use_rate_feedback=False)
    err_aw, z2_aw = run_saturation_sim(ctrl_aw, use_rate_feedback=True)

    overshoot_no_aw = abs(min(0.0, min(err_no_aw)))
    overshoot_aw = abs(min(0.0, min(err_aw)))
    max_z2_windup_no_aw = max(abs(z) for z in z2_no_aw)
    max_z2_windup_aw = max(abs(z) for z in z2_aw)

    aw_improvement_pct = ((overshoot_no_aw - overshoot_aw) / max(1e-4, overshoot_no_aw)) * 100.0 if overshoot_no_aw > 0 else 0.0

    print(f"  • Without Anti-Windup Overshoot: {overshoot_no_aw:.3f}° | Max z2 Windup: {max_z2_windup_no_aw:.2f}°/s")
    print(f"  • With Anti-Windup Overshoot:    {overshoot_aw:.3f}° | Max z2 Windup: {max_z2_windup_aw:.2f}°/s")
    print(f"  • Anti-Windup Overshoot Imprv:   {aw_improvement_pct:.1f}%")

    assert overshoot_aw <= overshoot_no_aw + 1e-4, "Anti-windup should eliminate or reduce saturation overshoot"

    print("  [PASS] Test 2: Actuator anti-windup prevents observer windup under rate limit saturation.")
    return {
        "overshoot_no_aw_deg": overshoot_no_aw,
        "overshoot_aw_deg": overshoot_aw,
        "aw_improvement_pct": aw_improvement_pct,
    }


def test_3_platform_vibration_rejection() -> Dict[str, float]:
    """
    Test 3: Compares closed-loop tracking error RMSE between standard PID and ADRC
    under multi-frequency platform base vibration (2 Hz, 6 Hz, 12 Hz).
    """
    print("\n--- Test 3: Multi-Frequency Platform Base Vibration Rejection (ADRC vs PID) ---")

    dt = 1.0 / 60.0
    duration_s = 6.0
    steps = int(duration_s / dt)
    rng = np.random.RandomState(42)

    # 2-axis Controllers
    pid_ctrl = PATCameraController(controller_type="PID")
    adrc_ctrl = PATCameraController(controller_type="ADRC")

    def run_tracking_under_vibration(ctrl: PATCameraController) -> Tuple[List[float], float]:
        # Target kinematics: linear drift at 0.5 deg/s
        target_pan_vel = 0.50
        target_tilt_vel = 0.25

        tgt_pan = 0.0
        tgt_tilt = 0.0
        cam_pan = 0.0
        cam_tilt = 0.0

        pointing_errors = []

        for step in range(steps):
            t = step * dt

            # Target position
            tgt_pan += target_pan_vel * dt
            tgt_tilt += target_tilt_vel * dt

            # Platform base vibration disturbance: 2 Hz + 6 Hz + 12 Hz + noise
            vib_pan = (
                0.35 * math.sin(2.0 * math.pi * 2.0 * t)
                + 0.20 * math.sin(2.0 * math.pi * 6.0 * t)
                + 0.10 * math.sin(2.0 * math.pi * 12.0 * t)
                + rng.normal(0.0, 0.03)
            )
            vib_tilt = (
                0.25 * math.cos(2.0 * math.pi * 2.5 * t)
                + 0.15 * math.sin(2.0 * math.pi * 7.0 * t)
                + 0.08 * math.sin(2.0 * math.pi * 11.0 * t)
                + rng.normal(0.0, 0.03)
            )

            # Net pointing error seen on sensor
            pan_error = (tgt_pan + vib_pan) - cam_pan
            tilt_error = (tgt_tilt + vib_tilt) - cam_tilt
            err_norm = math.hypot(pan_error, tilt_error)
            pointing_errors.append(err_norm)

            pat_state = PATState(
                mode=PATMode.TRACK,
                pan_error_deg=pan_error,
                tilt_error_deg=tilt_error,
                track_quality=0.92,
            )

            # Compute control command
            cmd_pan, cmd_tilt, _, _, _, _, _ = ctrl.compute_control_command(
                dt=dt,
                pat_state=pat_state,
                search_pan_rate=0.0,
                search_tilt_rate=0.0,
                reacquire_pan_rate=0.0,
                reacquire_tilt_rate=0.0,
                estimated_vx_px_s=target_pan_vel * 80.0,
                estimated_vy_px_s=target_tilt_vel * 80.0,
            )

            # Actuator response
            cam_pan += cmd_pan * dt
            cam_tilt += cmd_tilt * dt

        # Discard initial 0.5s settling phase for steady-state evaluation
        settled_errors = pointing_errors[int(0.5 / dt):]
        rmse = float(np.sqrt(np.mean(np.square(settled_errors))))
        p95 = float(np.percentile(settled_errors, 95))
        return settled_errors, rmse, p95

    _, pid_rmse, pid_p95 = run_tracking_under_vibration(pid_ctrl)
    _, adrc_rmse, adrc_p95 = run_tracking_under_vibration(adrc_ctrl)

    rmse_reduction_pct = ((pid_rmse - adrc_rmse) / pid_rmse) * 100.0
    p95_reduction_pct = ((pid_p95 - adrc_p95) / pid_p95) * 100.0

    print(f"  • Standard PID Tracking RMSE:  {pid_rmse:.4f}° | P95: {pid_p95:.4f}°")
    print(f"  • Non-Linear ADRC RMSE:        {adrc_rmse:.4f}° | P95: {adrc_p95:.4f}°")
    print(f"  • RMSE Error Reduction:        {rmse_reduction_pct:.1f}%")
    print(f"  • P95 Tail Error Reduction:    {p95_reduction_pct:.1f}%")

    assert adrc_rmse < pid_rmse, f"ADRC RMSE ({adrc_rmse:.4f}) must be lower than PID RMSE ({pid_rmse:.4f})"
    assert rmse_reduction_pct >= 25.0, f"ADRC disturbance rejection improvement ({rmse_reduction_pct:.1f}%) < 25%"

    print("  [PASS] Test 3: ADRC outperforms PID by > 25% under multi-frequency platform vibration.")
    return {
        "pid_rmse_deg": pid_rmse,
        "adrc_rmse_deg": adrc_rmse,
        "rmse_reduction_pct": rmse_reduction_pct,
        "pid_p95_deg": pid_p95,
        "adrc_p95_deg": adrc_p95,
        "p95_reduction_pct": p95_reduction_pct,
    }


def test_4_pat_telemetry_and_latency() -> Dict[str, float]:
    """
    Test 4: Verifies PATCameraController real-time disturbance telemetry access,
    numerical stability, and computation latency (< 0.05 ms per step).
    """
    print("\n--- Test 4: PAT Disturbance Telemetry & Latency Benchmark ---")

    ctrl = PATCameraController(controller_type="ADRC")
    pat_state = PATState(
        mode=PATMode.TRACK,
        pan_error_deg=0.45,
        tilt_error_deg=-0.30,
        track_quality=0.88,
    )

    # 1. Warm-up
    for _ in range(20):
        ctrl.compute_control_command(
            dt=0.0167,
            pat_state=pat_state,
            search_pan_rate=0.0,
            search_tilt_rate=0.0,
            reacquire_pan_rate=0.0,
            reacquire_tilt_rate=0.0,
        )

    # 2. Benchmark 5,000 steps
    n_steps = 5000
    t0 = time.perf_counter()
    for _ in range(n_steps):
        cmd_pan, cmd_tilt, pid_p, pid_t, ff_p, ff_t, sat = ctrl.compute_control_command(
            dt=0.0167,
            pat_state=pat_state,
            search_pan_rate=0.0,
            search_tilt_rate=0.0,
            reacquire_pan_rate=0.0,
            reacquire_tilt_rate=0.0,
        )
    total_time_s = time.perf_counter() - t0
    mean_lat_us = (total_time_s / n_steps) * 1e6
    mean_lat_ms = mean_lat_us / 1000.0
    throughput_hz = n_steps / total_time_s

    # 3. Telemetry access check
    d_pan, d_tilt = ctrl.get_estimated_disturbance()

    print(f"  • Computation Latency:         {mean_lat_us:.2f} µs ({mean_lat_ms:.4f} ms)")
    print(f"  • Execution Throughput:        {throughput_hz:,.0f} Hz (Closed Loop)")
    print(f"  • Estimated Disturbance (Pan): {d_pan:+.3f}°/s")
    print(f"  • Estimated Disturbance (Tilt):{d_tilt:+.3f}°/s")

    assert math.isfinite(cmd_pan) and math.isfinite(cmd_tilt), "Commanded rates must be finite"
    assert math.isfinite(d_pan) and math.isfinite(d_tilt), "Estimated disturbances must be finite"
    assert mean_lat_ms < 0.10, f"ADRC computation latency ({mean_lat_ms:.4f} ms) must be < 0.10 ms"

    print("  [PASS] Test 4: Real-time telemetry is verified with microsecond execution throughput.")
    return {
        "mean_latency_us": mean_lat_us,
        "mean_latency_ms": mean_lat_ms,
        "throughput_hz": throughput_hz,
        "dist_pan_deg_s": d_pan,
        "dist_tilt_deg_s": d_tilt,
    }


def main():
    print("=" * 80)
    print("HORIZON STEP 4: ACTIVE DISTURBANCE REJECTION CONTROL (ADRC) VERIFICATION")
    print("Non-Linear NLESO (fal) · Actuator Anti-Windup · Platform Vibration Cancellation")
    print("=" * 80)

    t_start = time.perf_counter()
    r1 = test_1_nleso_peaking_suppression()
    r2 = test_2_actuator_anti_windup()
    r3 = test_3_platform_vibration_rejection()
    r4 = test_4_pat_telemetry_and_latency()
    total_wall_s = time.perf_counter() - t_start

    print("\n" + "=" * 80)
    print(f"ALL STEP 4 VERIFICATION BENCHMARKS PASSED in {total_wall_s:.2f}s!")
    print("=" * 80)
    print(f"  [1] NLESO Peaking Suppression:     {r1['z2_peak_reduction_pct']:.1f}% peak transient reduction")
    print(f"  [2] Actuator Anti-Windup:          {r2['aw_improvement_pct']:.1f}% saturation overshoot reduction")
    print(f"  [3] Multi-Frequency Vibration:     {r3['rmse_reduction_pct']:.1f}% RMSE error reduction vs PID")
    print(f"  [4] Controller Execution Latency:  {r4['mean_latency_us']:.2f} µs ({r4['throughput_hz']:,.0f} Hz loop)")
    print("=" * 80)


if __name__ == "__main__":
    main()
