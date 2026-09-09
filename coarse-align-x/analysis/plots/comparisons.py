"""
Plot Comparisons Module
=======================
Algorithm comparison bar charts across metrics.
"""

from __future__ import annotations
from typing import Dict, List
import matplotlib.pyplot as plt


def plot_algorithm_comparison(results: Dict[str, float], metric_name: str, output_path: str) -> None:
    if not results:
        return
    fig, ax = plt.subplots(figsize=(7, 5))
    algos = list(results.keys())
    vals = list(results.values())
    ax.bar(algos, vals, color="#34c759", alpha=0.85)
    ax.set_ylabel(metric_name)
    ax.set_title(f"Algorithm Comparison — {metric_name}")
    ax.grid(True, linestyle="--", alpha=0.5, axis="y")
    plt.tight_layout()
    plt.savefig(output_path, dpi=300)
    plt.close(fig)
