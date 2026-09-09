"""
Seed-Matched Difference Engine
==============================
Compares matched trials sharing identical scenario and seed across different algorithm paths.
Analyzes per-trial differences: Delta_i = Metric_A,i - Metric_B,i.
"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple
import numpy as np


class SeedMatchedAnalyzer:
    """Computes paired trial-by-trial metrics across algorithm configurations."""

    @staticmethod
    def match_trials(
        trials_a: List[Dict[str, Any]],
        trials_b: List[Dict[str, Any]],
        key_fields: Tuple[str, ...] = ("scenario_id", "seed"),
    ) -> List[Tuple[Dict[str, Any], Dict[str, Any]]]:
        """Match trials between Method A and Method B by key_fields."""
        map_b: Dict[Tuple[Any, ...], Dict[str, Any]] = {}
        for t in trials_b:
            key = tuple(t.get(k) for k in key_fields)
            map_b[key] = t

        matched_pairs: List[Tuple[Dict[str, Any], Dict[str, Any]]] = []
        for t_a in trials_a:
            key = tuple(t_a.get(k) for k in key_fields)
            if key in map_b:
                matched_pairs.append((t_a, map_b[key]))

        return matched_pairs

    @classmethod
    def analyze_paired_differences(
        self,
        trials_a: List[Dict[str, Any]],
        trials_b: List[Dict[str, Any]],
        alg_a_name: str = "OURS",
        alg_b_name: str = "BASELINE",
        metrics_to_compare: Tuple[str, ...] = (
            "mean_tracking_error",
            "RMSE_tracking_error",
            "P95_tracking_error",
            "processing_time",
            "lock_retention_rate",
        ),
    ) -> Dict[str, Any]:
        """Compute per-trial deltas (A - B) for all matched seeds."""
        pairs = self.match_trials(trials_a, trials_b)
        if not pairs:
            return {
                "comparison_pair": f"{alg_a_name} vs {alg_b_name}",
                "matched_trial_count": 0,
                "metrics": {},
                "seed_level_deltas": [],
            }

        metric_results: Dict[str, Dict[str, Any]] = {}
        seed_level_deltas: List[Dict[str, Any]] = []

        for m_key in metrics_to_compare:
            deltas: List[float] = []
            vals_a: List[float] = []
            vals_b: List[float] = []

            for t_a, t_b in pairs:
                v_a = float(t_a.get("metrics", {}).get(m_key, 0.0))
                v_b = float(t_b.get("metrics", {}).get(m_key, 0.0))
                delta = v_a - v_b
                deltas.append(delta)
                vals_a.append(v_a)
                vals_b.append(v_b)

                if m_key == metrics_to_compare[0]:
                    seed_level_deltas.append({
                        "scenario_id": t_a.get("scenario_id"),
                        "seed": t_a.get("seed"),
                        f"val_{alg_a_name}": v_a,
                        f"val_{alg_b_name}": v_b,
                        "delta": delta,
                    })

            arr_d = np.array(deltas, dtype=np.float64)
            pct_improved = float(np.mean(arr_d < 0)) * 100.0 if "error" in m_key or "time" in m_key else float(np.mean(arr_d > 0)) * 100.0

            metric_results[m_key] = {
                "mean_delta": float(np.mean(arr_d)),
                "median_delta": float(np.median(arr_d)),
                "std_delta": float(np.std(arr_d, ddof=1)) if len(arr_d) > 1 else 0.0,
                "p50_delta": float(np.percentile(arr_d, 50)),
                "p95_delta": float(np.percentile(arr_d, 95)),
                "p99_delta": float(np.percentile(arr_d, 99)),
                "min_delta": float(np.min(arr_d)),
                "max_delta": float(np.max(arr_d)),
                "pct_trials_improved": pct_improved,
            }

        return {
            "comparison_pair": f"{alg_a_name} vs {alg_b_name}",
            "matched_trial_count": len(pairs),
            "metrics": metric_results,
            "seed_level_deltas": seed_level_deltas,
        }
