"""
Unit tests for batch runner checkpointing and resumption.
"""

import json
from benchmark.runner import BatchRunner, TrialResult


def test_checkpointing_resumption(tmp_path):
    runner = BatchRunner(output_dir=tmp_path)

    # 1. Run 2 trials first
    trials_part1 = runner.run_batch(
        algorithm="B1",
        scenario_id="nominal",
        master_seed=42,
        trials_count=2,
        duration=1.0,
    )
    assert len(trials_part1) == 2

    # 2. Run total 4 trials (should resume 2 and execute remaining 2)
    trials_part2 = runner.run_batch(
        algorithm="B1",
        scenario_id="nominal",
        master_seed=42,
        trials_count=4,
        duration=1.0,
    )
    assert len(trials_part2) == 4
    # First 2 trial IDs match
    assert trials_part2[0].trial_id == trials_part1[0].trial_id
    assert trials_part2[1].trial_id == trials_part1[1].trial_id
