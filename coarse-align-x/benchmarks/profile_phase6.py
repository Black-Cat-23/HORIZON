"""
Phase 6 Closed-Loop PAT Benchmark & Profiler.
HORIZON Phase 6
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import time
import numpy as np
from pat.mode_manager import PATModeManager
from control.camera_controller import PATCameraController
from tracking.association.track import Track


def run_benchmark(num_iterations: int = 10000):
    pat_mgr = PATModeManager()
    pat_ctrl = PATCameraController()
    track = Track(track_id=1)

    latencies_us = []

    for i in range(num_iterations):
        t_start = time.perf_counter()

        # Step 1: Kalman Track Step
        est = track.step(
            measurement=(320.0 + np.sin(i * 0.1) * 10.0, 240.0 + np.cos(i * 0.1) * 10.0),
            confidence=0.9,
            timestamp=i * 0.016,
        )

        # Step 2: PAT Mode Manager
        state = pat_mgr.process_step(
            dt=0.016,
            timestamp_s=i * 0.016,
            detection_valid=True,
            detection_confidence=0.9,
            mahalanobis_d2=est.mahalanobis_distance**2,
            covariance_trace=est.position_uncertainty**2,
            estimated_u_px=est.estimated_x,
            estimated_v_px=est.estimated_y,
            estimated_vx_px_s=est.estimated_vx,
            estimated_vy_px_s=est.estimated_vy,
            current_pan_deg=0.0,
            current_tilt_deg=0.0,
        )

        # Step 3: Controller
        pat_ctrl.compute_control_command(
            dt=0.016,
            pat_state=state,
            search_pan_rate=0.0,
            search_tilt_rate=0.0,
            reacquire_pan_rate=0.0,
            reacquire_tilt_rate=0.0,
        )

        t_end = time.perf_counter()
        latencies_us.append((t_end - t_start) * 1e6)

    arr = np.array(latencies_us)
    mean_us = np.mean(arr)
    median_us = np.median(arr)
    p95_us = np.percentile(arr, 95)
    p99_us = np.percentile(arr, 99)
    max_us = np.max(arr)
    throughput_hz = 1e6 / mean_us

    print("============================================================")
    print("PHASE 6 CLOSED-LOOP PAT BENCHMARK RESULTS")
    print("============================================================")
    print(f"Iterations Evaluated: {num_iterations:,}")
    print(f"Mean Latency:         {mean_us:.2f} µs")
    print(f"Median Latency:       {median_us:.2f} µs")
    print(f"P95 Latency:          {p95_us:.2f} µs")
    print(f"P99 Latency:          {p99_us:.2f} µs")
    print(f"Maximum Latency:      {max_us:.2f} µs")
    print(f"Throughput:           {throughput_hz:,.0f} Hz")
    print("============================================================")


if __name__ == "__main__":
    run_benchmark()
