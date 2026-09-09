"""
Duplicate Detector Module
=========================
Detects duplicate trial identifiers or identical seed/scenario combinations.
"""

from __future__ import annotations
from typing import Any, Dict, List, Set, Tuple


class DuplicateDetector:
    """Audits trial collections for duplicate entries."""

    def find_duplicates(self, trials: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        seen_keys: Set[Tuple[str, int, str]] = set()
        duplicates: List[Dict[str, Any]] = []

        for trial in trials:
            algo = trial.get("algorithm", "")
            seed = trial.get("seed", 0)
            scen = trial.get("scenario_id", "")
            key = (algo, seed, scen)
            if key in seen_keys:
                duplicates.append(trial)
            else:
                seen_keys.add(key)
        return duplicates
