"""
Failure Frequency Module
========================
Calculates failure mode counts and percentages across benchmark algorithms.
"""

from __future__ import annotations
from typing import Any, Dict, List
from collections import Counter
from analysis.failures.classifier import FailureClassifier, FailureMode


class FailureFrequency:
    """Computes failure frequency statistics."""

    def compute_frequencies(self, trials: List[Dict[str, Any]]) -> Dict[str, Dict[str, int]]:
        classifier = FailureClassifier()
        counts: Dict[str, Counter] = {}

        for trial in trials:
            algo = trial.get("algorithm", "UNKNOWN")
            if algo not in counts:
                counts[algo] = Counter()
            mode = classifier.classify_trial(trial)
            counts[algo][mode.value] += 1

        return {algo: dict(c) for algo, c in counts.items()}
