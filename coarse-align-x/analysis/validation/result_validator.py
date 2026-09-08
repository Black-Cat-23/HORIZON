"""
Result Validator Module
=======================
Defines explicit trial validity states and auditing rules.
"""

from __future__ import annotations
from enum import Enum
import math
from typing import Any, Dict, List, Optional, Tuple


class TrialValidityState(str, Enum):
    VALID = "VALID"
    FAILED_RUNTIME = "FAILED_RUNTIME"
    INVALID_DATA = "INVALID_DATA"
    INCOMPLETE = "INCOMPLETE"
    EXCLUDED_WITH_REASON = "EXCLUDED_WITH_REASON"


REQUIRED_FIELDS = [
    "experiment_id",
    "trial_id",
    "algorithm",
    "seed",
    "scenario_id",
    "status",
    "metrics",
    "resolved_configuration",
]

REQUIRED_METRICS = [
    "simulation_duration",
    "average_fps",
    "processing_time",
    "P95_processing_time",
    "mean_tracking_error",
    "median_tracking_error",
    "RMSE_tracking_error",
    "P95_tracking_error",
    "P99_tracking_error",
    "lock_retention_rate",
]


class ResultValidator:
    """Audits trial JSON output for schema compliance and validity state."""

    REQUIRED_FIELDS = REQUIRED_FIELDS

    def validate_trial(self, trial_data: Dict[str, Any]) -> tuple[TrialValidityState, Optional[str]]:
        for field in self.REQUIRED_FIELDS:
            if field not in trial_data:
                return TrialValidityState.INVALID_DATA, f"Missing required field: '{field}'"

        status = trial_data.get("status")
        if status == "RUNTIME_ERROR":
            return TrialValidityState.FAILED_RUNTIME, "Trial terminated with runtime exception"
        if status == "INCOMPLETE":
            return TrialValidityState.INCOMPLETE, "Trial output is incomplete"

        metrics = trial_data.get("metrics")
        if not isinstance(metrics, dict):
            return TrialValidityState.INVALID_DATA, "'metrics' field must be a dictionary"

        return TrialValidityState.VALID, None


def validate_trial_result(data: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """Validate a single trial result dictionary."""
    issues: List[str] = []

    for req in REQUIRED_FIELDS:
        if req not in data:
            issues.append(f"Missing required field: '{req}'")

    if issues:
        return False, issues

    metrics = data.get("metrics", {})
    if not isinstance(metrics, dict):
        issues.append("Field 'metrics' is not a dictionary.")
        return False, issues

    for m_key in REQUIRED_METRICS:
        if m_key not in metrics and (m_key + "_px") not in metrics:
            issues.append(f"Missing metric: '{m_key}'")
        else:
            val = metrics.get(m_key, metrics.get(m_key + "_px"))
            if val is not None and isinstance(val, (int, float)):
                if math.isnan(val) or math.isinf(val):
                    issues.append(f"Non-finite value for metric '{m_key}': {val}")

    is_valid = len(issues) == 0
    return is_valid, issues


def audit_trials_directory(trials_dir: Any) -> Dict[str, Any]:
    """Scan and audit all trial result files in a directory hierarchy."""
    import json
    from pathlib import Path
    path = Path(trials_dir)
    if not path.exists():
        return {"total_files": 0, "valid_count": 0, "corrupted_count": 0, "valid_trials": [], "issues": []}

    trial_files = [f for f in path.glob("**/*.json") if f.name != "checkpoint.json"]
    valid_trials: List[Dict[str, Any]] = []
    audit_report: List[Dict[str, Any]] = []

    for f_path in trial_files:
        try:
            with open(f_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            is_valid, issues = validate_trial_result(data)
            if is_valid:
                valid_trials.append(data)
            else:
                audit_report.append({"file": str(f_path), "issues": issues})
        except Exception as e:
            audit_report.append({"file": str(f_path), "issues": [f"JSON Parse Exception: {str(e)}"]})

    return {
        "total_files": len(trial_files),
        "valid_count": len(valid_trials),
        "corrupted_count": len(audit_report),
        "valid_trials": valid_trials,
        "audit_issues": audit_report,
    }
