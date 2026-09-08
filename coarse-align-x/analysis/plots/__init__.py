"""
Phase 10 — Scientific Plotting Subpackage
==========================================
Scientific matplotlib plotting modules for distributions, robustness, failures, comparisons, and trade-offs.
"""

from analysis.plots.distributions import plot_ecdf
from analysis.plots.robustness import plot_robustness_heatmap
from analysis.plots.failures import plot_failure_pareto
from analysis.plots.comparisons import plot_algorithm_comparison
from analysis.plots.tradeoffs import plot_pareto_tradeoff

__all__ = [
    "plot_ecdf",
    "plot_robustness_heatmap",
    "plot_failure_pareto",
    "plot_algorithm_comparison",
    "plot_pareto_tradeoff",
]
