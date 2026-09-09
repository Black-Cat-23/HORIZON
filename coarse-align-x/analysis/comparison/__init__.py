"""
Phase 10 — Comparison & Ablation Subpackage
============================================
Seed-matched B0/B1/B2/OURS comparisons, component ablation, latency vs accuracy trade-offs, Pareto frontiers.
"""

from analysis.comparison.b0_b1_b2_ours import BaselineComparison
from analysis.comparison.ablation import AblationAnalyzer
from analysis.comparison.tradeoffs import TradeoffAnalyzer
from analysis.comparison.pareto import ParetoFrontier
from analysis.comparison.seed_matched import SeedMatchedAnalyzer

__all__ = [
    "BaselineComparison",
    "AblationAnalyzer",
    "TradeoffAnalyzer",
    "ParetoFrontier",
    "SeedMatchedAnalyzer",
]

