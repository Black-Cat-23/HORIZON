"""
Robustness Envelope Engine
==========================
2D parameter sweeps, robustness heatmaps, classification boundaries, and simulation robustness regions.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Tuple
import numpy as np


@dataclass
class RobustnessGridCell:
    param_x_val: float
    param_y_val: float
    trials_count: int
    success_count: int
    success_rate: float
    median_error: float
    p95_error: float
    classification: str  # "SUCCESS", "DEGRADED", "FAILURE"


class RobustnessEnvelopeEngine:
    """Generates 2D parameter sweep heatmaps and boundary classifications."""

    def __init__(
        self,
        success_rate_threshold: float = 0.90,
        degraded_rate_threshold: float = 0.60,
        max_degraded_error_px: float = 25.0,
    ) -> None:
        self.success_rate_threshold = success_rate_threshold
        self.degraded_rate_threshold = degraded_rate_threshold
        self.max_degraded_error_px = max_degraded_error_px

    def classify_cell(self, success_rate: float, median_error: float) -> str:
        """Classify grid cell into SUCCESS, DEGRADED, or FAILURE."""
        if success_rate >= self.success_rate_threshold and median_error <= self.max_degraded_error_px:
            return "SUCCESS"
        elif success_rate >= self.degraded_rate_threshold:
            return "DEGRADED"
        else:
            return "FAILURE"

    def evaluate_grid(
        self,
        param_x_name: str,
        param_x_values: List[float],
        param_y_name: str,
        param_y_values: List[float],
        cell_evaluator: Callable[[float, float], Tuple[int, int, float, float]],
    ) -> Dict[str, Any]:
        """Run 2D parameter grid sweep using provided evaluator function.

        cell_evaluator(x_val, y_val) -> (trials_count, success_count, median_error, p95_error)
        """
        grid_results: List[Dict[str, Any]] = []
        matrix_success = np.zeros((len(param_y_values), len(param_x_values)), dtype=float)
        matrix_error = np.zeros((len(param_y_values), len(param_x_values)), dtype=float)
        matrix_class = []

        for i, y_val in enumerate(param_y_values):
            class_row = []
            for j, x_val in enumerate(param_x_values):
                n_trials, n_success, med_err, p95_err = cell_evaluator(x_val, y_val)
                succ_rate = n_success / n_trials if n_trials > 0 else 0.0
                cell_class = self.classify_cell(succ_rate, med_err)

                matrix_success[i, j] = succ_rate
                matrix_error[i, j] = med_err
                class_row.append(cell_class)

                cell = RobustnessGridCell(
                    param_x_val=x_val,
                    param_y_val=y_val,
                    trials_count=n_trials,
                    success_count=n_success,
                    success_rate=succ_rate,
                    median_error=med_err,
                    p95_error=p95_err,
                    classification=cell_class,
                )
                grid_results.append(cell.__dict__)

            matrix_class.append(class_row)

        return {
            "param_x": {"name": param_x_name, "values": param_x_values},
            "param_y": {"name": param_y_name, "values": param_y_values},
            "grid_results": grid_results,
            "success_rate_matrix": matrix_success.tolist(),
            "median_error_matrix": matrix_error.tolist(),
            "classification_matrix": matrix_class,
        }
