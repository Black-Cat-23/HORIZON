"""
Unit tests for fair algorithm comparison matching seeds and scenarios.
"""

from benchmark.manifest import DeterministicSeedSystem
from benchmark.profiles import build_app_config_for_scenario


def test_fair_comparison_seed_and_scenario_matching():
    seed_sys = DeterministicSeedSystem(master_seed=100, scenario_id="severe")

    # Trial 0 seed for B0, B1, B2, OURS
    t0_seed_b0 = seed_sys.get_trial_seed(0)
    t0_seed_b1 = seed_sys.get_trial_seed(0)
    t0_seed_b2 = seed_sys.get_trial_seed(0)
    t0_seed_ours = seed_sys.get_trial_seed(0)

    assert t0_seed_b0 == t0_seed_b1 == t0_seed_b2 == t0_seed_ours

    # Verify identical resolved config objects generated
    cfg_b0 = build_app_config_for_scenario("severe", seed=t0_seed_b0)
    cfg_ours = build_app_config_for_scenario("severe", seed=t0_seed_ours)

    assert cfg_b0.simulation.seed == cfg_ours.simulation.seed
    assert cfg_b0.target.size_px == cfg_ours.target.size_px
    assert cfg_b0.disturbance.gaussian.sigma == cfg_ours.disturbance.gaussian.sigma
