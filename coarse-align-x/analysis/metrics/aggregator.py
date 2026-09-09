"""
Distribution Aggregator Module
==============================
Calculates summary statistics, percentiles (P50, P95, P99), and confidence intervals over trial distribution datasets.
"""

from __future__ import annotations
import math
from typing import Any, Dict, List, Sequence, Tuple
import numpy as np
from benchmark.metrics import compute_binomial_ci, compute_bootstrap_ci, compute_percentiles


class DistributionAggregator:
    """Aggregates scalar metrics into distribution summary statistics."""

    @staticmethod
    def aggregate_values(values: Sequence[float]) -> Dict[str, float]:
        if not values:
            return {
                "count": 0,
                "mean": 0.0,
                "median": 0.0,
                "std": 0.0,
                "min": 0.0,
                "max": 0.0,
                "p50": 0.0,
                "p95": 0.0,
                "p99": 0.0,
            }

        arr = np.array(values, dtype=np.float64)
        return {
            "count": len(arr),
            "mean": float(np.mean(arr)),
            "median": float(np.median(arr)),
            "std": float(np.std(arr, ddof=1)) if len(arr) > 1 else 0.0,
            "min": float(np.min(arr)),
            "max": float(np.max(arr)),
            "p50": float(np.percentile(arr, 50)),
            "p95": float(np.percentile(arr, 95)),
            "p99": float(np.percentile(arr, 99)),
        }

    @staticmethod
    def aggregate(trials: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Compute statistical summary across a list of trial results."""
        if not trials:
            return {}

        total_trials = len(trials)
        success_count = sum(1 for t in trials if t.get("success", False))
        succ_rate, succ_ci_lo, succ_ci_hi = compute_binomial_ci(success_count, total_trials)

        errors = [t["metrics"].get("mean_tracking_error", t["metrics"].get("mean_tracking_error_px", 0.0)) for t in trials if "metrics" in t]
        rmse_errors = [t["metrics"].get("RMSE_tracking_error", 0.0) for t in trials if "metrics" in t]
        locks = [t["metrics"].get("lock_retention_rate", 0.0) for t in trials if "metrics" in t]
        latencies = [t["metrics"].get("processing_time", t["metrics"].get("mean_processing_latency_ms", 0.0)) for t in trials if "metrics" in t]

        acq_times = [
            t["metrics"]["acquisition_time"]
            for t in trials
            if "metrics" in t and t["metrics"].get("acquisition_time") is not None
        ]
        reacq_times = [
            t["metrics"]["reacquisition_time"]
            for t in trials
            if "metrics" in t and t["metrics"].get("reacquisition_time") is not None
        ]

        mean_err, err_ci_lo, err_ci_hi = compute_bootstrap_ci(errors, stat_fn="mean") if errors else (0.0, 0.0, 0.0)
        med_err, med_ci_lo, med_ci_hi = compute_bootstrap_ci(errors, stat_fn="median") if errors else (0.0, 0.0, 0.0)
        mean_lock, lock_ci_lo, lock_ci_hi = compute_bootstrap_ci(locks, stat_fn="mean") if locks else (0.0, 0.0, 0.0)

        err_percentiles = compute_percentiles(errors)
        rmse_percentiles = compute_percentiles(rmse_errors)
        latency_percentiles = compute_percentiles(latencies)
        lock_percentiles = compute_percentiles(locks)

        return {
            "total_trials": total_trials,
            "success_count": success_count,
            "success_rate": succ_rate,
            "success_rate_ci95": [succ_ci_lo, succ_ci_hi],
            "tracking_error": {
                "mean": mean_err,
                "mean_ci95": [err_ci_lo, err_ci_hi],
                "median": med_err,
                "median_ci95": [med_ci_lo, med_ci_hi],
                "std": float(np.std(errors)) if errors else 0.0,
                "rmse": float(np.sqrt(np.mean(np.array(errors)**2))) if errors else 0.0,
                "min": err_percentiles["min"],
                "p50": err_percentiles["p50"],
                "p95": err_percentiles["p95"],
                "p99": err_percentiles["p99"],
                "max": err_percentiles["max"],
            },
            "rmse_tracking_error": {
                "mean": float(np.mean(rmse_errors)) if rmse_errors else 0.0,
                "median": rmse_percentiles["median"],
                "p50": rmse_percentiles["p50"],
                "p95": rmse_percentiles["p95"],
                "p99": rmse_percentiles["p99"],
                "min": rmse_percentiles["min"],
                "max": rmse_percentiles["max"],
            },
            "lock_retention_rate": {
                "mean": mean_lock,
                "mean_ci95": [lock_ci_lo, lock_ci_hi],
                "median": lock_percentiles["median"],
                "std": float(np.std(locks)) if locks else 0.0,
                "p50": lock_percentiles["p50"],
                "p95": lock_percentiles["p95"],
                "p99": lock_percentiles["p99"],
                "min": lock_percentiles["min"],
                "max": lock_percentiles["max"],
            },
            "latency_ms": {
                "mean": float(np.mean(latencies)) if latencies else 0.0,
                "median": latency_percentiles["median"],
                "p50": latency_percentiles["p50"],
                "p95": latency_percentiles["p95"],
                "p99": latency_percentiles["p99"],
                "min": latency_percentiles["min"],
                "max": latency_percentiles["max"],
            },
            "acquisition_time_s": {
                "count": len(acq_times),
                "mean": float(np.mean(acq_times)) if acq_times else None,
                "median": float(np.median(acq_times)) if acq_times else None,
                "p50": float(np.percentile(acq_times, 50)) if acq_times else None,
                "p95": float(np.percentile(acq_times, 95)) if acq_times else None,
                "p99": float(np.percentile(acq_times, 99)) if acq_times else None,
                "min": float(np.min(acq_times)) if acq_times else None,
                "max": float(np.max(acq_times)) if acq_times else None,
            },
            "reacquisition_time_s": {
                "count": len(reacq_times),
                "mean": float(np.mean(reacq_times)) if reacq_times else None,
                "median": float(np.median(reacq_times)) if reacq_times else None,
                "p50": float(np.percentile(reacq_times, 50)) if reacq_times else None,
                "p95": float(np.percentile(reacq_times, 95)) if reacq_times else None,
                "p99": float(np.percentile(reacq_times, 99)) if reacq_times else None,
                "min": float(np.min(reacq_times)) if reacq_times else None,
                "max": float(np.max(reacq_times)) if reacq_times else None,
            },
        }
