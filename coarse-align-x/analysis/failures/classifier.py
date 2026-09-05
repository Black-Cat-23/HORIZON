"""
Failure Classifier Module
==========================
Categorizes trial outputs into 9 formal failure mode taxonomies.
"""

from __future__ import annotations
from enum import Enum
from typing import Any, Dict


class FailureMode(str, Enum):
    SUCCESS = "SUCCESS"
    NO_ACQUISITION = "NO_ACQUISITION"
    FALSE_DETECTION = "FALSE_DETECTION"
    FALSE_LOCK = "FALSE_LOCK"
    TRACK_LOSS = "TRACK_LOSS"
    REACQUISITION_TIMEOUT = "REACQUISITION_TIMEOUT"
    EXCESSIVE_ERROR = "EXCESSIVE_ERROR"
    CONTROLLER_SATURATION = "CONTROLLER_SATURATION"
    PROCESSING_OVERRUN = "PROCESSING_OVERRUN"
    RUNTIME_ERROR = "RUNTIME_ERROR"


class FailureClassifier:
    """Categorizes trial telemetry outcomes into formal taxonomy failure modes."""

    def classify_trial(self, trial_data: Dict[str, Any]) -> FailureMode:
        status = trial_data.get("status", "")
        if status == "RUNTIME_ERROR":
            return FailureMode.RUNTIME_ERROR

        metrics = trial_data.get("metrics", {})
        mean_err = metrics.get("mean_tracking_error_px", 0.0)
        lock_ret = metrics.get("lock_retention_rate", 0.0)
        proc_latency = metrics.get("mean_processing_latency_ms", 0.0)
        sat_rate = metrics.get("controller_saturation_rate", 0.0)

        if proc_latency > 50.0:
            return FailureMode.PROCESSING_OVERRUN
        if sat_rate > 0.20:
            return FailureMode.CONTROLLER_SATURATION
        if mean_err > 50.0:
            return FailureMode.EXCESSIVE_ERROR
        if lock_ret < 0.10:
            return FailureMode.TRACK_LOSS
        if lock_ret == 0.0:
            return FailureMode.NO_ACQUISITION

        return FailureMode.SUCCESS


class FailureAnalyzer:
    """Analyzes and categorizes trial outcome statuses into formal failure taxonomies."""

    @staticmethod
    def analyze_trial_group(trials: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Compute failure breakdown matrix across a list of trial results."""
        total_trials = len(trials)
        if total_trials == 0:
            return {"total_trials": 0, "failure_counts": {}, "failure_percentages": {}}

        counts: Dict[str, int] = {}
        for t in trials:
            status = t.get("status")
            if status:
                mode = str(status)
            else:
                classifier = FailureClassifier()
                mode = classifier.classify_trial(t).value
            counts[mode] = counts.get(mode, 0) + 1

        percentages = {mode: (cnt / total_trials) * 100.0 for mode, cnt in counts.items()}

        return {
            "total_trials": total_trials,
            "failure_counts": counts,
            "failure_percentages": percentages,
        }

