"""
Unit tests for DeterministicSeedSystem.
"""

from benchmark.manifest import DeterministicSeedSystem


def test_seed_generation_determinism():
    seed_sys1 = DeterministicSeedSystem(master_seed=42, scenario_id="nominal")
    seed_sys2 = DeterministicSeedSystem(master_seed=42, scenario_id="nominal")

    seeds1 = [seed_sys1.get_trial_seed(i) for i in range(10)]
    seeds2 = [seed_sys2.get_trial_seed(i) for i in range(10)]

    assert seeds1 == seeds2
    assert len(set(seeds1)) == 10  # All trial seeds unique for distinct indices


def test_seed_generation_scenario_independence():
    seed_sys_nom = DeterministicSeedSystem(master_seed=42, scenario_id="nominal")
    seed_sys_sev = DeterministicSeedSystem(master_seed=42, scenario_id="severe")

    seeds_nom = [seed_sys_nom.get_trial_seed(i) for i in range(5)]
    seeds_sev = [seed_sys_sev.get_trial_seed(i) for i in range(5)]

    assert seeds_nom != seeds_sev
