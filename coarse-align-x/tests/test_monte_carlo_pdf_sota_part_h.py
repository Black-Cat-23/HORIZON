"""Unit tests for Phase H: Monte Carlo Batch Sweeper, Non-Parametric Statistical Suite & Automated ISRO PDF Report Generator SOTA Upgrades."""

import tempfile
from pathlib import Path
import numpy as np
import pytest

from analysis.pdf_report_generator import ISROPerformancePDFGenerator
from analysis.statistical_suite import HypothesisTestResult, StatisticalDistributionSuite
from benchmarks.monte_carlo_runner import MonteCarloRunner


def test_statistical_distribution_suite_mann_whitney():
    """Verify Mann-Whitney U and Kolmogorov-Smirnov statistical hypothesis testing."""
    ours_errors = [0.08, 0.09, 0.07, 0.10, 0.06, 0.09, 0.08]
    baseline_errors = [0.45, 0.50, 0.38, 0.55, 0.42, 0.49, 0.51]

    mw_res = StatisticalDistributionSuite.mann_whitney_u_test(ours_errors, baseline_errors)
    assert isinstance(mw_res, HypothesisTestResult)
    assert mw_res.is_statistically_significant
    assert mw_res.p_value < 0.05

    ks_res = StatisticalDistributionSuite.kolmogorov_smirnov_test(ours_errors, baseline_errors)
    assert isinstance(ks_res, HypothesisTestResult)
    assert ks_res.is_statistically_significant
    assert ks_res.statistic > 0.5


def test_ablation_delta_ranking():
    """Verify component ablation delta ranking."""
    full_rmse = 0.12
    ablated_map = {
        "No Zernike PSF": 0.25,
        "No IMM-EKF": 0.42,
        "No JPDA Gating": 0.31,
    }

    rankings = StatisticalDistributionSuite.rank_ablation_deltas(full_rmse, ablated_map)
    assert len(rankings) == 3
    # Top impact component should be No IMM-EKF
    assert rankings[0][0] == "No IMM-EKF"
    assert rankings[0][2] > 200.0  # > 200% degradation


def test_parallel_monte_carlo_runner():
    """Verify multi-threaded parallel Monte Carlo benchmark suite execution."""
    runner = MonteCarloRunner(num_trials=4, trial_duration_s=0.5, dt=0.016, algorithms=["OURS"])
    metrics = runner.run_parallel_benchmark_suite(num_workers=2)

    assert "OURS" in metrics
    m = metrics["OURS"]
    assert m.trials_run == 4
    assert m.acquisition_success_pct >= 0.0
    assert m.achieved_fps > 0.0


def test_isro_pdf_report_generator():
    """Verify ReportLab PDF generation for ISRO evaluation report."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        pdf_path = Path(tmp_dir) / "ISRO_Test_Report.pdf"
        generator = ISROPerformancePDFGenerator(output_path=str(pdf_path))

        generated_file = generator.generate(benchmark_metrics=None)
        assert Path(generated_file).exists()
        assert Path(generated_file).stat().st_size > 1000  # Non-empty PDF
