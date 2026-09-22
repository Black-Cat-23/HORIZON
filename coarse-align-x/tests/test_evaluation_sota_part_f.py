"""Unit tests for Phase F: Evaluation, Metrics, Benchmarking & Ground-Truth Invariant Verification Engine SOTA Upgrades."""

import math
import numpy as np
import pytest

from benchmark.invariant_checker import GroundTruthInvariantGuard
from benchmark.metrics import MetricEngine, compute_binomial_ci, compute_bootstrap_ci
from benchmark.sih26169_compliance import SIH26169ComplianceEvaluator
from tracking.diagnostics.evaluation import EstimatorEvaluator


def test_chi2_nees_consistency_hypothesis_evaluation():
    """Verify 95% Chi-square NEES consistency bounds evaluation."""
    evaluator = EstimatorEvaluator()

    # Record 50 consistent step error samples
    for i in range(50):
        cov = np.eye(4, dtype=np.float64) * 2.0
        evaluator.record_step(
            estimated_pos=(100.0 + i, 200.0 + i),
            estimated_vel=(10.0, 5.0),
            covariance=cov,
            gt_pos=(100.1 + i, 200.1 + i),
            gt_vel=(10.0, 5.0),
            timestamp=0.1 * i,
        )

    status, mean_nees, ci_lower, ci_upper = evaluator.evaluate_chi2_consistency(dof=4)

    assert status in ("VALID_CONSISTENT", "OVERCONFIDENT_OPTIMISTIC", "UNDERCONFIDENT_PESSIMISTIC")
    assert mean_nees > 0.0
    assert ci_lower < ci_upper


def test_bootstrap_and_wilson_confidence_intervals():
    """Verify non-parametric bootstrap and Wilson score confidence intervals."""
    data = [0.1, 0.12, 0.09, 0.11, 0.15, 0.08, 0.13, 0.10, 0.14, 0.11]
    point_est, ci_lower, ci_upper = compute_bootstrap_ci(data, stat_fn="mean", num_samples=200)

    assert ci_lower <= point_est <= ci_upper

    prop, w_lower, w_upper = compute_binomial_ci(successes=98, total=100)
    assert prop == 0.98
    assert w_lower < prop < w_upper


def test_ground_truth_invariant_guard():
    """Verify GroundTruthInvariantGuard blocks forbidden ground truth kwargs."""
    clean_kwargs = {"measurement": (100.0, 100.0), "confidence": 0.95}
    assert GroundTruthInvariantGuard.verify_no_ground_truth_in_kwargs(clean_kwargs)

    dirty_kwargs = {"measurement": (100.0, 100.0), "true_x": 100.1}
    with pytest.raises(ValueError, match="CRITICAL LEAKAGE DETECTED"):
        GroundTruthInvariantGuard.verify_no_ground_truth_in_kwargs(dirty_kwargs, caller_name="update_step")


def test_isro_sih26169_compliance_evaluator():
    """Verify SIH26169ComplianceEvaluator audit report."""
    metrics = {
        "acquisition_time": 0.25,
        "reacquisition_time": 0.10,
        "RMSE_tracking_error": 0.20,
        "P95_tracking_error": 0.25,
        "median_tracking_error": 0.18,
        "lock_retention_rate": 0.99,
    }

    report = SIH26169ComplianceEvaluator.evaluate_trial_metrics(metrics)

    assert report.is_fully_compliant
    assert report.acquisition_compliant
    assert report.reacquisition_compliant
    assert report.pointing_rmse_compliant
    assert report.jitter_compliant
    assert report.lock_retention_compliant
