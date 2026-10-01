"""
Unit tests for trial execution repeatability and determinism.
"""

from benchmark.manifest import ExperimentManifest, DeterministicSeedSystem
from benchmark.runner import run_single_trial
from benchmark.profiles import build_app_config_for_scenario


def test_single_trial_repeatability():
    seed_sys = DeterministicSeedSystem(master_seed=42, scenario_id="nominal")
    trial_seed = seed_sys.get_trial_seed(0)
    cfg = build_app_config_for_scenario("nominal", seed=trial_seed, duration=1.0)

    manifest1 = ExperimentManifest(
        experiment_id="EXP_DET_1",
        algorithm="B1",
        master_seed=42,
        trial_seed=trial_seed,
        trial_index=0,
        scenario_id="nominal",
        simulation_duration=1.0,
        simulation_frequency=cfg.simulation.frequency_hz,
        camera_configuration=cfg.camera.__dict__,
        target_configuration=cfg.target.__dict__,
        trajectory_configuration=cfg.trajectory.__dict__,
        disturbance_configuration=cfg.disturbance.__dict__,
        perception_configuration={},
        estimator_configuration={},
        controller_configuration={},
    )

    res1 = run_single_trial(manifest1)
    res2 = run_single_trial(manifest1)

    # Core algorithmic metrics must be exactly reproducible with the same seed.
    # Note: `status` is intentionally excluded here — it is derived from
    # FailureClassifier.classify_trial() which checks P95 *wall-clock* processing
    # time against a 50ms threshold. Under heavy parallel test load the second call
    # can be CPU-starved and cross the threshold while the first does not, producing
    # a spurious PROCESSING_OVERRUN vs SUCCESS mismatch that is NOT an algorithmic
    # non-determinism issue.
    assert res1.metrics["mean_tracking_error"] == res2.metrics["mean_tracking_error"]
    assert res1.metrics["lock_retention_rate"] == res2.metrics["lock_retention_rate"]
