"""
Test Missing Data & Quality Auditor
"""
import math
from analysis.validation.data_quality import DataQualityAuditor

def test_data_quality():
    metrics = {"valid": 1.0, "nan_val": math.nan, "inf_val": math.inf}
    issues = DataQualityAuditor.check_data_quality(metrics)
    assert len(issues) == 2
