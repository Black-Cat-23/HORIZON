"""
Deterministic Bootstrap Module
==============================
Deterministic non-parametric bootstrap resampling engine.
"""

from __future__ import annotations
from typing import Sequence, Tuple
import numpy as np


class DeterministicBootstrap:
    """Performs deterministic non-parametric bootstrap resampling for continuous metrics."""

    @staticmethod
    def bootstrap_ci(
        data: Sequence[float],
        num_samples: int = 1000,
        confidence_level: float = 0.95,
        seed: int = 42,
    ) -> Tuple[float, float]:
        if len(data) == 0:
            return 0.0, 0.0
        arr = np.array(data, dtype=np.float64)
        rng = np.random.default_rng(seed)

        means = []
        n = len(arr)
        for _ in range(num_samples):
            resample = rng.choice(arr, size=n, replace=True)
            means.append(np.mean(resample))

        alpha = (1.0 - confidence_level) / 2.0
        low = float(np.percentile(means, 100.0 * alpha))
        high = float(np.percentile(means, 100.0 * (1.0 - alpha)))
        return low, high
