"""
Compute empirical detection and error metrics under Gaussian noise and combined disturbances.
"""

from pathlib import Path
import sys
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from simulator.core.seed_manager import SeedManager
from simulator.disturbances.noise import apply_gaussian_noise
from simulator.disturbances.pipeline import DisturbancePipeline
from simulator.disturbances.presets import get_preset_config
from simulator.perception.detector import ClassicalBeaconDetector
from simulator.world.beacon import Beacon

det = ClassicalBeaconDetector()

# 1. Gaussian Noise (sigma = 5, 10, 15, 20)
print("\n=== Section 6: Gaussian Noise Verification ===")
for sigma in [5.0, 10.0, 15.0, 20.0]:
    detected_count = 0
    errors = []
    for seed in range(50):
        tx = 300.0 + seed * 0.2
        ty = 200.0 + seed * 0.15
        frame = np.full((480, 640), 10, dtype=np.uint8)
        b = Beacon(size_px=10.0, intensity=255, shape="square")
        b.render_into(frame, x=tx, y=ty, background_level=10)

        rng = SeedManager(seed=seed).get_rng("gaussian")
        noisy = apply_gaussian_noise(frame, sigma=sigma, rng=rng)

        res = det.detect(noisy)
        if res.detected:
            detected_count += 1
            err = np.hypot(res.centroid[0] - tx, res.centroid[1] - ty)
            errors.append(err)

    det_rate = (detected_count / 50.0) * 100.0
    err_arr = np.array(errors)
    rmse = np.sqrt(np.mean(err_arr ** 2))
    p95 = np.percentile(err_arr, 95)
    p99 = np.percentile(err_arr, 99)
    print(f"| sigma={sigma:4.1f} | Detection Rate: {det_rate:5.1f}% | RMSE: {rmse:.4f} px | P95: {p95:.4f} px | P99: {p99:.4f} px |")

# 2. Combined Disturbances
print("\n=== Section 9: Combined Disturbance Verification ===")
combos = [
    ("Gaussian + Fog", "SEVERE"),
    ("S&P + Fog", "SEVERE"),
    ("Gaussian + Jitter", "DIFFICULT"),
    ("S&P + Gaussian + Fog", "SEVERE"),
    ("S&P + Gauss + Fog + Jitter", "ADVERSARIAL"),
]

for name, preset in combos:
    detected_count = 0
    errors = []
    cfg = get_preset_config(preset)
    for seed in range(50):
        tx = 320.0 + (seed % 10) * 1.5
        ty = 240.0 + (seed % 10) * 1.2
        frame = np.full((480, 640), 10, dtype=np.uint8)
        b = Beacon(size_px=10.0, intensity=255, shape="square")
        b.render_into(frame, x=tx, y=ty, background_level=10)

        pipeline = DisturbancePipeline(cfg, SeedManager(seed=seed))
        disturbed, telem = pipeline.apply(frame, sim_time=0.1 * seed, sim_dt=1/60.0)

        # Apply platform and jitter true translation to ground truth position for error calculation
        effective_tx = tx + telem.platform_offset_x + telem.camera_jitter_x
        effective_ty = ty + telem.platform_offset_y + telem.camera_jitter_y

        res = det.detect(disturbed)
        if res.detected:
            detected_count += 1
            err = np.hypot(res.centroid[0] - effective_tx, res.centroid[1] - effective_ty)
            errors.append(err)

    det_rate = (detected_count / 50.0) * 100.0
    err_arr = np.array(errors)
    rmse = np.sqrt(np.mean(err_arr ** 2)) if len(errors) > 0 else 0.0
    p95 = np.percentile(err_arr, 95) if len(errors) > 0 else 0.0
    p99 = np.percentile(err_arr, 99) if len(errors) > 0 else 0.0
    max_e = np.max(err_arr) if len(errors) > 0 else 0.0
    print(f"| {name:<26} | Det Rate: {det_rate:5.1f}% | RMSE: {rmse:.4f} px | P95: {p95:.4f} px | P99: {p99:.4f} px | Max: {max_e:.4f} px |")
