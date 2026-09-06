"""
Phase 10 — Validation Subpackage
================================
Validates trial schemas, data quality, duplicate trials, and validity state tagging.
"""

from analysis.validation.result_validator import (
    ResultValidator,
    TrialValidityState,
    validate_trial_result,
    audit_trials_directory,
)
from analysis.validation.schema_validator import SchemaValidator
from analysis.validation.duplicate_detector import DuplicateDetector
from analysis.validation.data_quality import DataQualityAuditor

__all__ = [
    "ResultValidator",
    "TrialValidityState",
    "validate_trial_result",
    "audit_trials_directory",
    "SchemaValidator",
    "DuplicateDetector",
    "DataQualityAuditor",
]
