"""
Baseline Comparison Module
===========================
Executes seed-matched B0 vs B1 vs B2 vs OURS paired benchmark analysis.
"""

from __future__ import annotations
from typing import Any, Dict, List, Tuple
import numpy as np
from analysis.statistics.effect_size import EffectSize
from analysis.statistics.paired_tests import PairedTests


class BaselineComparison:
    """Executes seed-matched comparisons across benchmark algorithms."""

    def compare_algorithms(self, trials_by_algo: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Any]:
        algos = ["B0", "B1", "B2", "OURS"]
        results = {}
        for pair in [("B1", "B0"), ("B2", "B1"), ("OURS", "B1"), ("OURS", "B2"), ("OURS", "B0")]:
            a1, a2 = pair
            t1 = trials_by_algo.get(a1, [])
            t2 = trials_by_algo.get(a2, [])

            err1 = [t["metrics"]["mean_tracking_error_px"] for t in t1 if "metrics" in t]
            err2 = [t["metrics"]["mean_tracking_error_px"] for t in t2 if "metrics" in t]

            if err1 and err2 and len(err1) == len(err2):
                p_val = PairedTests.paired_bootstrap_test(err1, err2)
                d = EffectSize.cohens_d(err1, err2)
                interp = EffectSize.interpret_cohens_d(d)
                results[f"{a1}_vs_{a2}"] = {
                    "p_value": p_val,
                    "cohens_d": d,
                    "interpretation": interp,
                    "significant": p_val < 0.05,
                }
            else:
                results[f"{a1}_vs_{a2}"] = {
                    "p_value": 1.0,
                    "cohens_d": 0.0,
                    "interpretation": "Insufficient paired data",
                    "significant": False,
                }
        return results
