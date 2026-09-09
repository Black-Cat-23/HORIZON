"""
Statistical Comparison and Effect Size Engine
=============================================
Non-parametric hypothesis testing, paired bootstrap tests, effect sizes, and Benjamini-Hochberg FDR control.
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Tuple
import numpy as np


def cohens_d(x: List[float] | np.ndarray, y: List[float] | np.ndarray) -> float:
    """Compute Cohen's d effect size for two numeric samples."""
    x_arr = np.asarray(x, dtype=float)
    y_arr = np.asarray(y, dtype=float)
    n1, n2 = len(x_arr), len(y_arr)
    if n1 < 2 or n2 < 2:
        return 0.0

    var1 = np.var(x_arr, ddof=1)
    var2 = np.var(y_arr, ddof=1)
    s_pooled = math.sqrt(((n1 - 1) * var1 + (n2 - 1) * var2) / (n1 + n2 - 2))

    if s_pooled == 0.0:
        return 0.0
    return float((np.mean(x_arr) - np.mean(y_arr)) / s_pooled)


def cliffs_delta(x: List[float] | np.ndarray, y: List[float] | np.ndarray) -> float:
    """Compute Cliff's delta non-parametric effect size."""
    x_arr = np.asarray(x, dtype=float)
    y_arr = np.asarray(y, dtype=float)
    n1, n2 = len(x_arr), len(y_arr)
    if n1 == 0 or n2 == 0:
        return 0.0

    greater = 0
    less = 0
    for val_x in x_arr:
        for val_y in y_arr:
            if val_x > val_y:
                greater += 1
            elif val_x < val_y:
                less += 1

    return float((greater - less) / (n1 * n2))


def paired_bootstrap_test(
    x: List[float] | np.ndarray,
    y: List[float] | np.ndarray,
    num_samples: int = 1000,
    seed: int = 42,
) -> Dict[str, Any]:
    """Paired bootstrap test for difference in means across identical seeds."""
    x_arr = np.asarray(x, dtype=float)
    y_arr = np.asarray(y, dtype=float)
    if len(x_arr) != len(y_arr):
        raise ValueError("Paired bootstrap requires equal sample lengths.")
    n = len(x_arr)
    if n == 0:
        return {"mean_diff": 0.0, "p_value": 1.0, "ci_lower": 0.0, "ci_upper": 0.0}

    diffs = x_arr - y_arr
    mean_diff = float(np.mean(diffs))

    rng = np.random.default_rng(seed)
    boot_means = []

    for _ in range(num_samples):
        boot_idx = rng.integers(0, n, size=n)
        boot_means.append(np.mean(diffs[boot_idx]))

    boot_means = np.asarray(boot_means)
    ci_lower = float(np.percentile(boot_means, 2.5))
    ci_upper = float(np.percentile(boot_means, 97.5))

    # Two-sided p-value: proportion of bootstrap means crossing zero
    if mean_diff > 0:
        p_val = 2.0 * float(np.sum(boot_means <= 0) / num_samples)
    else:
        p_val = 2.0 * float(np.sum(boot_means >= 0) / num_samples)
    p_val = min(1.0, max(0.0, p_val))

    return {
        "mean_diff": mean_diff,
        "p_value": p_val,
        "ci_lower": ci_lower,
        "ci_upper": ci_upper,
    }


def check_normality(sample: List[float] | np.ndarray) -> Dict[str, Any]:
    """Test normality assumption using skewness and excess kurtosis."""
    arr = np.asarray(sample, dtype=float)
    n = len(arr)
    if n < 3:
        return {"is_normal": True, "skewness": 0.0, "excess_kurtosis": 0.0}

    mean = float(np.mean(arr))
    std = float(np.std(arr, ddof=1))
    if std == 0.0:
        return {"is_normal": True, "skewness": 0.0, "excess_kurtosis": 0.0}

    skewness = float(np.mean(((arr - mean) / std) ** 3))
    kurtosis = float(np.mean(((arr - mean) / std) ** 4))
    excess_kurtosis = kurtosis - 3.0

    # Non-normality threshold: |skewness| > 0.8 or |excess_kurtosis| > 1.5
    is_normal = abs(skewness) <= 0.8 and abs(excess_kurtosis) <= 1.5
    return {
        "is_normal": is_normal,
        "skewness": skewness,
        "excess_kurtosis": excess_kurtosis,
    }


def vargha_delaney_a12(x: List[float] | np.ndarray, y: List[float] | np.ndarray) -> float:
    """Compute Vargha-Delaney A12 effect size statistic."""
    x_arr = np.asarray(x, dtype=float)
    y_arr = np.asarray(y, dtype=float)
    m, n = len(x_arr), len(y_arr)
    if m == 0 or n == 0:
        return 0.5

    r1 = 0.0
    for val_x in x_arr:
        for val_y in y_arr:
            if val_x > val_y:
                r1 += 1.0
            elif val_x == val_y:
                r1 += 0.5

    return float(r1 / (m * n))


def paired_wilcoxon_test(x: List[float] | np.ndarray, y: List[float] | np.ndarray) -> Dict[str, Any]:
    """Paired Wilcoxon signed-rank test for paired samples."""
    x_arr = np.asarray(x, dtype=float)
    y_arr = np.asarray(y, dtype=float)
    if len(x_arr) != len(y_arr):
        raise ValueError("Paired Wilcoxon test requires equal sample lengths.")

    diffs = x_arr - y_arr
    nonzero_diffs = diffs[diffs != 0]
    n = len(nonzero_diffs)
    if n == 0:
        return {"w_statistic": 0.0, "p_value": 1.0, "z_score": 0.0}

    abs_diffs = np.abs(nonzero_diffs)
    ranks = np.argsort(np.argsort(abs_diffs)) + 1

    pos_mask = nonzero_diffs > 0
    w_pos = float(np.sum(ranks[pos_mask]))
    w_neg = float(np.sum(ranks[~pos_mask]))
    w_stat = min(w_pos, w_neg)

    # Asymptotic normal approximation
    mean_w = n * (n + 1) / 4.0
    var_w = n * (n + 1) * (2 * n + 1) / 24.0
    std_w = math.sqrt(var_w) if var_w > 0 else 1.0
    z_score = (w_stat - mean_w) / std_w

    # Two-sided approximate p-value using erf
    p_val = 2.0 * (0.5 * (1.0 + math.erf(z_score / math.sqrt(2.0))))
    p_val = min(1.0, max(0.0, float(p_val)))

    return {"w_statistic": w_stat, "p_value": p_val, "z_score": float(z_score)}


def benjamini_hochberg_correction(
    p_values: List[float], fdr_rate: float = 0.05
) -> List[Tuple[float, bool]]:
    """Apply Benjamini-Hochberg procedure for multiple hypothesis testing.

    Returns:
        List of (adjusted_p_value, is_significant) tuples.
    """
    m = len(p_values)
    if m == 0:
        return []

    # Sort p-values with original indices
    indexed_p = sorted(enumerate(p_values), key=lambda x: x[1])
    adjusted = [1.0] * m
    results = [False] * m

    cum_min = 1.0
    for rank_idx in range(m - 1, -1, -1):
        orig_idx, p_val = indexed_p[rank_idx]
        rank = rank_idx + 1
        adj_p = (p_val * m) / rank
        cum_min = min(cum_min, adj_p)
        cum_min = min(1.0, max(0.0, cum_min))
        adjusted[orig_idx] = cum_min

    for i in range(m):
        results[i] = adjusted[i] <= fdr_rate

    return list(zip(adjusted, results))

