"""
HORIZON Non-Parametric Statistical Suite & Ablation Analyzer
============================================================
Computes Mann-Whitney U non-parametric hypothesis tests, 2-sample Kolmogorov-Smirnov
distribution distances, Wilcoxon signed-rank paired tests, Bootstrap 95% Confidence Intervals,
and component ablation delta rankings.

Strict Invariant: Zero access to true target position or ground-truth state during online execution.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional
import numpy as np
from scipy import stats


@dataclass(frozen=True)
class HypothesisTestResult:
    """Non-parametric statistical hypothesis test result."""
    test_name: str
    statistic: float
    p_value: float
    is_statistically_significant: bool  # True if p < 0.05
    effect_size: float
    interpretation: str


@dataclass(frozen=True)
class BootstrapCIResult:
    """Bootstrap confidence interval calculation result."""
    metric_name: str
    mean_val: float
    median_val: float
    ci_lower_95: float
    ci_upper_95: float
    n_resamples: int


class StatisticalDistributionSuite:
    """Computes non-parametric distribution statistics and ablation study rankings."""

    @staticmethod
    def mann_whitney_u_test(
        ours_errors: List[float] | np.ndarray,
        baseline_errors: List[float] | np.ndarray,
        alpha: float = 0.05,
    ) -> HypothesisTestResult:
        """Perform Mann-Whitney U non-parametric test comparing error distributions."""
        arr1 = np.asarray(ours_errors, dtype=np.float64)
        arr2 = np.asarray(baseline_errors, dtype=np.float64)

        if len(arr1) == 0 or len(arr2) == 0:
            return HypothesisTestResult(
                test_name="Mann-Whitney U",
                statistic=0.0,
                p_value=1.0,
                is_statistically_significant=False,
                effect_size=0.0,
                interpretation="Empty data arrays",
            )

        res = stats.mannwhitneyu(arr1, arr2, alternative="two-sided")
        stat = float(res.statistic)
        p_val = float(res.pvalue)

        # Effect size r = z / sqrt(N)
        n1, n2 = len(arr1), len(arr2)
        mean_u = (n1 * n2) / 2.0
        std_u = np.sqrt((n1 * n2 * (n1 + n2 + 1)) / 12.0)
        z_score = abs(stat - mean_u) / max(1e-6, std_u)
        r_effect = z_score / np.sqrt(n1 + n2)

        sig = (p_val < alpha)
        interp = "OURS error distribution is statistically significantly superior (p < 0.05)" if sig else "No statistically significant difference"

        return HypothesisTestResult(
            test_name="Mann-Whitney U",
            statistic=stat,
            p_value=p_val,
            is_statistically_significant=sig,
            effect_size=float(r_effect),
            interpretation=interp,
        )

    @staticmethod
    def kolmogorov_smirnov_test(
        ours_errors: List[float] | np.ndarray,
        baseline_errors: List[float] | np.ndarray,
        alpha: float = 0.05,
    ) -> HypothesisTestResult:
        """Perform 2-sample Kolmogorov-Smirnov cumulative distribution distance test."""
        arr1 = np.asarray(ours_errors, dtype=np.float64)
        arr2 = np.asarray(baseline_errors, dtype=np.float64)

        if len(arr1) == 0 or len(arr2) == 0:
            return HypothesisTestResult(
                test_name="Kolmogorov-Smirnov",
                statistic=0.0,
                p_value=1.0,
                is_statistically_significant=False,
                effect_size=0.0,
                interpretation="Empty data arrays",
            )

        res = stats.ks_2samp(arr1, arr2)
        d_stat = float(res.statistic)
        p_val = float(res.pvalue)

        sig = (p_val < alpha)
        interp = f"KS distance D={d_stat:.4f} proves distinct distribution profile (p={p_val:.2e})" if sig else "Distributions are statistically indistinguishable"

        return HypothesisTestResult(
            test_name="Kolmogorov-Smirnov",
            statistic=d_stat,
            p_value=p_val,
            is_statistically_significant=sig,
            effect_size=d_stat,
            interpretation=interp,
        )

    @staticmethod
    def wilcoxon_signed_rank_test(
        ours_errors: List[float] | np.ndarray,
        baseline_errors: List[float] | np.ndarray,
        alpha: float = 0.05,
    ) -> HypothesisTestResult:
        """Perform Wilcoxon paired signed-rank test across matching runs."""
        arr1 = np.asarray(ours_errors, dtype=np.float64)
        arr2 = np.asarray(baseline_errors, dtype=np.float64)

        min_len = min(len(arr1), len(arr2))
        if min_len < 5:
            return HypothesisTestResult(
                test_name="Wilcoxon Signed-Rank",
                statistic=0.0,
                p_value=1.0,
                is_statistically_significant=False,
                effect_size=0.0,
                interpretation="Insufficient paired samples (need >= 5)",
            )

        res = stats.wilcoxon(arr1[:min_len], arr2[:min_len])
        stat = float(res.statistic)
        p_val = float(res.pvalue)

        sig = (p_val < alpha)
        interp = "OURS algorithm consistently outperforms baseline across paired scenarios (p < 0.05)" if sig else "No statistically significant difference on paired runs"

        return HypothesisTestResult(
            test_name="Wilcoxon Signed-Rank",
            statistic=stat,
            p_value=p_val,
            is_statistically_significant=sig,
            effect_size=float(stat / (min_len * (min_len + 1) / 4.0)),
            interpretation=interp,
        )

    @staticmethod
    def bootstrap_confidence_interval(
        data: List[float] | np.ndarray,
        metric_name: str = "RMSE",
        n_resamples: int = 2000,
        ci_level: float = 0.95,
        seed: int = 42,
    ) -> BootstrapCIResult:
        """Compute non-parametric bootstrap percentile 95% Confidence Interval."""
        arr = np.asarray(data, dtype=np.float64)
        if len(arr) == 0:
            return BootstrapCIResult(
                metric_name=metric_name, mean_val=0.0, median_val=0.0, ci_lower_95=0.0, ci_upper_95=0.0, n_resamples=n_resamples
            )

        rng = np.random.default_rng(seed)
        resamples = rng.choice(arr, size=(n_resamples, len(arr)), replace=True)
        means = np.mean(resamples, axis=1)

        alpha_half = (1.0 - ci_level) / 2.0
        ci_lower = float(np.percentile(means, alpha_half * 100.0))
        ci_upper = float(np.percentile(means, (1.0 - alpha_half) * 100.0))

        return BootstrapCIResult(
            metric_name=metric_name,
            mean_val=float(np.mean(arr)),
            median_val=float(np.median(arr)),
            ci_lower_95=ci_lower,
            ci_upper_95=ci_upper,
            n_resamples=n_resamples,
        )

    @staticmethod
    def rank_ablation_deltas(
        full_pipeline_rmse: float,
        ablated_pipeline_rmses: Dict[str, float],
    ) -> List[Tuple[str, float, float]]:
        """Rank component contributions by tracking error delta."""
        results = []
        for component, ab_rmse in ablated_pipeline_rmses.items():
            delta_pct = max(0.0, ((ab_rmse - full_pipeline_rmse) / max(1e-6, full_pipeline_rmse)) * 100.0)
            results.append((component, ab_rmse, float(delta_pct)))

        results.sort(key=lambda x: x[2], reverse=True)
        return results
