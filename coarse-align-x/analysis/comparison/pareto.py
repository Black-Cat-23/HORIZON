"""
Pareto Frontier Module
======================
Calculates non-dominated Pareto frontier algorithms for error vs. latency.
"""

from __future__ import annotations
from typing import Any, Dict, List


class ParetoFrontier:
    """Identifies Pareto-optimal configurations for multi-objective trade-offs."""

    @staticmethod
    def calculate_pareto_frontier(points: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        # Objective: Minimize error AND minimize latency
        pareto = []
        for i, p1 in enumerate(points):
            dominated = False
            for j, p2 in enumerate(points):
                if i != j:
                    if p2["mean_error_px"] <= p1["mean_error_px"] and p2["mean_latency_ms"] <= p1["mean_latency_ms"]:
                        if p2["mean_error_px"] < p1["mean_error_px"] or p2["mean_latency_ms"] < p1["mean_latency_ms"]:
                            dominated = True
                            break
            if not dominated:
                pareto.append(p1)
        return pareto
