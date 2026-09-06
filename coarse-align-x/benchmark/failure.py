"""
Failure Classification Engine
=============================
Taxonomy and automatic classification of trial outcome status and failure reasons.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, Optional


class FailureCategory(str, Enum):
    SUCCESS = "SUCCESS"
    NO_ACQUISITION = "NO_ACQUISITION"
    TRACK_LOSS = "TRACK_LOSS"
    REACQUISITION_TIMEOUT = "REACQUISITION_TIMEOUT"
    FALSE_LOCK = "FALSE_LOCK"
    EXCESSIVE_ERROR = "EXCESSIVE_ERROR"
    CONTROLLER_SATURATION = "CONTROLLER_SATURATION"
    PROCESSING_OVERRUN = "PROCESSING_OVERRUN"
    INVALID_OUTPUT = "INVALID_OUTPUT"
    RUNTIME_ERROR = "RUNTIME_ERROR"


class FailureClassifier:
    """Classifies trial telemetry and metrics into standard failure categories."""

    def __init__(
        self,
        max_mean_error_px: float = 50.0,
        max_saturation_ratio: float = 0.20,
        max_frame_processing_time_ms: float = 50.0,
        min_lock_retention_rate: float = 0.50,
    ) -> None:
        self.max_mean_error_px = max_mean_error_px
        self.max_saturation_ratio = max_saturation_ratio
        self.max_frame_processing_time_ms = max_frame_processing_time_ms
        self.min_lock_retention_rate = min_lock_retention_rate

    def classify_trial(
        self, metrics: Dict[str, Any], exception: Optional[Exception] = None
    ) -> FailureCategory:
        """Evaluate metrics and optional exception to return a FailureCategory."""
        if exception is not None:
            return FailureCategory.RUNTIME_ERROR

        # 1. No acquisition
        if metrics.get("acquisition_time") is None:
            return FailureCategory.NO_ACQUISITION

        # 2. Track loss without recovery
        if metrics.get("failed_reacquisition_count", 0) > 0 and metrics.get("lock_retention_rate", 0.0) < self.min_lock_retention_rate:
            return FailureCategory.TRACK_LOSS

        # 3. Excessive tracking error
        if metrics.get("mean_tracking_error", 0.0) > self.max_mean_error_px:
            return FailureCategory.EXCESSIVE_ERROR

        # 4. Controller saturation
        total_frames = int(metrics.get("simulation_duration", 10.0) * 60.0)
        sat_count = metrics.get("controller_saturation_count", 0)
        if total_frames > 0 and (sat_count / total_frames) > self.max_saturation_ratio:
            return FailureCategory.CONTROLLER_SATURATION

        # 5. Processing overrun
        if metrics.get("P95_processing_time", 0.0) > self.max_frame_processing_time_ms:
            return FailureCategory.PROCESSING_OVERRUN

        # Default success
        return FailureCategory.SUCCESS
