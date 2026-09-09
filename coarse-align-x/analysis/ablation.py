"""
Component Ablation Analysis Engine
===================================
Quantifies the statistical contribution of individual architecture components (e.g. IMM-EKF, Association Gating, Feedforward Control)
by analyzing performance drops under ablated pipeline configurations.
"""

from __future__ import annotations

from typing import Any, Dict, List
import numpy as np
from benchmark.statistics import cohens_d, paired_wilcoxon_test


class AblationAnalyzer:
    """Analyzes pipeline performance under component ablations."""

    @staticmethod
    def compare_ablation_variant(
        full_pipeline_trials: List[Dict[str, Any]],
        ablated_pipeline_trials: List[Dict[str, Any]],
        ablated_component_name: str,
    ) -> Dict[str, Any]:
        """Compare full architecture against ablated pipeline variant on matched seeds."""
        map_full = {(t.get("scenario_id"), t.get("seed")): t for t in full_pipeline_trials}
        pairs = []

        for t_abl in ablated_pipeline_trials:
            key = (t_abl.get("scenario_id"), t_abl.get("seed"))
            if key in map_full:
                pairs.append((map_full[key], t_abl))

        if not pairs:
            return {
                "ablated_component": ablated_component_name,
                "matched_pairs_count": 0,
                "demonstrated_benefit": False,
                "benefit_summary": "No matched seed data available for ablation comparison.",
            }

        err_full = [t_f["metrics"].get("mean_tracking_error", 0.0) for t_f, _ in pairs]
        err_abl = [t_a["metrics"].get("mean_tracking_error", 0.0) for _, t_a in pairs]

        lock_full = [t_f["metrics"].get("lock_retention_rate", 1.0) for t_f, _ in pairs]
        lock_abl = [t_a["metrics"].get("lock_retention_rate", 1.0) for _, t_a in pairs]

        # Metric delta: Full vs Ablated
        err_diff = np.array(err_abl) - np.array(err_full)  # positive if ablation increases error
        lock_diff = np.array(lock_full) - np.array(lock_abl) # positive if full has higher lock rate

        d_err = cohens_d(err_abl, err_full)
        test_res = paired_wilcoxon_test(err_abl, err_full) if len(err_full) > 0 else {"p_value": 1.0}

        # Component benefit is strictly demonstrated ONLY if error increases or lock rate drops with p < 0.05
        is_benefit_demonstrated = (float(np.mean(err_diff)) > 0.5 or float(np.mean(lock_diff)) > 0.05) and (test_res["p_value"] < 0.05)

        return {
            "ablated_component": ablated_component_name,
            "matched_pairs_count": len(pairs),
            "full_pipeline_metrics": {
                "mean_tracking_error_px": float(np.mean(err_full)),
                "mean_lock_retention": float(np.mean(lock_full)),
            },
            "ablated_pipeline_metrics": {
                "mean_tracking_error_px": float(np.mean(err_abl)),
                "mean_lock_retention": float(np.mean(lock_abl)),
            },
            "component_delta": {
                "tracking_error_penalty_px": float(np.mean(err_diff)),
                "lock_retention_loss_pct": float(np.mean(lock_diff) * 100.0),
                "cohens_d": float(d_err),
                "p_value": float(test_res["p_value"]),
            },
            "demonstrated_benefit": is_benefit_demonstrated,
            "scientific_claim": (
                f"Component '{ablated_component_name}' improves mean error by {float(np.mean(err_diff)):.2f}px (p={test_res['p_value']:.4f}, d={d_err:.2f})"
                if is_benefit_demonstrated
                else f"Component '{ablated_component_name}' does NOT show statistically significant benefit under current benchmark conditions (p={test_res['p_value']:.4f})"
            ),
        }
