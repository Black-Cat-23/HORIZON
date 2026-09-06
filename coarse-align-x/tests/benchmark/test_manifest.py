"""
Unit tests for ExperimentManifest serialization, immutability, and hashing.
"""

import json
import pytest
from benchmark.manifest import ExperimentManifest, DeterministicSeedSystem


def test_manifest_creation_and_immutability():
    manifest = ExperimentManifest(
        experiment_id="EXP_TEST_001",
        algorithm="OURS",
        master_seed=42,
        trial_seed=1001,
        trial_index=0,
        scenario_id="nominal",
        simulation_duration=10.0,
        simulation_frequency=60.0,
        camera_configuration={"width": 640, "height": 480},
        target_configuration={"size_px": 10},
        trajectory_configuration={"type": "circular"},
        disturbance_configuration={"gaussian": 2.0},
        perception_configuration={"mode": "HYBRID"},
        estimator_configuration={"type": "KALMAN"},
        controller_configuration={"mode": "CLOSED_LOOP"},
    )

    assert manifest.experiment_id == "EXP_TEST_001"
    assert manifest.algorithm == "OURS"
    assert manifest.master_seed == 42
    assert manifest.trial_seed == 1001

    with pytest.raises(AttributeError):
        manifest.algorithm = "B0"  # Frozen dataclass


def test_manifest_serialization_deserialization(tmp_path):
    manifest = ExperimentManifest(
        experiment_id="EXP_SER_001",
        algorithm="B1",
        master_seed=123,
        trial_seed=999,
        trial_index=1,
        scenario_id="severe",
        simulation_duration=5.0,
        simulation_frequency=60.0,
        camera_configuration={},
        target_configuration={},
        trajectory_configuration={},
        disturbance_configuration={},
        perception_configuration={},
        estimator_configuration={},
        controller_configuration={},
    )

    file_path = tmp_path / "manifest.json"
    manifest.save(file_path)

    loaded = ExperimentManifest.load(file_path)
    assert loaded.experiment_id == manifest.experiment_id
    assert loaded.algorithm == manifest.algorithm
    assert loaded.master_seed == manifest.master_seed
    assert loaded.trial_seed == manifest.trial_seed
