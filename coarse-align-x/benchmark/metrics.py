"""
Metric Engine and Statistical Metrics
=====================================
Centralized metric calculations, formula implementations, binomial & bootstrap confidence intervals.

Ground-Truth Usage Constraint: Ground truth is used STRICTLY for post-hoc metric evaluation.
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Tuple, Union
import numpy as np


def compute_percentiles(values: List[float] | np.ndarray) -> Dict[str, float]:
    """Compute P50, P95, P99, min, median, and max from a numeric sequence."""
    arr = np.asarray(values, dtype=float)
    if len(arr) == 0:
        return {"min": 0.0, "median": 0.0, "p50": 0.0, "p95": 0.0, "p99": 0.0, "max": 0.0}
    return {
        "min": float(np.min(arr)),
        "median": float(np.median(arr)),
        "p50": float(np.percentile(arr, 50)),
        "p95": float(np.percentile(arr, 95)),
        "p99": float(np.percentile(arr, 99)),
        "max": float(np.max(arr)),
    }


def compute_binomial_ci(
    successes: int, total: int, confidence: float = 0.95
) -> Tuple[float, float, float]:
    """Wilson score interval for binomial proportions.

    Returns:
        (proportion, ci_lower, ci_upper)
    """
    if total <= 0:
        return (0.0, 0.0, 0.0)

    p_hat = successes / total
    if confidence == 0.95:
        z = 1.95996
    elif confidence == 0.99:
        z = 2.57583
    else:
        z = 1.64485  # 90% default fallback

    denominator = 1.0 + (z**2) / total
    center = (p_hat + (z**2) / (2.0 * total)) / denominator
    spread = (
        z
        * math.sqrt((p_hat * (1.0 - p_hat) / total) + ((z**2) / (4.0 * total**2)))
        / denominator
    )

    lower = max(0.0, center - spread)
    upper = min(1.0, center + spread)
    return (float(p_hat), float(lower), float(upper))


def compute_bootstrap_ci(
    data: List[float] | np.ndarray,
    stat_fn: str = "mean",
    num_samples: int = 1000,
    confidence: float = 0.95,
    seed: int = 42,
) -> Tuple[float, float, float]:
    """Non-parametric bootstrap confidence interval for continuous data.

    Returns:
        (point_estimate, ci_lower, ci_upper)
    """
    arr = np.asarray(data, dtype=float)
    if len(arr) == 0:
        return (0.0, 0.0, 0.0)
    if len(arr) == 1:
        val = float(arr[0])
        return (val, val, val)

    rng = np.random.default_rng(seed)

    if stat_fn == "mean":
        calc = np.mean
    elif stat_fn == "median":
        calc = np.median
    elif stat_fn == "std":
        calc = np.std
    elif stat_fn == "rmse":
        calc = lambda x: np.sqrt(np.mean(x**2))
    else:
        calc = np.mean

    point_est = float(calc(arr))

    # Bootstrap resampling
    indices = rng.integers(0, len(arr), size=(num_samples, len(arr)))
    boot_stats = calc(arr[indices], axis=1)

    alpha = 1.0 - confidence
    lower_pct = (alpha / 2.0) * 100.0
    upper_pct = (1.0 - alpha / 2.0) * 100.0

    ci_lower = float(np.percentile(boot_stats, lower_pct))
    ci_upper = float(np.percentile(boot_stats, upper_pct))

    return (point_est, ci_lower, ci_upper)


class MetricEngine:
    """Centralized Metric Engine for trial telemetry parsing and evaluation."""

    def __init__(self, fov_deg: float = 4.0, sensor_width_px: int = 640) -> None:
        self.fov_deg = fov_deg
        self.sensor_width_px = sensor_width_px
        # Convert deg to rad per pixel for angular error
        self.deg_per_px = fov_deg / sensor_width_px
        self.rad_per_px = math.radians(self.deg_per_px)

    def evaluate_telemetry(self, telemetry_records: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Compute all Phase 9 required metrics from a trial's frame telemetry records.

        Expected telemetry record keys:
            timestamp, frame_idx, state ("SEARCH", "ACQUIRING", "TRACK", "LOST"),
            true_x, true_y, est_x, est_y, det_x, det_y, detected (bool),
            processing_time_ms, pan_cmd, tilt_cmd, is_saturated (bool)
        """
        if not telemetry_records:
            return self._empty_metrics()

        n_frames = len(telemetry_records)
        dt_list = []
        proc_times = []
        pixel_errors = []
        angular_errors = []
        states = []
        is_detected_list = []
        is_saturated_list = []
        pred_only_flags = []

        for i, rec in enumerate(telemetry_records):
            states.append(rec.get("state", "SEARCH"))
            proc_ms = rec.get("processing_time_ms", 0.0)
            proc_times.append(proc_ms)
            is_detected_list.append(rec.get("detected", False))
            is_saturated_list.append(rec.get("is_saturated", False))

            # Pred only flag (estimated coordinates present without detection)
            det = rec.get("detected", False)
            est_x = rec.get("est_x", None)
            if est_x is not None and not det:
                pred_only_flags.append(True)
            else:
                pred_only_flags.append(False)

            # Error calculation vs ground truth
            true_x = rec.get("true_x", None)
            true_y = rec.get("true_y", None)
            est_y = rec.get("est_y", None)

            if true_x is not None and true_y is not None and est_x is not None and est_y is not None:
                err = math.sqrt((est_x - true_x)**2 + (est_y - true_y)**2)
                pixel_errors.append(err)
                angular_errors.append(err * self.rad_per_px)

            if i > 0:
                dt_list.append(rec["timestamp"] - telemetry_records[i-1]["timestamp"])

        # 1. Timing & Speed
        t_start = telemetry_records[0]["timestamp"]
        t_end = telemetry_records[-1]["timestamp"]
        simulation_duration = max(0.0, t_end - t_start)
        
        proc_arr = np.asarray(proc_times, dtype=float)
        processing_time_mean = float(np.mean(proc_arr)) if len(proc_arr) > 0 else 0.0
        p95_processing_time = float(np.percentile(proc_arr, 95)) if len(proc_arr) > 0 else 0.0
        
        # FPS calculation
        fps_list = [1000.0 / p if p > 0 else 60.0 for p in proc_times]
        average_fps = float(np.mean(fps_list)) if fps_list else 0.0
        minimum_fps = float(np.min(fps_list)) if fps_list else 0.0

        # 2. State & Acquisition / Reacquisition logic
        acq_start_ts: Optional[float] = t_start
        acq_confirmed_ts: Optional[float] = None
        acquisition_time: Optional[float] = None

        loss_timestamps: List[float] = []
        reacq_start_timestamps: List[float] = []
        reacq_success_timestamps: List[float] = []
        reacq_times: List[float] = []
        
        track_frame_count = 0
        in_loss = False
        loss_start_t = 0.0

        for i, rec in enumerate(telemetry_records):
            st = rec.get("state", "SEARCH")
            ts = rec["timestamp"]

            if st == "TRACK":
                track_frame_count += 1
                if acq_confirmed_ts is None:
                    acq_confirmed_ts = ts
                    acquisition_time = max(0.0, acq_confirmed_ts - acq_start_ts)

                if in_loss:
                    # Reacquisition successful
                    reacq_success_timestamps.append(ts)
                    reacq_times.append(ts - loss_start_t)
                    in_loss = False

            elif st == "LOST":
                if not in_loss and acq_confirmed_ts is not None:
                    # Target loss event
                    in_loss = True
                    loss_start_t = ts
                    loss_timestamps.append(ts)
                    reacq_start_timestamps.append(ts)

        target_loss_count = len(loss_timestamps)
        successful_reacquisition_count = len(reacq_times)
        failed_reacquisition_count = target_loss_count - successful_reacquisition_count

        mean_reacquisition_time = float(np.mean(reacq_times)) if reacq_times else None
        median_reacquisition_time = float(np.median(reacq_times)) if reacq_times else None

        # 3. Lock Retention Rate
        # Eligible experiment time = duration - acquisition_time (or total duration if no acquisition)
        if acquisition_time is not None and simulation_duration > acquisition_time:
            eligible_time = simulation_duration - acquisition_time
        else:
            eligible_time = simulation_duration

        time_in_confirmed_track = (track_frame_count / n_frames) * simulation_duration
        lock_retention_rate = min(1.0, max(0.0, time_in_confirmed_track / eligible_time)) if eligible_time > 0 else 0.0

        # 4. Tracking Error Metrics
        err_arr = np.asarray(pixel_errors, dtype=float)
        if len(err_arr) > 0:
            mean_tracking_error = float(np.mean(err_arr))
            median_tracking_error = float(np.median(err_arr))
            rmse_tracking_error = float(np.sqrt(np.mean(err_arr**2)))
            p95_tracking_error = float(np.percentile(err_arr, 95))
            p99_tracking_error = float(np.percentile(err_arr, 99))
            maximum_tracking_error = float(np.max(err_arr))
        else:
            mean_tracking_error = median_tracking_error = rmse_tracking_error = 0.0
            p95_tracking_error = p99_tracking_error = maximum_tracking_error = 0.0

        # Angular RMSE
        ang_arr = np.asarray(angular_errors, dtype=float)
        rmse_angular_error = float(np.sqrt(np.mean(ang_arr**2))) if len(ang_arr) > 0 else 0.0

        # 5. Perception Quality & Saturation
        det_count = sum(1 for d in is_detected_list if d)
        detection_success_rate = det_count / n_frames if n_frames > 0 else 0.0
        false_detection_rate = 1.0 - detection_success_rate
        controller_saturation_count = sum(1 for s in is_saturated_list if s)
        prediction_only_duration = (sum(1 for p in pred_only_flags if p) / n_frames) * simulation_duration

        return {
            "simulation_duration": simulation_duration,
            "average_fps": average_fps,
            "minimum_fps": minimum_fps,
            "processing_time": processing_time_mean,
            "P95_processing_time": p95_processing_time,
            "acquisition_start_timestamp": acq_start_ts,
            "acquisition_confirmed_timestamp": acq_confirmed_ts,
            "acquisition_time": acquisition_time,
            "reacquisition_time": mean_reacquisition_time,
            "median_reacquisition_time": median_reacquisition_time,
            "mean_tracking_error": mean_tracking_error,
            "median_tracking_error": median_tracking_error,
            "RMSE_tracking_error": rmse_tracking_error,
            "P95_tracking_error": p95_tracking_error,
            "P99_tracking_error": p99_tracking_error,
            "maximum_tracking_error": maximum_tracking_error,
            "RMSE_angular_error_rad": rmse_angular_error,
            "lock_retention_rate": lock_retention_rate,
            "target_loss_count": target_loss_count,
            "successful_reacquisition_count": successful_reacquisition_count,
            "failed_reacquisition_count": failed_reacquisition_count,
            "false_detection_rate": false_detection_rate,
            "detection_success_rate": detection_success_rate,
            "controller_saturation_count": controller_saturation_count,
            "prediction_only_duration": prediction_only_duration,
        }

    def _empty_metrics(self) -> Dict[str, Any]:
        return {
            "simulation_duration": 0.0,
            "average_fps": 0.0,
            "minimum_fps": 0.0,
            "processing_time": 0.0,
            "P95_processing_time": 0.0,
            "acquisition_start_timestamp": None,
            "acquisition_confirmed_timestamp": None,
            "acquisition_time": None,
            "reacquisition_time": None,
            "median_reacquisition_time": None,
            "mean_tracking_error": 0.0,
            "median_tracking_error": 0.0,
            "RMSE_tracking_error": 0.0,
            "P95_tracking_error": 0.0,
            "P99_tracking_error": 0.0,
            "maximum_tracking_error": 0.0,
            "RMSE_angular_error_rad": 0.0,
            "lock_retention_rate": 0.0,
            "target_loss_count": 0,
            "successful_reacquisition_count": 0,
            "failed_reacquisition_count": 0,
            "false_detection_rate": 0.0,
            "detection_success_rate": 0.0,
            "controller_saturation_count": 0,
            "prediction_only_duration": 0.0,
        }
