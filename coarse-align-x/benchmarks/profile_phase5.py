"""
HORIZON Phase 5 Performance Profiling & Micro-Benchmarks
===============================================================
Measures isolated latency and throughput of:
  - Kalman prediction step: F, Q, x_pred, P_pred
  - Kalman measurement update step (Joseph form): y, S, K, x, P
  - Mahalanobis gating test
  - Multi-candidate association
  - Full end-to-end estimation cycle
"""

from __future__ import annotations

from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).parent.parent))

import numpy as np

from tracking.association.association import MeasurementCandidate, TrackAssociator
from tracking.association.gate import MahalanobisGate
from tracking.association.track import Track
from tracking.estimation.kalman import KalmanFilterConfig, TargetKalmanFilter
from tracking.estimation.model import (
    build_measurement_matrix,
    build_measurement_noise_matrix,
)


def benchmark_phase5_operations(n_iterations: int = 5000):
    print(f"================================================================")
    print(f"HORIZON Phase 5 State Estimation Micro-Benchmarks")
    print(f"Iterations: {n_iterations:,}")
    print(f"================================================================")

    kf = TargetKalmanFilter(KalmanFilterConfig(use_joseph_form=True))
    kf.initialize((320.0, 240.0), timestamp=0.0)

    # 1. Benchmark Predict Step
    predict_times = []
    for _ in range(n_iterations):
        t0 = time.perf_counter_ns()
        kf.predict(0.01667)
        t1 = time.perf_counter_ns()
        predict_times.append((t1 - t0) / 1000.0)  # microseconds

    # 2. Benchmark Update Step (Joseph Form)
    update_times = []
    meas = (321.0, 240.5)
    for _ in range(n_iterations):
        t0 = time.perf_counter_ns()
        kf.update(meas, confidence=0.95)
        t1 = time.perf_counter_ns()
        update_times.append((t1 - t0) / 1000.0)  # microseconds

    # 3. Benchmark Mahalanobis Gate
    gate = MahalanobisGate(threshold=9.21)
    x_pred = np.array([[320.0], [240.0], [10.0], [-5.0]])
    P_pred = np.diag([2.0, 2.0, 20.0, 20.0])
    H = build_measurement_matrix()
    R = build_measurement_noise_matrix(confidence=0.9)
    z = np.array([[320.5], [239.8]])

    gate_times = []
    for _ in range(n_iterations):
        t0 = time.perf_counter_ns()
        gate.test(z, x_pred, P_pred, H, R)
        t1 = time.perf_counter_ns()
        gate_times.append((t1 - t0) / 1000.0)

    # 4. Benchmark Multi-Candidate Association (5 candidates)
    associator = TrackAssociator()
    candidates = [
        MeasurementCandidate(candidate_id=i, centroid_x=320.0 + i*5, centroid_y=240.0 + i*3, confidence=0.9 - i*0.1)
        for i in range(5)
    ]
    assoc_times = []
    for _ in range(n_iterations):
        t0 = time.perf_counter_ns()
        associator.associate(candidates, x_pred, P_pred)
        t1 = time.perf_counter_ns()
        assoc_times.append((t1 - t0) / 1000.0)

    # 5. Benchmark Full Track.step Cycle
    track = Track(track_id=1)
    track.step(measurement=(320.0, 240.0), timestamp=0.0)
    full_cycle_times = []
    for step in range(1, n_iterations + 1):
        t = step * 0.01667
        meas_step = (320.0 + (step % 50) * 0.2, 240.0 + (step % 30) * 0.1)
        t0 = time.perf_counter_ns()
        track.step(measurement=meas_step, confidence=0.92, timestamp=t)
        t1 = time.perf_counter_ns()
        full_cycle_times.append((t1 - t0) / 1000.0)

    def print_stats(name: str, times_us: list[float]):
        arr = np.array(times_us)
        mean_us = np.mean(arr)
        med_us = np.median(arr)
        p95_us = np.percentile(arr, 95)
        p99_us = np.percentile(arr, 99)
        max_us = np.max(arr)
        fps = 1_000_000.0 / mean_us if mean_us > 0 else 0
        print(f"[{name}]")
        print(f"  Mean:   {mean_us:6.2f} µs ({mean_us/1000.0:.4f} ms) | Equivalent: {fps:,.0f} Hz")
        print(f"  Median: {med_us:6.2f} µs ({med_us/1000.0:.4f} ms)")
        print(f"  P95:    {p95_us:6.2f} µs ({p95_us/1000.0:.4f} ms)")
        print(f"  P99:    {p99_us:6.2f} µs ({p99_us/1000.0:.4f} ms)")
        print(f"  Max:    {max_us:6.2f} µs ({max_us/1000.0:.4f} ms)")
        print()

    print_stats("Kalman Prediction Step", predict_times)
    print_stats("Kalman Update Step (Joseph Form)", update_times)
    print_stats("Mahalanobis Gating Test", gate_times)
    print_stats("Multi-Candidate Association (5 cands)", assoc_times)
    print_stats("Full End-to-End Track.step Cycle", full_cycle_times)


if __name__ == "__main__":
    benchmark_phase5_operations()
