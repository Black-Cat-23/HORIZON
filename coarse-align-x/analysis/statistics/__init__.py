"""
Phase 10 — Statistics Subpackage
================================
Deterministic bootstrap, Wilson Score 95% CIs, Wilcoxon signed-rank paired tests, Cohen's d / Cliff's delta, Benjamini-Hochberg FDR control.
"""

from analysis.statistics.bootstrap import DeterministicBootstrap
from analysis.statistics.confidence_intervals import ConfidenceIntervals
from analysis.statistics.paired_tests import PairedTests
from analysis.statistics.effect_size import EffectSize
from analysis.statistics.correction import MultipleComparisonCorrection
from analysis.statistics.hypothesis import HypothesisTestingEngine

__all__ = [
    "DeterministicBootstrap",
    "ConfidenceIntervals",
    "PairedTests",
    "EffectSize",
    "MultipleComparisonCorrection",
    "HypothesisTestingEngine",
]
