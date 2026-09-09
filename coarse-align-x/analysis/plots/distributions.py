"""
Plot Distributions Module
=========================
Scientific plotting for empirical cumulative distribution functions (eCDF).
"""

from __future__ import annotations
from typing import Dict, List, Sequence
import matplotlib.pyplot as plt
import numpy as np


def plot_ecdf(distributions: Dict[str, Sequence[float]], output_path: str) -> None:
    fig, ax = plt.subplots(figsize=(8, 5))
    for name, data in distributions.items():
        if not data:
            continue
        sorted_vals = np.sort(data)
        y = np.arange(1, len(sorted_vals) + 1) / len(sorted_vals)
        ax.plot(sorted_vals, y, label=name, linewidth=2)

    ax.set_xlabel("Tracking Error (pixels)")
    ax.set_ylabel("Empirical CDF")
    ax.set_title("Tracking Error Distribution (eCDF)")
    ax.grid(True, linestyle="--", alpha=0.5)
    ax.legend()
    plt.tight_layout()
    plt.savefig(output_path, dpi=300)
    plt.close(fig)
