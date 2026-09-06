"""
Ablation Analyzer Module
========================
Evaluates component ablation steps A through E and feature toggle contributions.
"""

from __future__ import annotations
from typing import Any, Dict, List


class AblationAnalyzer:
    """Evaluates component and feature ablations."""

    ABLATION_STEPS = {
        "A": "Classical (Thresholding)",
        "B": "Neural (YOLOv8 Raw)",
        "C": "Basic Fusion",
        "D": "Fusion + Optical Gaussian CoG Refinement",
        "E": "Full Hybrid System (OURS)",
    }

    def evaluate_ablation(self, ablation_trials: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Dict[str, float]]:
        summary = {}
        for step, name in self.ABLATION_STEPS.items():
            trials = ablation_trials.get(step, [])
            if not trials:
                summary[step] = {"name": name, "mean_error_px": 0.0, "lock_retention": 0.0, "latency_ms": 0.0}
                continue
            errs = [t["metrics"]["mean_tracking_error_px"] for t in trials if "metrics" in t]
            rets = [t["metrics"]["lock_retention_rate"] for t in trials if "metrics" in t]
            lats = [t["metrics"]["mean_processing_latency_ms"] for t in trials if "metrics" in t]
            summary[step] = {
                "name": name,
                "mean_error_px": float(sum(errs) / len(errs)) if errs else 0.0,
                "lock_retention": float(sum(rets) / len(rets)) if rets else 0.0,
                "latency_ms": float(sum(lats) / len(lats)) if lats else 0.0,
            }
        return summary
