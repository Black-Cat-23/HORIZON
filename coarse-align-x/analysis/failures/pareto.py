"""
Failure Pareto Module
=====================
Generates Pareto rankings for failure categories.
"""

from __future__ import annotations
from typing import Any, Dict, List, Tuple
from collections import Counter


class FailurePareto:
    """Generates Pareto ranking of failure modes."""

    @staticmethod
    def generate_pareto_ranking(failure_counts: Dict[str, int]) -> List[Tuple[str, int, float]]:
        total = sum(failure_counts.values())
        if total == 0:
            return []
        sorted_failures = sorted(failure_counts.items(), key=lambda x: x[1], reverse=True)
        cumulative = 0.0
        pareto = []
        for mode, cnt in sorted_failures:
            cumulative += cnt / total
            pareto.append((mode, cnt, cumulative * 100.0))
        return pareto
