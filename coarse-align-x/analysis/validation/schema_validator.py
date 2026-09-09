"""
Schema Validator Module
=======================
Strict JSON schema structural auditor.
"""

from __future__ import annotations
from typing import Any, Dict, List


class SchemaValidator:
    """Validates structural metadata schemas for benchmark trial results."""

    @staticmethod
    def validate_schema(data: Dict[str, Any]) -> List[str]:
        errors = []
        if not isinstance(data.get("experiment_id"), str):
            errors.append("experiment_id must be a string")
        if not isinstance(data.get("trial_id"), str):
            errors.append("trial_id must be a string")
        if not isinstance(data.get("algorithm"), str):
            errors.append("algorithm must be a string")
        if not isinstance(data.get("seed"), int):
            errors.append("seed must be an integer")
        if not isinstance(data.get("metrics"), dict):
            errors.append("metrics must be a dict")
        return errors
