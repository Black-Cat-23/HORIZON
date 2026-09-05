"""
Robustness Envelope Module
==========================
Generates 2D parameter heatmaps and operational robustness matrices.
"""

from __future__ import annotations
from typing import Any, Dict, List
import numpy as np
from benchmark.robustness import RobustnessEnvelopeEngine
from analysis.robustness.boundary_analysis import BoundaryAnalyzer, RobustnessRegion


class RobustnessEnvelope:
    """Generates machine-readable 2D robustness matrices over disturbance parameters."""

    def build_envelope_matrix(
        self,
        grid_results: Dict[str, Dict[str, Any]],
        param1_name: str,
        param2_name: str,
    ) -> Dict[str, Any]:
        matrix = {}
        for key, res in grid_results.items():
            err = res.get("mean_error", 100.0)
            ret = res.get("lock_retention", 0.0)
            reg = BoundaryAnalyzer.classify_region(err, ret)
            matrix[key] = {
                "mean_error": err,
                "lock_retention": ret,
                "region": reg.value,
            }
        return {
            "param1": param1_name,
            "param2": param2_name,
            "matrix": matrix,
        }


class RobustnessMapGenerator:
    """Generates 2D parameter grid heatmaps and boundary region transition boundaries."""

    def __init__(
        self,
        stable_success_threshold: float = 0.90,
        degraded_success_threshold: float = 0.60,
        max_stable_error_px: float = 15.0,
    ) -> None:
        self.engine = RobustnessEnvelopeEngine(
            success_rate_threshold=stable_success_threshold,
            degraded_rate_threshold=degraded_success_threshold,
            max_degraded_error_px=max_stable_error_px,
        )

    def generate_map_data(
        self,
        param_x_name: str,
        param_x_vals: List[float],
        param_y_name: str,
        param_y_vals: List[float],
        cell_data: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        n_x, n_y = len(param_x_vals), len(param_y_vals)
        success_matrix = np.zeros((n_y, n_x), dtype=float)
        error_matrix = np.zeros((n_y, n_x), dtype=float)
        class_matrix = []

        cell_dict = {(c["param_x_val"], c["param_y_val"]): c for c in cell_data}

        for i, y_val in enumerate(param_y_vals):
            row_class = []
            for j, x_val in enumerate(param_x_vals):
                c = cell_dict.get((x_val, y_val), {})
                succ_rate = c.get("success_rate", 0.0)
                med_err = c.get("median_error", 999.0)
                cell_class = self.engine.classify_cell(succ_rate, med_err)

                success_matrix[i, j] = succ_rate
                error_matrix[i, j] = med_err
                row_class.append(cell_class)

            class_matrix.append(row_class)

        return {
            "param_x": {"name": param_x_name, "values": param_x_vals},
            "param_y": {"name": param_y_name, "values": param_y_vals},
            "success_rate_matrix": success_matrix.tolist(),
            "median_error_matrix": error_matrix.tolist(),
            "classification_matrix": class_matrix,
        }
