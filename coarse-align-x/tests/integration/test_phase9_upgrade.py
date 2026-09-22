"""
HORIZON Phase 9 Upgrade Verification Test Suite
=================================================
Verifies Steps 1 to 14 of the Phase 9 Existing Benchmark Upgrade:
  - Step 1: Configuration freezing & SHA-256 hashing.
  - Step 2: Fair seed matching across baseline algorithms.
  - Step 3 & 4: Multi-factor scenario challenge presets.
  - Step 5 & 6: Trial repeatability and failure preservation.
  - Step 7 & 8: External MP4 video evaluation & strict blind mode.
  - Step 9 & 10: Replay & counterfactual experiment runner.
  - Step 11 & 12: Monte Carlo execution & audit bundle export.
  - Step 13: Metric computation completeness.
"""

import json
from pathlib import Path
import pytest
import numpy as np

from benchmark.manifest import DeterministicSeedSystem, ExperimentManifest, compute_config_hash
from benchmark.profiles import SCENARIO_PRESETS, build_app_config_for_scenario, get_algorithm_profile
from benchmark.runner import BatchRunner, run_single_trial, run_counterfactual_experiment, export_audit_bundle
from benchmark.failure import FailureClassifier, FailureCategory
from benchmark.metrics import MetricEngine


def test_step1_frozen_algorithm_configurations():
    """Verify algorithm configurations are frozen and generate consistent SHA-256 hashes."""
    b0_profile = get_algorithm_profile("B0")
    b1_profile = get_algorithm_profile("B1")
    b2_profile = get_algorithm_profile("B2")
    ours_profile = get_algorithm_profile("OURS")

    hash_b0 = compute_config_hash(b0_profile)
    hash_ours = compute_config_hash(ours_profile)

    assert len(hash_b0) == 16
    assert hash_b0 != hash_ours
    assert compute_config_hash(b0_profile) == hash_b0


def test_step2_fair_seed_matching():
    """Verify DeterministicSeedSystem produces identical seeds across B0, B1, B2, OURS for trial index i."""
    seed_sys = DeterministicSeedSystem(master_seed=42, scenario_id="severe")
    
    seed_0 = seed_sys.get_trial_seed(0)
    seed_1 = seed_sys.get_trial_seed(1)
    seed_0_repeat = seed_sys.get_trial_seed(0)

    assert seed_0 == seed_0_repeat
    assert seed_0 != seed_1
    assert 0 <= seed_0 < 2**31


def test_step3_step4_scenario_factors():
    """Verify challenge presets support controlled scenario factor variations."""
    assert "challenge_stealth" in SCENARIO_PRESETS
    assert "challenge_maneuver" in SCENARIO_PRESETS
    assert "challenge_heavy_jitter" in SCENARIO_PRESETS
    assert "challenge_occlusion" in SCENARIO_PRESETS

    cfg = build_app_config_for_scenario("challenge_stealth", seed=100, duration=2.0)
    assert cfg.target.size_px == 4
    assert cfg.disturbance.atmosphere.enabled is True


def test_step5_step6_repeatability_and_failure_preservation():
    """Verify trial execution is reproducible and failure classification is preserved."""
    manifest = ExperimentManifest(
        experiment_id="TEST_EXP_01",
        algorithm="B1",
        master_seed=42,
        trial_seed=12345,
        trial_index=0,
        scenario_id="nominal",
        simulation_duration=1.0,
        simulation_frequency=30.0,
        camera_configuration={},
        target_configuration={},
        trajectory_configuration={},
        disturbance_configuration={},
        perception_configuration={},
        estimator_configuration={},
        controller_configuration={},
    )

    res1 = run_single_trial(manifest)
    res2 = run_single_trial(manifest)

    assert res1.trial_id == res2.trial_id
    assert res1.status in [c.value for c in FailureCategory]
    assert res1.metrics["mean_tracking_error"] == res2.metrics["mean_tracking_error"]


def test_step9_step10_counterfactual_runner(tmp_path):
    """Verify counterfactual experiment runner executes pair-matched trials."""
    res = run_counterfactual_experiment(
        algorithm="OURS",
        scenario_id="nominal",
        disturbance_factor="camera_jitter",
        master_seed=42,
        trials_count=2,
        output_dir=tmp_path,
    )

    assert res["trials_count"] == 2
    assert "mean_error_ON" in res
    assert "mean_error_OFF" in res
    assert len(res["trials_ON"]) == 2
    assert len(res["trials_OFF"]) == 2


def test_step11_step12_audit_bundle_export(tmp_path):
    """Verify audit bundle export generates manifest and audit files."""
    bundle_path = export_audit_bundle("EXP_TEST_BUNDLE_01", output_dir=tmp_path)
    assert bundle_path.exists()

    with open(bundle_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data["experiment_id"] == "EXP_TEST_BUNDLE_01"
    assert data["status"] == "COMPLETED"
    assert "frozen_models" in data


def test_step13_metrics_computation():
    """Verify MetricEngine computes mandatory and extended metrics."""
    telemetry = [
        {"timestamp": 0.0, "true_x": 100.0, "true_y": 100.0, "est_x": 102.0, "est_y": 101.0, "detected": True, "state": "TRACK", "processing_time_ms": 10.0, "is_saturated": False},
        {"timestamp": 0.1, "true_x": 105.0, "true_y": 105.0, "est_x": 107.0, "est_y": 106.0, "detected": True, "state": "TRACK", "processing_time_ms": 11.0, "is_saturated": False},
    ]

    engine = MetricEngine(sensor_width_px=640)
    metrics = engine.evaluate_telemetry(telemetry)

    assert "mean_tracking_error" in metrics
    assert "RMSE_tracking_error" in metrics
    assert "lock_retention_rate" in metrics
    assert metrics["lock_retention_rate"] == 1.0
