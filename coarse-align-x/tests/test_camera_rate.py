"""
Formal V&V: Clock Timesteps, Camera Update Rate, Ground-Truth Telemetry, and Serialization.
Sections 4, 5, 19, 20, 21 of Phase 2 Formal Verification & Validation specification.
"""

import csv
import json
import numpy as np
import pytest
from simulator.core.config import AppConfig, SimulationConfig, TrajectoryConfig
from simulator.core.simulation import SimulationEngine


class TestClockAndRateVerification:
    """Sections 4 & 5: Clock and Camera Rate Verification."""

    def test_fixed_timestep_clock_progression(self):
        config = AppConfig(
            simulation=SimulationConfig(frequency_hz=60.0, duration_seconds=10.0)
        )
        engine = SimulationEngine(config)
        engine.initialize()

        assert engine.clock.current_frame == 0
        assert engine.clock.current_time == 0.0

        engine.step()
        assert engine.clock.current_frame == 1
        assert abs(engine.clock.current_time - (1.0 / 60.0)) < 1e-12

        engine.step()
        assert engine.clock.current_frame == 2
        assert abs(engine.clock.current_time - (2.0 / 60.0)) < 1e-12

    def test_10_second_simulation_observation_counts(self):
        # 10s at 60 Hz simulation = 600 steps
        # Camera at 30 Hz = captures every 2nd frame (frames 0, 2, 4, ... 600) = 301 observations
        config = AppConfig(
            simulation=SimulationConfig(frequency_hz=60.0, duration_seconds=10.0)
        )
        engine = SimulationEngine(config)
        engine.initialize()

        obs_frames = []

        def capture_hook(f, s, frame):
            if engine.camera.is_new_observation:
                obs = engine.get_camera_frame()
                obs_frames.append(f)

        engine.run(callback=capture_hook)

        # Expected simulation steps
        assert engine.clock.current_frame == 600
        # Expected camera observations ≈ 300 (specifically 301 including frame 0)
        assert abs(len(obs_frames) - 300) <= 1
        assert abs(engine.camera.observation_count - 300) <= 1


class TestGroundTruthAndSerializationVerification:
    """Sections 19, 20, 21: Ground Truth Telemetry, CSV/JSON Export, and Bit-Exact Determinism."""

    def test_ground_truth_fields_and_no_ai_leakage(self):
        config = AppConfig(
            simulation=SimulationConfig(frequency_hz=60.0, duration_seconds=0.2)
        )
        engine = SimulationEngine(config)
        engine.run()

        records = engine.recorder.records
        assert len(records) == 13  # 12 steps + initial

        # Verify all mandatory Phase 2 fields exist and no detector fields exist
        rec = records[0]
        assert hasattr(rec, "camera_pan_deg")
        assert hasattr(rec, "camera_tilt_deg")
        assert hasattr(rec, "target_theta_x_deg")
        assert hasattr(rec, "target_theta_y_deg")
        assert hasattr(rec, "target_pixel_u")
        assert hasattr(rec, "target_pixel_v")
        assert hasattr(rec, "target_in_fov")

        # Confirm NO AI/detector fields exist
        forbidden_fields = ["detected_x", "confidence", "kalman_x", "yolo_box", "pid_output"]
        for forbidden in forbidden_fields:
            assert not hasattr(rec, forbidden), f"Forbidden field '{forbidden}' found in ground truth!"

    def test_csv_json_export_and_readback(self, tmp_path):
        config = AppConfig(
            simulation=SimulationConfig(frequency_hz=60.0, duration_seconds=0.2)
        )
        engine = SimulationEngine(config)
        engine.run()

        csv_file = tmp_path / "telemetry.csv"
        json_file = tmp_path / "telemetry.json"

        engine.recorder.export_csv(csv_file)
        engine.recorder.export_json(json_file)

        # Read back CSV
        with open(csv_file, "r", encoding="utf-8") as f:
            reader = list(csv.DictReader(f))
            assert len(reader) == 13
            assert "camera_pan_deg" in reader[0]
            assert "target_pixel_u" in reader[0]

        # Read back JSON
        with open(json_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            assert data["metadata"]["total_frames"] == 13
            assert len(data["records"]) == 13

    def test_phase2_determinism_experiments(self):
        # Experiment A: Seed 42 with target at center (1000, 1000)
        # Experiment B: Seed 42 with target at center (1000, 1000)
        from simulator.core.config import TargetConfig, TargetInitialPosition
        init_center = TargetConfig(initial_position=TargetInitialPosition(x=1000.0, y=1000.0))

        cfg_a = AppConfig(
            target=init_center,
            simulation=SimulationConfig(seed=42, duration_seconds=0.5),
        )
        cfg_b = AppConfig(
            target=init_center,
            simulation=SimulationConfig(seed=42, duration_seconds=0.5),
        )

        eng_a = SimulationEngine(cfg_a)
        eng_b = SimulationEngine(cfg_b)

        eng_a.run()
        eng_b.run()

        # Both must produce identical camera observation
        cam_a = eng_a.get_camera_frame()
        cam_b = eng_b.get_camera_frame()
        assert np.array_equal(cam_a, cam_b)

        # Experiment C: Seed 43 (divergent random motion from center)
        cfg_c = AppConfig(
            target=init_center,
            simulation=SimulationConfig(seed=43, duration_seconds=0.5),
            trajectory=TrajectoryConfig(type="random"),
        )
        eng_c = SimulationEngine(cfg_c)
        eng_c.run()

        cam_c = eng_c.get_camera_frame()
        assert not np.array_equal(cam_a, cam_c)
