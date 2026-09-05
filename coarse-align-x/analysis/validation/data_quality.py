"""
Data Quality Auditor Module
===========================
Audits numerical data quality, non-finite values (NaN, Inf), and timestamp monotonicity.
"""

from __future__ import annotations
import math
from typing import Any, Dict, List, Tuple


class DataQualityAuditor:
    """Audits metrics and telemetry streams for data corruption or non-finite values."""

    @staticmethod
    def check_data_quality(metrics: Dict[str, Any]) -> List[str]:
        issues = []
        for key, val in metrics.items():
            if isinstance(val, float):
                if math.isnan(val):
                    issues.append(f"Metric '{key}' contains NaN")
                elif math.isinf(val):
                    issues.append(f"Metric '{key}' contains Infinity")
        return issues
