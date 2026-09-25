"""
Hard-Negative Mining Pipeline Tests for HORIZON Perception Engine.
Phase 7 Upgrade: Harvesting false-positive candidates with data isolation.
"""

from pathlib import Path
import numpy as np
import pytest

from simulator.perception.hard_negative import HardNegativeMiner, HardNegativeSample


def test_hard_negative_miner_recording(tmp_path):
    """Verify recording and exporting false positives without crashing."""
    miner = HardNegativeMiner(output_dir=tmp_path / "hard_negatives", max_samples=10)
    
    frame = np.full((480, 640), 25, dtype=np.uint8)
    sample = miner.record_false_positive(
        frame=frame,
        bbox=(100, 100, 20, 20),
        score=0.85,
        snr=4.5,
        peak_intensity=200,
        background_mean=25,
        distractor_type="GLINT",
        failure_mode="FALSE_LOCK",
        timestamp_s=1.25,
    )

    assert isinstance(sample, HardNegativeSample)
    assert miner.sample_count == 1
    assert sample.distractor_type == "GLINT"

    manifest_path = miner.export_manifest()
    assert manifest_path.exists()
