"""
Compute exact centroid method comparison statistics on 200 identical frames.
"""

from pathlib import Path
import sys
import time
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from simulator.perception.config import CentroidConfig, DetectorConfig
from simulator.perception.detector import ClassicalBeaconDetector
from simulator.world.beacon import Beacon

rng = np.random.default_rng(42)
true_positions = []
for _ in range(200):
    tx = rng.uniform(50.0, 590.0)
    ty = rng.uniform(50.0, 430.0)
    true_positions.append((tx, ty))

methods = ["geometric", "weighted_cog", "gaussian_fit"]
results = {}

for m in methods:
    det = ClassicalBeaconDetector(DetectorConfig(centroid=CentroidConfig(method=m)))
    errors = []
    times = []
    for tx, ty in true_positions:
        frame = np.full((480, 640), 10, dtype=np.uint8)
        b = Beacon(size_px=10.0, intensity=255, shape="square")
        b.render_into(frame, x=tx, y=ty, background_level=10)

        t0 = time.perf_counter()
        res = det.detect(frame)
        t1 = time.perf_counter()

        times.append((t1 - t0) * 1000.0)
        err = np.hypot(res.centroid[0] - tx, res.centroid[1] - ty)
        errors.append(err)

    err_arr = np.array(errors)
    time_arr = np.array(times)
    results[m] = {
        "mean": np.mean(err_arr),
        "rmse": np.sqrt(np.mean(err_arr ** 2)),
        "p95": np.percentile(err_arr, 95),
        "p99": np.percentile(err_arr, 99),
        "max": np.max(err_arr),
        "time": np.mean(time_arr),
    }

print("\n| Method | Mean Error (px) | RMSE (px) | P95 (px) | P99 (px) | Max Error (px) | Mean Time (ms) |")
print("|---|---|---|---|---|---|---|")
for m in methods:
    r = results[m]
    print(f"| **{m}** | {r['mean']:.4f} px | {r['rmse']:.4f} px | {r['p95']:.4f} px | {r['p99']:.4f} px | {r['max']:.4f} px | {r['time']:.3f} ms |")
