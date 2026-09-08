"""
Grid Evaluator Module
=====================
Grid cell evaluation over N x M parameter ranges.
"""

from __future__ import annotations
from typing import Any, Dict, List


class GridEvaluator:
    """Evaluates trials mapped across 2D disturbance parameter grid cells."""

    @staticmethod
    def evaluate_grid(trials: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        cells: Dict[str, List[Dict[str, Any]]] = {}
        for t in trials:
            cfg = t.get("resolved_configuration", {})
            cell_key = f"{cfg.get('dist1', 0.0)}_{cfg.get('dist2', 0.0)}"
            if cell_key not in cells:
                cells[cell_key] = []
            cells[cell_key].append(t)
        return cells
