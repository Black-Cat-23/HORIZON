"""
HORIZON Perception & Tracking Profile Benchmarking (B0 vs B1 vs B2 vs OURS)
===================================================================================
Executes side-by-side evaluation of perception profiles on identical seeds:

Profiles:
  - B0: Baseline (No tracking control / raw centroid)
  - B1: Classical Optical Detector + Estimator + PAT Controller
  - B2: Neural YOLOv8n ONNX Detector + Estimator + PAT Controller
  - OURS: Phase 8 Hybrid Perception + Optical Refinement + Estimator + PAT Controller

Evaluates across:
  - Disturbance Presets: NOMINAL, GAUSSIAN, SALT_PEPPER, FOG, RAIN, LOW_LIGHT, SEVERE
  - Target Sizes: 5×5, 10×10, 15×15, 20×20 px
  - Target Trajectories: Straight, Circular, Figure-8, Random

Strict Invariant: Zero ground-truth leakage into detector execution.
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
from simulator.perception.hybrid_detector import HybridBeaconDetector

logger = logging.getLogger(__name__)


def run_hybrid_profile_benchmark(
    num_frames_per_condition: int = 40, seed: int = 42
) -> Dict[str, Any]:
    """Execute side-by-side benchmark comparing B1 (CLASSICAL), B2 (NEURAL), and OURS (HYBRID)."""
    detector_b1 = HybridBeaconDetector(DetectorConfig(perception_mode="CLASSICAL"))
    detector_b2 = HybridBeaconDetector(DetectorConfig(perception_mode="NEURAL"))
    detector_ours = HybridBeaconDetector(DetectorConfig(perception_mode="HYBRID"))

    presets = ["NOMINAL", "GAUSSIAN", "SALT_PEPPER", "FOG", "RAIN", "LOW_LIGHT", "SEVERE"]
    target_sizes = [5.0, 10.0, 15.0, 20.0]
    rng = np.random.RandomState(seed)

    benchmark_results: Dict[str, Any] = {}

    for preset in presets:
        results = {
            "b1_classical": {"hits": 0, "errors": [], "times": []},
            "b2_neural": {"hits": 0, "errors": [], "times": []},
            "ours_hybrid": {"hits": 0, "errors": [], "times": []},
        }

        for i in range(num_frames_per_condition):
            u_gt = rng.uniform(60.0, 580.0)
            v_gt = rng.uniform(60.0, 420.0)
            size = float(rng.choice(target_sizes))

            frame, bbox_gt = render_synthetic_sample(
                u_center=u_gt,
                v_center=v_gt,
                size_px=size,
                disturbance_preset=preset,
                seed=seed + i,
            )

            # 1. B1 Classical
            res_b1 = detector_b1.detect(frame, timestamp=float(i))
            results["b1_classical"]["times"].append(res_b1.processing_time_ms)
            if res_b1.detected and res_b1.centroid is not None:
                results["b1_classical"]["hits"] += 1
                results["b1_classical"]["errors"].append(
                    math.hypot(res_b1.centroid[0] - u_gt, res_b1.centroid[1] - v_gt)
                )

            # 2. B2 Neural
            res_b2 = detector_b2.detect(frame, timestamp=float(i))
            results["b2_neural"]["times"].append(res_b2.processing_time_ms)
            if res_b2.detected and res_b2.centroid is not None:
                results["b2_neural"]["hits"] += 1
                results["b2_neural"]["errors"].append(
                    math.hypot(res_b2.centroid[0] - u_gt, res_b2.centroid[1] - v_gt)
                )

            # 3. OURS Hybrid
            res_ours = detector_ours.detect(frame, timestamp=float(i))
            results["ours_hybrid"]["times"].append(res_ours.processing_time_ms)
            if res_ours.detected and res_ours.centroid is not None:
                results["ours_hybrid"]["hits"] += 1
                results["ours_hybrid"]["errors"].append(
                    math.hypot(res_ours.centroid[0] - u_gt, res_ours.centroid[1] - v_gt)
                )

        preset_summary = {}
        for prof_key, data in results.items():
            errs = data["errors"]
            tms = data["times"]
            preset_summary[prof_key] = {
                "detection_rate_pct": (data["hits"] / num_frames_per_condition) * 100.0,
                "mean_error_px": float(np.mean(errs)) if errs else float("nan"),
                "p95_error_px": float(np.percentile(errs, 95)) if errs else float("nan"),
                "mean_latency_ms": float(np.mean(tms)),
                "fps": 1000.0 / max(float(np.mean(tms)), 0.01),
            }

        benchmark_results[preset] = preset_summary

    report_path = Path("benchmarks/hybrid_profile_benchmark_report.json")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(benchmark_results, f, indent=2)

    logger.info("Hybrid profile benchmark complete. Saved to %s", report_path)
    return benchmark_results


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    res = run_hybrid_profile_benchmark(num_frames_per_condition=25, seed=42)
    print(json.dumps(res, indent=2))
