"""
Unit and integration tests for 4-Way Monte Carlo Runner & 2D Robustness Envelope.
HORIZON — SIH 2026 PS SIH26169 (PDF Section 6.9 & 6.10)
"""

import numpy as np
import pytest
from benchmarks.monte_carlo_runner import MonteCarloRunner
from benchmarks.robustness_envelope import RobustnessEnvelopeGenerator


def test_monte_carlo_reproducibility():
    """Verifies that fixing the random seed guarantees exact numerical replay."""
    runner = MonteCarloRunner(num_trials=5, trial_duration_s=2.0, seed_start=555)
    
    # Run 1
    metrics_run1 = runner.run_benchmark_suite()
    
    # Run 2 with identical seed
    metrics_run2 = runner.run_benchmark_suite()

    for algo in ["B0", "B1", "B2", "OURS"]:
        m1 = metrics_run1[algo]
        m2 = metrics_run2[algo]
        assert m1.acquisition_success_pct == pytest.approx(m2.acquisition_success_pct)
        assert m1.mean_tracking_error_deg == pytest.approx(m2.mean_tracking_error_deg)
        assert m1.median_time_to_lock_s == pytest.approx(m2.median_time_to_lock_s)


def test_monte_carlo_4way_evaluation():
    """Verifies that all 4 algorithms are evaluated and produce valid metric ranges."""
    runner = MonteCarloRunner(num_trials=4, trial_duration_s=2.0, seed_start=123)
    metrics = runner.run_benchmark_suite()

    assert set(metrics.keys()) == {"B0", "B1", "B2", "OURS"}

    for algo, m in metrics.items():
        assert 0.0 <= m.acquisition_success_pct <= 100.0
        assert 0.0 <= m.lock_retention_pct <= 100.0
        assert 0.0 <= m.false_lock_rate_pct <= 100.0
        assert m.mean_tracking_error_deg >= 0.0
        assert m.achieved_fps > 10.0


def test_robustness_envelope_boundary_calculation():
    """Verifies 2D robustness boundary computation on known synthetic grid."""
    generator = RobustnessEnvelopeGenerator(
        speeds_deg_s=[1.0, 2.0],
        disturbance_levels=[0.5, 1.0, 2.0],
        success_threshold=0.90,
    )
    # Speed 1: passes all 3 levels (0.5, 1.0, 2.0)
    # Speed 2: passes 0.5 and 1.0, fails 2.0 (0.80 < 0.90)
    synthetic_grid = np.array([
        [0.98, 0.95, 0.92],
        [0.95, 0.91, 0.80],
    ])

    boundary, area_score = generator.compute_boundary(synthetic_grid)
    assert boundary["1.0"] == pytest.approx(2.0)
    assert boundary["2.0"] == pytest.approx(1.0)
    assert area_score == pytest.approx(5.0 / 6.0)

