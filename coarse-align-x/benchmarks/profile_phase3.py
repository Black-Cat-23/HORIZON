"""
HORIZON Phase 3 Performance Profiling Script
===================================================
Benchmarks exact execution time per 640×480 frame for:
  - Salt & Pepper noise
  - Additive Gaussian noise
  - Poisson photon shot noise
  - Atmospheric degradation (Fog/Haze)
  - Camera jitter
  - Continuous platform motion
  - Complete DisturbancePipeline (ADVERSARIAL worst-case preset)

Computes:
  - Mean execution time (ms)
  - Median execution time (ms)
  - P95 execution time (ms)
  - Maximum execution time (ms)
"""

from pathlib import Path
import sys
import time
import numpy as np

# Ensure repository root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from simulator.core.seed_manager import SeedManager
from simulator.disturbances.atmosphere import apply_atmospheric_degradation
from simulator.disturbances.config import AtmosphereConfig, CameraJitterConfig, PlatformMotionConfig
from simulator.disturbances.jitter import CameraJitterEngine
from simulator.disturbances.noise import (
    apply_gaussian_noise,
    apply_poisson_noise,
    apply_salt_and_pepper_noise,
)
from simulator.disturbances.pipeline import DisturbancePipeline
from simulator.disturbances.platform import PlatformMotionEngine
from simulator.disturbances.presets import get_preset_config


def benchmark_function(name: str, fn, n_runs: int = 100):
    # Warmup
    for _ in range(5):
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
    max_val = np.max(durations)

    print(f"| {name:<32} | {mean_val:8.3f} ms | {med_val:8.3f} ms | {p95_val:8.3f} ms | {max_val:8.3f} ms |", flush=True)
    return {
        "name": name,
        "mean_ms": mean_val,
        "median_ms": med_val,
        "p95_ms": p95_val,
        "max_ms": max_val,
    }


def main():
    frame = np.full((480, 640), 128, dtype=np.uint8)
    seed_mgr = SeedManager(seed=42)

    rng_sp = seed_mgr.get_rng("salt_pepper")
    rng_gauss = seed_mgr.get_rng("gaussian")
    rng_poiss = seed_mgr.get_rng("poisson")
    rng_jit = seed_mgr.get_rng("jitter")
    rng_plat = seed_mgr.get_rng("platform")

    jitter_engine = CameraJitterEngine(
        CameraJitterConfig(enabled=True, max_x_px=15.0, max_y_px=15.0), rng_jit
    )
    platform_engine = PlatformMotionEngine(
        PlatformMotionConfig(enabled=True, model="linear", velocity_x=60.0, velocity_y=30.0),
        rng_plat,
    )
    atmos_cfg = AtmosphereConfig(enabled=True, condition="fog")

    pipeline_adversarial = DisturbancePipeline(
        get_preset_config("ADVERSARIAL"),
        SeedManager(seed=101),
    )

    print("\n==========================================================================================")
    print("HORIZON Phase 3 Disturbance Engine — Micro-Benchmark (640×480 frame, 500 iterations)")
    print("==========================================================================================")
    print(f"| {'Component Stage':<32} | {'Mean':<11} | {'Median':<11} | {'P95':<11} | {'Max':<11} |")
    print("|" + "-" * 34 + "|" + "-" * 13 + "|" + "-" * 13 + "|" + "-" * 13 + "|" + "-" * 13 + "|")

    benchmark_function(
        "Salt & Pepper (p=0.10)",
        lambda: apply_salt_and_pepper_noise(frame, 0.10, rng_sp),
    )
    benchmark_function(
        "Gaussian Noise (sigma=20.0)",
        lambda: apply_gaussian_noise(frame, 20.0, rng_gauss),
    )
    benchmark_function(
        "Poisson Shot Noise (peak=30)",
        lambda: apply_poisson_noise(frame, 30.0, rng_poiss),
    )
    benchmark_function(
        "Atmospheric Degradation (Fog)",
        lambda: apply_atmospheric_degradation(frame, atmos_cfg),
    )
    benchmark_function(
        "Camera Jitter (Affine ±15px)",
        lambda: jitter_engine.step(frame),
    )
    benchmark_function(
        "Platform Motion (Linear Step)",
        lambda: platform_engine.step(frame, dt=1/60.0, sim_time=1.0),
    )
    benchmark_function(
        "FULL PIPELINE (ADVERSARIAL)",
        lambda: pipeline_adversarial.apply(frame, sim_time=1.0, sim_dt=1/60.0),
    )
    print("==========================================================================================\n")


if __name__ == "__main__":
    main()
