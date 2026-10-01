"""
Cross-combination validation: all trajectories x disturbance presets.

Uses the CORRECT SimulationEngine API:
  - engine.step()          → world frame (numpy array, disturbance already applied)
  - engine.get_current_state()  → TargetState with .x, .y ground truth
  - engine.get_disturbed_frame() → 480x640 camera frame (disturbed)
  - engine.current_target_state → property alias

Validates 6 trajectories x 11 disturbance presets = 66 combos.
Each combo runs 3 s @ 60 Hz (180 frames) with an IMM filter tracking the
simulated ground truth + Gaussian noise measurement.
"""

import sys, os, itertools, traceback
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import numpy as np

from simulator.core.config import AppConfig, SimulationConfig, TrajectoryConfig, TargetConfig
from simulator.core.simulation import SimulationEngine
from simulator.disturbances.presets import get_preset_config
from tracking.estimation.imm_kalman import InteractingMultipleModelFilter

TRAJECTORIES = ["circular", "figure8", "random", "sinusoidal", "spiral", "straight"]
DISTURBANCE_PRESETS = [
    "NOMINAL", "DIFFICULT", "SEVERE", "RECOVERY", "ADVERSARIAL",
    "DISTRACTOR_BURST", "OCCLUSION_EVENT", "BRIGHTNESS_FADE",
    "JITTER_BURST", "PLATFORM_SWING", "COMBINED_TURBULENCE",
]

SEED = 42
DURATION_S = 3.0
FREQ_HZ = 60.0

results = []
failures = []

total = len(TRAJECTORIES) * len(DISTURBANCE_PRESETS)
done = 0

rng_meas = np.random.default_rng(seed=SEED)

for traj, preset_name in itertools.product(TRAJECTORIES, DISTURBANCE_PRESETS):
    combo_id = f"{traj}+{preset_name}"
    try:
        disturbance_cfg = get_preset_config(preset_name)

        cfg = AppConfig(
            simulation=SimulationConfig(
                frequency_hz=FREQ_HZ,
                seed=SEED,
                duration_seconds=DURATION_S,
            ),
            trajectory=TrajectoryConfig(type=traj),
            target=TargetConfig(size_px=8, intensity=220),
            disturbance=disturbance_cfg,
        )

        engine = SimulationEngine(cfg, experiment_id=f"VAL_{combo_id}")
        engine.initialize()

        imm = InteractingMultipleModelFilter()
        rmse_sum = 0.0
        n_meas = 0
        total_frames = cfg.simulation.total_frames

        for _ in range(total_frames):
            # Advance simulation (disturbance pipeline runs internally)
            _world_frame = engine.step()

            # Get ground-truth state and disturbed camera frame
            gt = engine.get_current_state()     # TargetState with .x, .y
            dist_frame = engine.get_disturbed_frame()  # 480x640 uint8

            # Validate disturbed frame invariants
            assert dist_frame.dtype == np.uint8, f"dtype={dist_frame.dtype}"
            assert dist_frame.ndim == 2, f"ndim={dist_frame.ndim}"
            assert dist_frame.shape == (480, 640), f"shape={dist_frame.shape}"
            assert np.all(np.isfinite(dist_frame.astype(np.float32))), "non-finite pixels"

            # Feed synthetic noisy measurement to IMM tracker
            meas_x = gt.x + rng_meas.normal(0.0, 1.5)
            meas_y = gt.y + rng_meas.normal(0.0, 1.5)
            ts = engine.clock.current_time

            if not imm.is_initialized:
                imm.initialize((meas_x, meas_y), timestamp=ts)
            else:
                est = imm.step((meas_x, meas_y), confidence=0.9, timestamp=ts)
                assert np.isfinite(est.estimated_x), "non-finite estimated_x"
                assert np.isfinite(est.estimated_y), "non-finite estimated_y"
                dx = est.estimated_x - gt.x
                dy = est.estimated_y - gt.y
                rmse_sum += dx*dx + dy*dy
                n_meas += 1

        rmse = float(np.sqrt(rmse_sum / max(1, n_meas)))
        results.append({
            "combo": combo_id, "rmse_px": round(rmse, 3),
            "frames": total_frames, "ok": True,
        })

    except Exception as exc:
        failures.append({"combo": combo_id, "error": str(exc),
                         "traceback": traceback.format_exc()})
        results.append({"combo": combo_id, "ok": False, "error": str(exc)})

    done += 1
    if done % 10 == 0 or done == total:
        print(f"  [{done}/{total}] completed", flush=True)


# Summary
passed = sum(1 for r in results if r["ok"])
failed = len(failures)
print(f"\n{'='*60}")
print(f"CROSS-COMBINATION VALIDATION SUMMARY")
print(f"{'='*60}")
print(f"  Total combinations : {total}")
print(f"  Passed             : {passed}")
print(f"  Failed             : {failed}")

if failures:
    print("\nFAILURES:")
    for f in failures:
        print(f"  COMBO : {f['combo']}")
        print(f"  ERROR : {f['error']}")
        print()
else:
    passing = [r for r in results if r["ok"]]
    rmse_vals = [r["rmse_px"] for r in passing]
    print(f"\n  RMSE range: {min(rmse_vals):.2f} - {max(rmse_vals):.2f} px")
    print(f"  All {total} trajectory x disturbance combinations PASSED.")

sys.exit(0 if failed == 0 else 1)
