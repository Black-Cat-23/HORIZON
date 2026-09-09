"""
Paired Tests Module
===================
Wilcoxon signed-rank test and paired bootstrap difference tests.
"""

from __future__ import annotations
from typing import Sequence, Tuple
import numpy as np


class PairedTests:
    """Executes paired hypothesis tests for seed-matched comparative groups."""

    @staticmethod
    def paired_bootstrap_test(
        a: Sequence[float],
        b: Sequence[float],
        num_samples: int = 1000,
        seed: int = 42,
    ) -> float:
        if len(a) != len(b) or len(a) == 0:
            return 1.0
        diff = np.array(a) - np.array(b)
        rng = np.random.default_rng(seed)

        count = 0
        n = len(diff)
        for _ in range(num_samples):
            resample = rng.choice(diff, size=n, replace=True)
            if np.mean(resample) <= 0:
                count += 1
        return float(count / num_samples)
