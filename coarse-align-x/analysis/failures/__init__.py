"""
Phase 10 — Failure Intelligence Subpackage
===========================================
Failure classification taxonomy, frequency counters, timeline reconstruction, Pareto ranking.
"""

from analysis.failures.classifier import FailureClassifier, FailureMode, FailureAnalyzer
from analysis.failures.frequency import FailureFrequency
from analysis.failures.timeline import FailureTimeline
from analysis.failures.pareto import FailurePareto

__all__ = [
    "FailureClassifier",
    "FailureMode",
    "FailureFrequency",
    "FailureTimeline",
    "FailurePareto",
    "FailureAnalyzer",
]
