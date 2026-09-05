"""
HORIZON Phase 4 Perception Profiling Benchmark
=====================================================
Empirical latency profiling for:
  - Preprocessing (adaptive median filter)
  - Candidate extraction & thresholding
  - Candidate filtering & scoring
  - Weighted CoG centroiding
  - 2D Gaussian surface fitting
  - Complete ClassicalBeaconDetector pipeline
"""

from pathlib import Path
import sys
import time
import numpy as np

# Ensure repository root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from simulator.perception.candidate import extract_candidates
from simulator.perception.centroid import compute_gaussian_fit, compute_weighted_cog
from simulator.perception.config import CentroidConfig, DetectorConfig
from simulator.perception.detector import ClassicalBeaconDetector
from simulator.perception.preprocessing import (
    apply_adaptive_median_filter,
    estimate_background_statistics,
    validate_input_frame,
)
from simulator.world.beacon import Beacon


def profile_stage(name: str, fn, n_runs: int = 200):
    # Warmup
    for _ in range(10):
        fn()

    durations = []
    for _ in range(n_runs):
        t0 = time.perf_counter()
        fn()
        t1 = time.perf_counter()
        durations.append((t1 - t0) * 1000.0)  # ms

    durations = np.array(durations)
    mean_val = np.mean(durations)
    med_val = np.median(durations)
    p95_val = np.percentile(durations, 95)
    p99_val = np.percentile(durations, 99)
    max_val = np.max(durations)

    print(
        f"| {name:<32} | {mean_val:8.3f} ms | {med_val:8.3f} ms | {p95_val:8.3f} ms | {p99_val:8.3f} ms | {max_val:8.3f} ms |",
        flush=True,
    )
    return {
        "name": name,
        "mean_ms": mean_val,
        "median_ms": med_val,
        "p95_ms": p95_val,
        "p99_ms": p99_val,
        "max_ms": max_val,
    }


def main():
    # Setup 640x480 frame with beacon
    frame = np.full((480, 640), 10, dtype=np.uint8)
    b = Beacon(size_px=10.0, intensity=255, shape="square")
    b.render_into(frame, x=320.5, y=240.5, background_level=10)

    cfg = DetectorConfig()
    detector = ClassicalBeaconDetector(cfg)

    # Preprocessed frame
    preprocessed = apply_adaptive_median_filter(frame, cfg.preprocessing)
    bg_level, noise_std = estimate_background_statistics(preprocessed)
    candidates, thresh_mask = extract_candidates(frame, preprocessed, bg_level, noise_std, cfg.scoring)

    cand = candidates[0]
    x, y, w, h = cand.bbox
    pad = 4
    x1, y1 = max(0, x - pad), max(0, y - pad)
    x2, y2 = min(640, x + w + pad), min(480, y + h + pad)
    roi_orig = frame[y1:y2, x1:x2]
    roi_mask = thresh_mask[y1:y2, x1:x2]

    print("\n======================================================================================================")
    print("HORIZON Phase 4 Perception Engine — Latency Profile (640×480 frame, 200 iterations)")
    print("======================================================================================================")
    print(f"| {'Component Stage':<32} | {'Mean':<11} | {'Median':<11} | {'P95':<11} | {'P99':<11} | {'Max':<11} |")
    print("|" + "-" * 34 + "|" + "-" * 13 + "|" + "-" * 13 + "|" + "-" * 13 + "|" + "-" * 13 + "|" + "-" * 13 + "|")

    profile_stage("Input Validation", lambda: validate_input_frame(frame))
    profile_stage("Adaptive Median Denoising", lambda: apply_adaptive_median_filter(frame, cfg.preprocessing))
    profile_stage("Background & Noise Estimation", lambda: estimate_background_statistics(preprocessed))
    profile_stage(
        "Candidate Extraction & Masking",
        lambda: extract_candidates(frame, preprocessed, bg_level, noise_std, cfg.scoring),
    )
    profile_stage(
        "Weighted CoG Centroid",
        lambda: compute_weighted_cog(roi_orig, roi_mask, bg_level, x1, y1),
    )
    profile_stage(
        "2D Gaussian Fit Centroid",
        lambda: compute_gaussian_fit(roi_orig, roi_mask, bg_level, x1, y1, cfg.centroid),
    )
    profile_stage("COMPLETE DETECTOR (Weighted CoG)", lambda: detector.detect(frame))

    det_gauss = ClassicalBeaconDetector(DetectorConfig(centroid=CentroidConfig(method="gaussian_fit")))
    profile_stage("COMPLETE DETECTOR (Gaussian Fit)", lambda: det_gauss.detect(frame))

    print("======================================================================================================\n")


if __name__ == "__main__":
    main()
