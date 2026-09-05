"""Tests for deterministic reproducibility across runs and seeds."""

import numpy as np
import pytest
from dataclasses import asdict
from simulator.core.config import AppConfig, SimulationConfig, TrajectoryConfig, RandomTrajectoryConfig
from simulator.core.simulation import SimulationEngine


class TestReproducibility:
    """Validate 100% deterministic reproducibility for experiments."""

    @pytest.mark.parametrize("traj_type", ["straight", "circular", "figure8", "random"])
    def test_identical_seed_produces_identical_run(self, traj_type: str):
        """Two independent engine instances with identical seed must produce identical outputs."""
        config = AppConfig(
            simulation=SimulationConfig(seed=42, frequency_hz=60.0, duration_seconds=0.5),
            trajectory=TrajectoryConfig(type=traj_type),
        )

        engine1 = SimulationEngine(config, experiment_id="EXP_RUN_1")
        engine2 = SimulationEngine(config, experiment_id="EXP_RUN_2")

        states1, states2 = [], []
        frames1, frames2 = [], []

        def cb1(f, s, img):
            states1.append(asdict(s))
            frames1.append(img.copy())

        def cb2(f, s, img):
            states2.append(asdict(s))
            frames2.append(img.copy())

        engine1.run(callback=cb1)
        engine2.run(callback=cb2)

        # 1. Exact count
        assert len(states1) == len(states2) == 31

        # 2. Exact state equality for every frame
        for f, (s1, s2) in enumerate(zip(states1, states2)):
            for key in ["x", "y", "vx", "vy", "ax", "ay", "timestamp"]:
                assert s1[key] == pytest.approx(s2[key], abs=1e-9), f"Mismatch in {key} at frame {f} ({traj_type})"

        # 3. Exact image pixel equality for every frame
        for f, (img1, img2) in enumerate(zip(frames1, frames2)):
            assert np.array_equal(img1, img2), f"Pixel mismatch in rendered image at frame {f} ({traj_type})"

        # 4. Exact ground truth records equality (excluding exp id)
        r1 = engine1.recorder.records
        r2 = engine2.recorder.records
        assert len(r1) == len(r2)
        for rec1, rec2 in zip(r1, r2):
            assert rec1.frame == rec2.frame
            assert rec1.target_x == rec2.target_x
            assert rec1.target_y == rec2.target_y
            assert rec1.target_vx == rec2.target_vx
            assert rec1.target_vy == rec2.target_vy

    def test_different_seed_produces_divergent_random_motion(self):
        """Different seeds for random motion must produce different trajectories."""
        config1 = AppConfig(
            simulation=SimulationConfig(seed=101, frequency_hz=60.0, duration_seconds=1.0),
            trajectory=TrajectoryConfig(type="random"),
        )
        config2 = AppConfig(
            simulation=SimulationConfig(seed=202, frequency_hz=60.0, duration_seconds=1.0),
            trajectory=TrajectoryConfig(type="random"),
        )

        engine1 = SimulationEngine(config1)
        engine2 = SimulationEngine(config2)

        engine1.run()
        engine2.run()

        s1 = engine1.get_current_state()
        s2 = engine2.get_current_state()

        # At t=1.0s, different seeds should not be in the same position
        pos_dist = np.hypot(s1.x - s2.x, s1.y - s2.y)
        assert pos_dist > 5.0, f"Expected divergent trajectories, but distance was {pos_dist} px"
