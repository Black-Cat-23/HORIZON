"""
Phase 4 Verification Suite: Non-Parametric Statistical Suite & PDF Report Generator
======================================================================================
Validates Mann-Whitney U, Kolmogorov-Smirnov, Wilcoxon signed-rank tests,
Bootstrap 95% Confidence Intervals, and ISRO Performance PDF generation.
"""

import os
import tempfile
import pytest
import numpy as np

from analysis.statistical_suite import StatisticalDistributionSuite
from analysis.pdf_report_generator import ISROPerformancePDFGenerator


def test_non_parametric_statistical_tests() -> None:
    """Verify Mann-Whitney U, KS-Test, Wilcoxon test, and Bootstrap 95% CI calculations."""
    rng = np.random.default_rng(42)
    ours_errors = rng.normal(loc=0.15, scale=0.05, size=100)
    baseline_errors = rng.normal(loc=0.85, scale=0.20, size=100)

    # 1. Mann-Whitney U
    mwu = StatisticalDistributionSuite.mann_whitney_u_test(ours_errors, baseline_errors)
    assert mwu.is_statistically_significant is True
    assert mwu.p_value < 0.05
    assert mwu.effect_size > 0.0

    # 2. Kolmogorov-Smirnov
    ks = StatisticalDistributionSuite.kolmogorov_smirnov_test(ours_errors, baseline_errors)
    assert ks.is_statistically_significant is True
    assert ks.statistic > 0.5

    # 3. Wilcoxon Paired Signed-Rank Test
    wilc = StatisticalDistributionSuite.wilcoxon_signed_rank_test(ours_errors, baseline_errors)
    assert wilc.is_statistically_significant is True

    # 4. Bootstrap 95% Confidence Interval
    ci = StatisticalDistributionSuite.bootstrap_confidence_interval(ours_errors, metric_name="RMSE", n_resamples=500)
    assert ci.ci_lower_95 <= ci.mean_val <= ci.ci_upper_95
    assert ci.ci_lower_95 > 0.0


def test_isro_pdf_report_generation() -> None:
    """Verify ISRO PDF Performance Report generation produces a non-empty valid PDF document."""
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        temp_pdf_path = f.name

    try:
        gen = ISROPerformancePDFGenerator(output_path=temp_pdf_path)
        pdf_path = gen.generate()

        assert os.path.exists(pdf_path)
        assert os.path.getsize(pdf_path) > 1000, "PDF document must contain formatted pages and graphics (>1 KB)"
    finally:
        if os.path.exists(temp_pdf_path):
            os.remove(temp_pdf_path)
