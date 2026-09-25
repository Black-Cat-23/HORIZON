"""
Counterfactual Disturbance Analysis Engine
===========================================
Isolates the empirical performance impact of individual environmental disturbances using seed-matched paired counterfactual trials.
"""

from __future__ import annotations

from typing import Any, Dict, List
import numpy as np


class CounterfactualAnalyzer:
    """Analyzes paired trial results to isolate individual disturbance effects."""

    @staticmethod
    def analyze_disturbance_effect(
        clean_trials: List[Dict[str, Any]],
        disturbed_trials: List[Dict[str, Any]],
        disturbance_name: str = "jitter",
    ) -> Dict[str, Any]:
        """Compare clean baseline vs single-disturbance baseline on matched seeds."""
        map_clean = {(t.get("scenario_id"), t.get("seed")): t for t in clean_trials}
        pairs = []

        for t_dist in disturbed_trials:
            key = (t_dist.get("scenario_id"), t_dist.get("seed"))
            if key in map_clean:
                pairs.append((map_clean[key], t_dist))

        if not pairs:
            return {
                "disturbance_name": disturbance_name,
                "matched_pairs_count": 0,
                "delta_mean_tracking_error_px": 0.0,
                "delta_lock_retention_rate": 0.0,
                "delta_processing_time_ms": 0.0,
                "isolated_impact_summary": "No matched seeds available for counterfactual analysis.",
            }

        err_clean = [t_c["metrics"].get("mean_tracking_error", 0.0) for t_c, _ in pairs]
        err_dist = [t_d["metrics"].get("mean_tracking_error", 0.0) for _, t_d in pairs]

        lock_clean = [t_c["metrics"].get("lock_retention_rate", 1.0) for t_c, _ in pairs]
        lock_dist = [t_d["metrics"].get("lock_retention_rate", 1.0) for _, t_d in pairs]

        time_clean = [t_c["metrics"].get("processing_time", 0.0) for t_c, _ in pairs]
        time_dist = [t_d["metrics"].get("processing_time", 0.0) for _, t_d in pairs]

        err_deltas = np.array(err_dist) - np.array(err_clean)
        lock_deltas = np.array(lock_dist) - np.array(lock_clean)
        time_deltas = np.array(time_dist) - np.array(time_clean)

        return {
            "disturbance_name": disturbance_name,
            "matched_pairs_count": len(pairs),
            "clean_baseline": {
                "mean_tracking_error": float(np.mean(err_clean)),
                "mean_lock_retention": float(np.mean(lock_clean)),
                "mean_processing_time": float(np.mean(time_clean)),
            },
            "disturbed_baseline": {
                "mean_tracking_error": float(np.mean(err_dist)),
                "mean_lock_retention": float(np.mean(lock_dist)),
                "mean_processing_time": float(np.mean(time_dist)),
            },
            "isolated_delta": {
                "tracking_error_increase_px": float(np.mean(err_deltas)),
                "lock_retention_drop_pct": float(-np.mean(lock_deltas) * 100.0),
                "processing_latency_increase_ms": float(np.mean(time_deltas)),
            },
        }
