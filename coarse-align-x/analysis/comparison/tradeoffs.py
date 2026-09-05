"""
Tradeoff Analyzer Module
========================
Accuracy vs latency trade-off analysis.
"""

from __future__ import annotations
from typing import Any, Dict, List, Tuple


class TradeoffAnalyzer:
    """Analyzes computational latency versus tracking accuracy trade-offs."""

    @staticmethod
    def extract_tradeoff_points(trials_by_algo: Dict[str, List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
        points = []
        for algo, trials in trials_by_algo.items():
            if not trials:
                continue
            errs = [t["metrics"]["mean_tracking_error_px"] for t in trials if "metrics" in t]
            lats = [t["metrics"]["mean_processing_latency_ms"] for t in trials if "metrics" in t]
            if errs and lats:
                points.append({
                    "algorithm": algo,
                    "mean_error_px": float(sum(errs) / len(errs)),
                    "mean_latency_ms": float(sum(lats) / len(lats)),
                })
        return points
