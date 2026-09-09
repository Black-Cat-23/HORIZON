"""
Hypothesis Testing & Statistical Superiority Engine
===================================================
Pairwise algorithm hypothesis tests, non-parametric effect sizes, and Benjamini-Hochberg FDR control.
"""

from __future__ import annotations
from typing import Any, Dict, List
import numpy as np

from benchmark.statistics import (
    benjamini_hochberg_correction,
    cliffs_delta,
    cohens_d,
    paired_bootstrap_test,
)


class HypothesisTestingEngine:
    """Performs pairwise hypothesis tests and calculates effect sizes across algorithms."""

    @staticmethod
    def compare_algorithm_pair(
        name_a: str,
        errors_a: List[float],
        name_b: str,
        errors_b: List[float],
        seed: int = 42,
    ) -> Dict[str, Any]:
        """Compare performance distributions between algorithm A and algorithm B."""
        arr_a = np.asarray(errors_a, dtype=float)
        arr_b = np.asarray(errors_b, dtype=float)

        mean_a, mean_b = float(np.mean(arr_a)) if len(arr_a) else 0.0, float(np.mean(arr_b)) if len(arr_b) else 0.0
        delta_mean = mean_a - mean_b
        pct_improvement = ((mean_b - mean_a) / mean_b) * 100.0 if mean_b > 0 else 0.0

        d_val = cohens_d(arr_a, arr_b)
        delta_val = cliffs_delta(arr_a, arr_b)

        if len(arr_a) == len(arr_b) and len(arr_a) > 0:
            boot_res = paired_bootstrap_test(arr_a, arr_b, seed=seed)
            p_val = boot_res["p_value"]
        else:
            boot_res = {"p_value": 1.0, "ci_lower": 0.0, "ci_upper": 0.0}
            p_val = 1.0

        abs_d = abs(d_val)
        if abs_d >= 0.8:
            effect_label = "Large"
        elif abs_d >= 0.5:
            effect_label = "Medium"
        elif abs_d >= 0.2:
            effect_label = "Small"
        else:
            effect_label = "Negligible"

        return {
            "pair": f"{name_a} vs {name_b}",
            "mean_a": mean_a,
            "mean_b": mean_b,
            "delta_mean": delta_mean,
            "percentage_improvement": pct_improvement,
            "p_value": p_val,
            "cohens_d": d_val,
            "cliffs_delta": delta_val,
            "effect_size_label": effect_label,
            "bootstrap_ci95": [boot_res.get("ci_lower", 0.0), boot_res.get("ci_upper", 0.0)],
        }

    @classmethod
    def evaluate_battlefield_matrix(
        cls, algorithm_data: Dict[str, List[float]], fdr_rate: float = 0.05
    ) -> Dict[str, Any]:
        """Perform all pairwise comparisons and apply Benjamini-Hochberg FDR correction."""
        alg_names = list(algorithm_data.keys())
        pairwise_results: List[Dict[str, Any]] = []
        p_values: List[float] = []

        for i in range(len(alg_names)):
            for j in range(i + 1, len(alg_names)):
                name_a, name_b = alg_names[i], alg_names[j]
                res = cls.compare_algorithm_pair(name_a, algorithm_data[name_a], name_b, algorithm_data[name_b])
                pairwise_results.append(res)
                p_values.append(res["p_value"])

        bh_corrections = benjamini_hochberg_correction(p_values, fdr_rate=fdr_rate)
        for idx, (adj_p, is_sig) in enumerate(bh_corrections):
            pairwise_results[idx]["adjusted_p_value"] = adj_p
            pairwise_results[idx]["is_statistically_significant"] = is_sig

        return {"pairwise_comparisons": pairwise_results}
