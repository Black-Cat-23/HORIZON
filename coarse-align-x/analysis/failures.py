"""
Failure Analysis & Root-Cause Attribution Engine
================================================
Aggregates failure modes, failure rates, and root-cause taxonomies across baseline algorithms.
"""

from __future__ import annotations

from typing import Any, Dict, List
from benchmark.failure import FailureCategory


class FailureAnalyzer:
    """Analyzes and categorizes trial outcome statuses into formal failure taxonomies."""

    @staticmethod
    def analyze_trial_group(trials: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Compute failure breakdown matrix across a list of trial results."""
        total_trials = len(trials)
        if total_trials == 0:
            return {"total_trials": 0, "failure_counts": {}, "failure_percentages": {}}

        counts: Dict[str, int] = {cat.value: 0 for cat in FailureCategory}
        for t in trials:
            status = t.get("status", FailureCategory.SUCCESS.value)
            counts[status] = counts.get(status, 0) + 1

        percentages = {cat: (cnt / total_trials) * 100.0 for cat, cnt in counts.items()}

        return {
            "total_trials": total_trials,
            "failure_counts": counts,
            "failure_percentages": percentages,
        }
