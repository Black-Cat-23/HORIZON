"""
Plot Tradeoffs Module
=====================
Accuracy vs. latency Pareto scatter plot rendering.
"""

from __future__ import annotations
from typing import Any, Dict, List
import matplotlib.pyplot as plt


def plot_pareto_tradeoff(points: List[Dict[str, Any]], pareto_points: List[Dict[str, Any]], output_path: str) -> None:
    if not points:
        return
    fig, ax = plt.subplots(figsize=(7, 5))
    for p in points:
        ax.scatter(p["mean_latency_ms"], p["mean_error_px"], label=p["algorithm"], s=100)

    pareto_algos = [p["algorithm"] for p in pareto_points]
    ax.set_xlabel("Processing Latency (ms)")
    ax.set_ylabel("Mean Tracking Error (pixels)")
    ax.set_title(f"Accuracy vs. Latency Pareto Frontier (Optimal: {', '.join(pareto_algos)})")
    ax.grid(True, linestyle="--", alpha=0.5)
    ax.legend()
    plt.tight_layout()
    plt.savefig(output_path, dpi=300)
    plt.close(fig)
