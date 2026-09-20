"""
IMM Telemetry and Diagnostics.
HORIZON Phase 6
"""

from typing import Dict, Any
import numpy as np


class IMMDiagnostics:
    """
    Diagnostics container for IMM filter model probabilities and mode switches.
    """

    def __init__(self):
        self.dominant_model = "CV"

    def format_telemetry(self, model_probabilities: np.ndarray) -> Dict[str, Any]:
        models = ["CV", "CA", "MANOEUVRE"]
        idx = int(np.argmax(model_probabilities))
        self.dominant_model = models[idx]

        return {
            "imm_dominant_model": self.dominant_model,
            "imm_prob_cv": float(model_probabilities[0]),
            "imm_prob_ca": float(model_probabilities[1]),
            "imm_prob_manoeuvre": float(model_probabilities[2]),
        }
