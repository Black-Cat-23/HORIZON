"""
Integration tests for headless batch runner and CLI functions.
"""

from benchmark.runner import BatchRunner
from benchmark.run import execute_fair_comparison


def test_headless_batch_runner_execution(tmp_path):
    runner = BatchRunner(output_dir=tmp_path)
    trials = runner.run_batch(
        algorithm="OURS",
        scenario_id="nominal",
        master_seed=42,
        trials_count=2,
        duration=1.0,
    )

    assert len(trials) == 2
    assert all(t.algorithm == "OURS" for t in trials)


def test_execute_fair_comparison_integration(tmp_path):
    summary = execute_fair_comparison(
        algorithms=["B1", "OURS"],
        scenario_id="nominal",
        master_seed=42,
        trials_count=2,
        duration=1.0,
        parallel=False,
        output_dir=tmp_path,
    )

    assert "B1" in summary
    assert "OURS" in summary
    assert (tmp_path / "comparisons" / "comparison.json").exists()
