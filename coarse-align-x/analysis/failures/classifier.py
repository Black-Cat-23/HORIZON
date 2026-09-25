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


class SubsystemFailureType(str, Enum):
    PERCEPTION = "perception"
    ASSOCIATION = "association"
    ESTIMATION = "estimation"
    PAT = "PAT"
    CONTROL = "control"
    COMPUTATION = "computation"
    UNKNOWN = "unknown"


class ForensicsConfidence(str, Enum):
    CONFIRMED = "CONFIRMED"
    LIKELY = "LIKELY"
    UNKNOWN = "UNKNOWN"


class FailureClassifier:
    """Categorizes trial telemetry outcomes into formal taxonomy failure modes."""

    def classify_trial(self, trial_data: Dict[str, Any]) -> FailureMode:
        status = trial_data.get("status", "")
        if status == "RUNTIME_ERROR":
            return FailureMode.RUNTIME_ERROR

        metrics = trial_data.get("metrics", {})
        mean_err = metrics.get("mean_tracking_error_px", metrics.get("mean_tracking_error", 0.0))
        lock_ret = metrics.get("lock_retention_rate", 0.0)
        proc_latency = metrics.get("mean_processing_latency_ms", metrics.get("processing_time", 0.0))
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
    """Analyzes and categorizes trial outcome statuses into formal failure taxonomies and telemetry forensics."""

    @staticmethod
    def classify_telemetry_failure(trial: Dict[str, Any]) -> Dict[str, Any]:
        """Reconstruct trial step telemetry timeline to pinpoint origin subsystem and confidence.

        Subsystems: perception, association, estimation, PAT, control, computation
        Confidence: CONFIRMED, LIKELY, UNKNOWN
        """
        import math
        metrics = trial.get("metrics", {})
        status = trial.get("status", "SUCCESS")

        if status in ("SUCCESS", "COMPLETED") and metrics.get("mean_tracking_error", 0.0) < 15.0:
            return {
                "is_failure": False,
                "subsystem": None,
                "confidence": ForensicsConfidence.CONFIRMED.value,
                "reason": "Trial completed within performance tolerances.",
            }

        # Inspect step logs or telemetry if recorded
        step_logs = trial.get("step_logs", []) or trial.get("telemetry_history", [])

        # 1. Computation failure check
        proc_time = metrics.get("processing_time", metrics.get("mean_processing_latency_ms", 0.0))
        p95_proc = metrics.get("P95_processing_time", proc_time)
        if proc_time > 33.3 or p95_proc > 50.0 or trial.get("failure_reason") == "PROCESSING_OVERRUN":
            return {
                "is_failure": True,
                "subsystem": SubsystemFailureType.COMPUTATION.value,
                "confidence": ForensicsConfidence.CONFIRMED.value if p95_proc > 50.0 else ForensicsConfidence.LIKELY.value,
                "reason": f"Processing overrun detected: mean={proc_time:.2f}ms, P95={p95_proc:.2f}ms",
            }

        # 2. Control saturation check
        gimbal_jitter = metrics.get("gimbal_jitter_rad", 0.0)
        if metrics.get("lock_retention_rate", 1.0) < 0.3 and gimbal_jitter > 0.05:
            return {
                "is_failure": True,
                "subsystem": SubsystemFailureType.CONTROL.value,
                "confidence": ForensicsConfidence.CONFIRMED.value if gimbal_jitter > 0.1 else ForensicsConfidence.LIKELY.value,
                "reason": f"Controller saturation / actuator jitter overshoot: jitter={gimbal_jitter:.4f} rad",
            }

        # Reconstruct step timeline if available
        if step_logs:
            for step in step_logs:
                det_conf = step.get("detection_confidence", 1.0)
                inn_cov = step.get("innovation_covariance", 0.0)
                assoc_dist = step.get("association_cost", 0.0)
                pat_state = step.get("pat_state", "FINE_TRACKING")

                if det_conf < 0.2:
                    return {
                        "is_failure": True,
                        "subsystem": SubsystemFailureType.PERCEPTION.value,
                        "confidence": ForensicsConfidence.CONFIRMED.value,
                        "reason": f"Perception detector dropout (confidence={det_conf:.2f})",
                    }
                if assoc_dist > 100.0:
                    return {
                        "is_failure": True,
                        "subsystem": SubsystemFailureType.ASSOCIATION.value,
                        "confidence": ForensicsConfidence.CONFIRMED.value,
                        "reason": f"Data association gating failure (cost={assoc_dist:.1f})",
                    }
                if inn_cov > 500.0 or math.isnan(inn_cov):
                    return {
                        "is_failure": True,
                        "subsystem": SubsystemFailureType.ESTIMATION.value,
                        "confidence": ForensicsConfidence.CONFIRMED.value,
                        "reason": f"Kalman filter innovation covariance blowup ({inn_cov})",
                    }
                if pat_state == "SEARCH":
                    return {
                        "is_failure": True,
                        "subsystem": SubsystemFailureType.PAT.value,
                        "confidence": ForensicsConfidence.LIKELY.value,
                        "reason": "PAT state machine demoted to SEARCH state.",
                    }

        # High-level fallbacks if step logs not recorded
        lock_rate = metrics.get("lock_retention_rate", 1.0)
        mean_err = metrics.get("mean_tracking_error", 0.0)

        if lock_rate < 0.5:
            return {
                "is_failure": True,
                "subsystem": SubsystemFailureType.PAT.value,
                "confidence": ForensicsConfidence.LIKELY.value,
                "reason": f"PAT lock break (lock retention rate = {lock_rate*100:.1f}%)",
            }
        elif mean_err > 25.0:
            return {
                "is_failure": True,
                "subsystem": SubsystemFailureType.ESTIMATION.value,
                "confidence": ForensicsConfidence.LIKELY.value,
                "reason": f"Excessive estimation drift (mean error = {mean_err:.2f}px)",
            }

        return {
            "is_failure": True,
            "subsystem": SubsystemFailureType.UNKNOWN.value,
            "confidence": ForensicsConfidence.UNKNOWN.value,
            "reason": "Unspecified degrade/failure event without definitive telemetry signature.",
        }

    @classmethod
    def analyze_trial_group(cls, trials: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Compute failure breakdown matrix and telemetry forensics across a trial group."""
        from benchmark.failure import FailureCategory
        total_trials = len(trials)
        if total_trials == 0:
            return {
                "total_trials": 0,
                "failure_counts": {},
                "failure_percentages": {},
                "forensics_summary": {},
            }

        counts: Dict[str, int] = {cat.value: 0 for cat in FailureCategory}
        subsystem_counts: Dict[str, int] = {sub.value: 0 for sub in SubsystemFailureType}
        confidence_counts: Dict[str, int] = {conf.value: 0 for conf in ForensicsConfidence}

        forensics_details = []

        for t in trials:
            status = t.get("status", FailureCategory.SUCCESS.value)
            counts[status] = counts.get(status, 0) + 1

            forensic = cls.classify_telemetry_failure(t)
            if forensic["is_failure"]:
                sub = forensic["subsystem"]
                conf = forensic["confidence"]
                subsystem_counts[sub] = subsystem_counts.get(sub, 0) + 1
                confidence_counts[conf] = confidence_counts.get(conf, 0) + 1

                forensics_details.append({
                    "trial_id": t.get("trial_id"),
                    "seed": t.get("seed"),
                    "scenario_id": t.get("scenario_id"),
                    "subsystem": sub,
                    "confidence": conf,
                    "reason": forensic["reason"],
                })

        percentages = {cat: (cnt / total_trials) * 100.0 for cat, cnt in counts.items()}

        return {
            "total_trials": total_trials,
            "failure_counts": counts,
            "failure_percentages": percentages,
            "forensics_summary": {
                "subsystem_counts": subsystem_counts,
                "confidence_counts": confidence_counts,
            },
            "forensics_details": forensics_details,
        }


