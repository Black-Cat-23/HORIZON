"""
HORIZON Perception Benchmark (CLASSICAL vs NEURAL)
==========================================================
Evaluates and compares ClassicalBeaconDetector vs NeuralBeaconDetector
on identical synthetic test frames under clean, Gaussian noise, Salt & Pepper noise,
fog, rain, low light, and target sizes (5×5, 10×10, 15×15, 20×20).

Reports:
  - Detection Rate [%]
  - Subpixel Error vs GT [px]
  - Mean Processing Latency [ms]
  - Frame Throughput [FPS]

Strict Invariant: Zero ground-truth leakage into detector execution.
Ground-truth target positions are used ONLY for accuracy evaluation.
"""

from __future__ import annotations

import json
import logging
import math
from pathlib import Path
import sys
from typing import Dict, Any, List
import numpy as np

project_root = Path(__file__).resolve().parents[1]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from research.data.generate_synthetic_dataset import render_synthetic_sample
from simulator.perception.config import DetectorConfig
from simulator.perception.detector import ClassicalBeaconDetector
from simulator.perception.neural_detector import NeuralBeaconDetector

logger = logging.getLogger(__name__)


def run_perception_benchmark(num_frames_per_condition: int = 50, seed: int = 42) -> Dict[str, Any]:
    """Execute side-by-side perception benchmark comparing CLASSICAL vs NEURAL."""
    classical_detector = ClassicalBeaconDetector(DetectorConfig(perception_mode="CLASSICAL"))
    neural_detector = NeuralBeaconDetector(DetectorConfig(perception_mode="NEURAL"))

    presets = ["NOMINAL", "GAUSSIAN", "SALT_PEPPER", "FOG", "RAIN", "LOW_LIGHT", "SEVERE"]
    target_sizes = [5.0, 10.0, 15.0, 20.0]

    rng = np.random.RandomState(seed)

    benchmark_results: Dict[str, Any] = {}

    for preset in presets:
        c_hits = 0
        n_hits = 0
        c_errors: List[float] = []
        n_errors: List[float] = []
        c_times: List[float] = []
        n_times: List[float] = []

        for i in range(num_frames_per_condition):
            u_gt = rng.uniform(50.0, 590.0)
            v_gt = rng.uniform(50.0, 430.0)
            size = float(rng.choice(target_sizes))

            frame, bbox_gt = render_synthetic_sample(
                u_center=u_gt,
                v_center=v_gt,
                size_px=size,
                disturbance_preset=preset,
                seed=seed + i,
            )

            # 1. Classical Detector Execution
            res_c = classical_detector.detect(frame, timestamp=float(i))
            c_times.append(res_c.processing_time_ms)
            if res_c.detected and res_c.centroid is not None:
                c_hits += 1
                c_errors.append(math.hypot(res_c.centroid[0] - u_gt, res_c.centroid[1] - v_gt))

            # 2. Neural Detector Execution
            res_n = neural_detector.detect(frame, timestamp=float(i))
            n_times.append(res_n.processing_time_ms)
            if res_n.detected and res_n.centroid is not None:
                n_hits += 1
                n_errors.append(math.hypot(res_n.centroid[0] - u_gt, res_n.centroid[1] - v_gt))

        benchmark_results[preset] = {
            "classical": {
                "detection_rate_pct": (c_hits / num_frames_per_condition) * 100.0,
                "mean_error_px": float(np.mean(c_errors)) if c_errors else float("nan"),
                "mean_latency_ms": float(np.mean(c_times)),
                "fps": 1000.0 / max(float(np.mean(c_times)), 0.01),
            },
            "neural": {
                "detection_rate_pct": (n_hits / num_frames_per_condition) * 100.0,
                "mean_error_px": float(np.mean(n_errors)) if n_errors else float("nan"),
                "mean_latency_ms": float(np.mean(n_times)),
                "fps": 1000.0 / max(float(np.mean(n_times)), 0.01),
                "is_model_loaded": neural_detector.is_model_loaded,
            },
        }

    report_path = Path("benchmarks/perception_benchmark_report.json")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(benchmark_results, f, indent=2)

    logger.info("Perception benchmark complete. Report saved to %s", report_path)
    return benchmark_results


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    res = run_perception_benchmark(num_frames_per_condition=30, seed=42)
    print(json.dumps(res, indent=2))
