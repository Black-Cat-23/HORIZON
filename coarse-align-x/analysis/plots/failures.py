"""
Plot Failures Module
====================
Scientific Pareto ranking plots for failure modes.
"""

from __future__ import annotations
from typing import List, Tuple
import matplotlib.pyplot as plt


def plot_failure_pareto(pareto_data: List[Tuple[str, int, float]], output_path: str) -> None:
    if not pareto_data:
        return
    fig, ax1 = plt.subplots(figsize=(8, 5))
    modes = [p[0] for p in pareto_data]
    counts = [p[1] for p in pareto_data]
    cum_pct = [p[2] for p in pareto_data]

    ax1.bar(modes, counts, color="#ff3b30", alpha=0.8)
    ax1.set_ylabel("Failure Frequency", color="#ff3b30")

    ax2 = ax1.twinx()
    ax2.plot(modes, cum_pct, color="#007aff", marker="o", linewidth=2)
    ax2.set_ylabel("Cumulative Percentage (%)", color="#007aff")
    ax2.set_ylim(0, 105)

    plt.title("Failure Mode Pareto Ranking")
    plt.tight_layout()
    plt.savefig(output_path, dpi=300)
    plt.close(fig)
