"""
Sensitivity Analyzer Module
============================
Continuous disturbance parameter sensitivity curves.
"""

from __future__ import annotations
from typing import Any, Dict, List, Tuple


class SensitivityAnalyzer:
    """Computes disturbance parameter degradation curves across continuous parameter ranges."""

    @staticmethod
    def compute_sensitivity_curve(
        parameter_name: str,
        parameter_values: List[float],
        metrics: List[float],
    ) -> List[Tuple[float, float]]:
        if len(parameter_values) != len(metrics):
            return []
        return sorted(zip(parameter_values, metrics), key=lambda x: x[0])
