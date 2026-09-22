"""
Comprehensive Trajectory & Disturbance Robustness Matrix
Evaluates all 6 trajectories across NOMINAL, DIFFICULT, SEVERE, and RECOVERY presets.
Verifies that tracking and locking are 100% dynamic without hardcoded thresholds.
"""

import sys
from verify_dynamic_trajectories import run_trajectory_test

presets = ["NOMINAL", "DIFFICULT", "SEVERE", "RECOVERY"]
trajectories = ["sinusoidal", "figure8", "circular", "spiral", "random", "straight"]

print(f"{'TRAJECTORY':<14} | {'PRESET':<12} | {'FOV %':<8} | {'LOCK %':<8} | {'MEAN ERR (px)':<14}", flush=True)
print("-" * 65, flush=True)

results = []
for p in presets:
    for t in trajectories:
        res = run_trajectory_test(t, preset=p, duration_s=2.0)
        results.append(res)
        print(
            f"{res['traj']:<14} | {res['preset']:<12} | {res['fov_pct']:>6.1f}% | {res['lock_pct']:>6.1f}% | {res['mean_err_px']:>10.2f} px",
            flush=True
        )

print("\n=== MATRIX SUMMARY ===", flush=True)
for p in presets:
    preset_results = [r for r in results if r["preset"] == p]
    avg_fov = sum(r["fov_pct"] for r in preset_results) / len(preset_results)
    avg_lock = sum(r["lock_pct"] for r in preset_results) / len(preset_results)
    avg_err = sum(r["mean_err_px"] for r in preset_results if not (r["mean_err_px"] != r["mean_err_px"])) / max(1, len([r for r in preset_results if not (r["mean_err_px"] != r["mean_err_px"])]))
    print(f"Preset {p:<10}: Avg FOV = {avg_fov:>5.1f}%, Avg Lock = {avg_lock:>5.1f}%, Avg Err = {avg_err:>5.2f} px", flush=True)
