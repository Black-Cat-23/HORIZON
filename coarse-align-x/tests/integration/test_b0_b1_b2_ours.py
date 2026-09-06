"""
Integration tests comparing B0, B1, B2, and OURS algorithm execution profiles.
"""

from benchmark.manifest import DeterministicSeedSystem, ExperimentManifest
from benchmark.profiles import build_app_config_for_scenario
from benchmark.runner import run_single_trial


def test_b0_b1_b2_ours_execution_profiles():
    seed_sys = DeterministicSeedSystem(master_seed=42, scenario_id="nominal")
    trial_seed = seed_sys.get_trial_seed(0)
    cfg = build_app_config_for_scenario("nominal", seed=trial_seed, duration=1.0)

    for alg in ["B0", "B1", "B2", "OURS"]:
        manifest = ExperimentManifest(
            experiment_id=f"EXP_INTEG_{alg}",
            algorithm=alg,
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

        result = run_single_trial(manifest)
        assert result.algorithm == alg
        from benchmark.failure import FailureCategory
        assert result.status in [c.value for c in FailureCategory]
        assert "mean_tracking_error" in result.metrics
