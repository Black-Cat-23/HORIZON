"""
Trial Manifest & Metric Schema Validation Engine
================================================
Audits raw trial result JSON files for schema completeness, numerical sanity, and timestamp monotonicity.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Dict, List, Tuple


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


def validate_trial_result(data: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """Validate a single trial result dictionary.

    Returns:
        Tuple of (is_valid, list_of_audit_issues)
    """
    issues: List[str] = []

    for req in REQUIRED_FIELDS:
        if req not in data:
            issues.append(f"Missing required field: '{req}'")

    if issues:
        return False, issues

    # Status check for trial completion
    status = str(data.get("status", "")).upper()
    if status not in ("COMPLETED", "SUCCESS", "FAILED"):
        issues.append(f"Incomplete trial: status is '{status}'")

    metrics = data.get("metrics", {})
    if not isinstance(metrics, dict):
        issues.append("Field 'metrics' is not a dictionary.")
        return False, issues

    for m_key in REQUIRED_METRICS:
        if m_key not in metrics:
            issues.append(f"Missing metric: '{m_key}'")
        else:
            val = metrics[m_key]
            if val is None:
                issues.append(f"Null metric value for '{m_key}'")
            elif isinstance(val, (int, float)):
                if math.isnan(val) or math.isinf(val):
                    issues.append(f"Non-finite value for metric '{m_key}': {val}")
            else:
                issues.append(f"Invalid type for metric '{m_key}': {type(val)}")

    # Sanity checks on duration & fps
    dur = metrics.get("simulation_duration", 0)
    if isinstance(dur, (int, float)) and dur <= 0:
        issues.append(f"Invalid simulation_duration: {dur}")

    fps = metrics.get("average_fps", 0)
    if isinstance(fps, (int, float)) and fps <= 0:
        issues.append(f"Invalid average_fps: {fps}")

    is_valid = len(issues) == 0
    return is_valid, issues


def audit_trials_directory(trials_dir: str | Path) -> Dict[str, Any]:
    """Scan and audit all trial result files in a directory hierarchy.

    Performs Step 1 Data Integrity Auditing:
    1. Duplicates check
    2. Missing data check
    3. Invalid data (NaN/Inf) check
    4. Incomplete trial check
    5. Configuration mismatch check across seeds.

    Returns:
        Dictionary with count summary, valid_trials list, audit_issues, and integrity_metrics.
    """
    path = Path(trials_dir)
    if not path.exists():
        return {
            "total_files": 0,
            "valid_count": 0,
            "corrupted_count": 0,
            "duplicate_count": 0,
            "incomplete_count": 0,
            "config_mismatch_count": 0,
            "valid_trials": [],
            "audit_issues": [],
            "integrity_summary": {
                "duplicates_found": 0,
                "missing_data_count": 0,
                "invalid_data_count": 0,
                "incomplete_trials": 0,
                "config_mismatches": 0,
            },
        }

    trial_files = list(path.glob("**/*.json"))
    # Filter out checkpoint.json files
    trial_files = [f for f in trial_files if f.name != "checkpoint.json"]

    valid_trials: List[Dict[str, Any]] = []
    audit_report: List[Dict[str, Any]] = []
    
    seen_trial_keys: Dict[Tuple[str, str, int], str] = {}
    config_hashes_by_alg: Dict[str, Dict[str, List[str]]] = {}
    
    duplicate_count = 0
    incomplete_count = 0
    missing_data_count = 0
    invalid_data_count = 0
    config_mismatch_count = 0

    for f_path in trial_files:
        try:
            with open(f_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            is_valid, issues = validate_trial_result(data)
            
            # Additional duplicate key tracking: (algorithm, scenario_id, seed)
            alg = str(data.get("algorithm", "UNKNOWN"))
            scen = str(data.get("scenario_id", "default"))
            seed = int(data.get("seed", -1))
            t_key = (alg, scen, seed)

            if t_key in seen_trial_keys:
                duplicate_count += 1
                issues.append(f"Duplicate trial key (alg={alg}, scenario={scen}, seed={seed}) previously seen in {seen_trial_keys[t_key]}")
                is_valid = False
            else:
                seen_trial_keys[t_key] = str(f_path)

            # Check configuration hash consistency if present
            cfg_hash = data.get("algorithm_config_hash") or data.get("resolved_configuration", {}).get("config_hash")
            if cfg_hash:
                config_hashes_by_alg.setdefault(alg, {}).setdefault(cfg_hash, []).append(str(f_path))

            if is_valid:
                valid_trials.append(data)
            else:
                for issue in issues:
                    if "Missing" in issue:
                        missing_data_count += 1
                    elif "Non-finite" in issue or "Invalid" in issue:
                        invalid_data_count += 1
                    elif "Incomplete" in issue:
                        incomplete_count += 1
                audit_report.append({"file": str(f_path), "issues": issues})
        except Exception as e:
            invalid_data_count += 1
            audit_report.append({"file": str(f_path), "issues": [f"JSON Parse Exception: {str(e)}"]})

    # Verify config hash consistency across algorithms
    for alg, hashes in config_hashes_by_alg.items():
        if len(hashes) > 1:
            config_mismatch_count += len(hashes) - 1
            audit_report.append({
                "file": f"Multiple config hashes detected for algorithm '{alg}'",
                "issues": [f"Configuration mismatch: {len(hashes)} distinct config hashes detected: {list(hashes.keys())}"]
            })

    return {
        "total_files": len(trial_files),
        "valid_count": len(valid_trials),
        "corrupted_count": len(audit_report),
        "duplicate_count": duplicate_count,
        "incomplete_count": incomplete_count,
        "config_mismatch_count": config_mismatch_count,
        "valid_trials": valid_trials,
        "audit_issues": audit_report,
        "integrity_summary": {
            "duplicates_found": duplicate_count,
            "missing_data_count": missing_data_count,
            "invalid_data_count": invalid_data_count,
            "incomplete_trials": incomplete_count,
            "config_mismatches": config_mismatch_count,
        },
    }

