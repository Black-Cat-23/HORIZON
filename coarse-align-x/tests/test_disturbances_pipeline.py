"""
HORIZON Phase 3 Unit Tests: Pipeline Composition & Ground Truth Invariance
================================================================================
Verification of:
  - Clean frame vs Disturbed frame separation
  - Ground truth integrity (zero corruption from disturbances)
  - Disturbance combinations and compositions
  - Predefined presets (NOMINAL, DIFFICULT, SEVERE, RECOVERY, ADVERSARIAL)
"""

import math
import numpy as np
import pytest

from simulator.core.config import AppConfig, SimulationConfig, TrajectoryConfig
from simulator.core.seed_manager import SeedManager
from simulator.core.simulation import SimulationEngine
from simulator.disturbances.config import (
    AtmosphereConfig,
    CameraJitterConfig,
    DisturbanceConfig,
    GaussianNoiseConfig,
    PlatformMotionConfig,
    PoissonNoiseConfig,
    SaltPepperConfig,
)
from simulator.disturbances.pipeline import DisturbancePipeline
from simulator.disturbances.presets import get_preset_config


class TestPipelineComposition:
    """Verification of disturbance pipeline composition and numerical safety."""

    @pytest.fixture
    def clean_frame(self):
        rng = np.random.default_rng(42)
        return rng.integers(30, 220, size=(480, 640), dtype=np.uint8)

    def test_clean_frame_unmodified(self, clean_frame):
        seed_mgr = SeedManager(seed=42)
        cfg = get_preset_config("SEVERE")
        pipeline = DisturbancePipeline(cfg, seed_mgr)

        clean_copy = clean_frame.copy()
        disturbed, telemetry = pipeline.apply(clean_frame, sim_time=0.1, sim_dt=1/60.0)

        # Original frame array must remain strictly unmodified
        assert np.array_equal(clean_frame, clean_copy)
        # Disturbed frame must differ
        assert not np.array_equal(clean_frame, disturbed)
        assert disturbed.shape == (480, 640)
        assert disturbed.dtype == np.uint8

    @pytest.mark.parametrize(
        "combo",
        [
            ("gaussian_only", DisturbanceConfig(gaussian=GaussianNoiseConfig(enabled=True, sigma=10.0))),
            ("sp_only", DisturbanceConfig(salt_pepper=SaltPepperConfig(enabled=True, probability=0.08))),
            ("poisson_only", DisturbanceConfig(poisson=PoissonNoiseConfig(enabled=True, peak_photons=40.0))),
            ("gaussian_plus_sp", DisturbanceConfig(
                gaussian=GaussianNoiseConfig(enabled=True, sigma=8.0),
                salt_pepper=SaltPepperConfig(enabled=True, probability=0.05)
            )),
            ("gaussian_plus_fog", DisturbanceConfig(
                gaussian=GaussianNoiseConfig(enabled=True, sigma=10.0),
                atmosphere=AtmosphereConfig(enabled=True, condition="fog")
            )),
            ("sp_plus_fog", DisturbanceConfig(
                salt_pepper=SaltPepperConfig(enabled=True, probability=0.07),
                atmosphere=AtmosphereConfig(enabled=True, condition="fog")
            )),
            ("gaussian_fog_jitter", DisturbanceConfig(
                gaussian=GaussianNoiseConfig(enabled=True, sigma=12.0),
                atmosphere=AtmosphereConfig(enabled=True, condition="fog"),
                camera_jitter=CameraJitterConfig(enabled=True, max_x_px=10.0, max_y_px=10.0)
            )),
            ("all_simultaneous", get_preset_config("ADVERSARIAL")),
        ],
    )
    def test_disturbance_combinations_numerical_safety(self, clean_frame, combo):
        name, dist_cfg = combo
        pipeline = DisturbancePipeline(dist_cfg, SeedManager(seed=123))

        disturbed, telemetry = pipeline.apply(clean_frame, sim_time=0.5, sim_dt=1/60.0)

        assert disturbed.shape == (480, 640)
        assert disturbed.dtype == np.uint8
        assert not np.isnan(disturbed).any()
        assert not np.isinf(disturbed).any()
        assert disturbed.min() >= 0
        assert disturbed.max() <= 255


class TestGroundTruthIntegrity:
    """CRITICAL HARD RULE: Disturbances must NOT corrupt ground truth."""

    def test_ground_truth_identical_with_and_without_disturbances(self):
        # Run 1: Clean simulation (NOMINAL)
        clean_app_cfg = AppConfig(
            simulation=SimulationConfig(seed=42, duration_seconds=1.0, frequency_hz=60.0),
            trajectory=TrajectoryConfig(type="circular"),
            disturbance=get_preset_config("NOMINAL"),
        )
        engine_clean = SimulationEngine(clean_app_cfg)
        engine_clean.initialize()
        engine_clean.run()
        records_clean = engine_clean.recorder.records

        # Run 2: Severe disturbances (ADVERSARIAL)
        dist_app_cfg = AppConfig(
            simulation=SimulationConfig(seed=42, duration_seconds=1.0, frequency_hz=60.0),
            trajectory=TrajectoryConfig(type="circular"),
            disturbance=get_preset_config("ADVERSARIAL"),
        )
        engine_dist = SimulationEngine(dist_app_cfg)
        engine_dist.initialize()
        engine_dist.run()
        records_dist = engine_dist.recorder.records

        assert len(records_clean) == len(records_dist)

        for rc, rd in zip(records_clean, records_dist):
            # Ground-truth target kinematics MUST BE IDENTICAL
            assert rc.target_x == rd.target_x
            assert rc.target_y == rd.target_y
            assert rc.target_vx == rd.target_vx
            assert rc.target_vy == rd.target_vy
            assert rc.target_ax == rd.target_ax
            assert rc.target_ay == rd.target_ay
            assert rc.target_visible == rd.target_visible

            # Ground-truth camera gimbal angles MUST BE IDENTICAL
            assert rc.camera_pan_deg == rd.camera_pan_deg
            assert rc.camera_tilt_deg == rd.camera_tilt_deg
            assert rc.target_theta_x_deg == rd.target_theta_x_deg
            assert rc.target_theta_y_deg == rd.target_theta_y_deg
            assert rc.target_pixel_u == rd.target_pixel_u
            assert rc.target_pixel_v == rd.target_pixel_v

            # Disturbance telemetry MUST reflect actual disturbance state
            assert rd.disturbance_enabled is True
            assert rd.gaussian_enabled is True
            assert rd.gaussian_sigma == 20.0
            assert rd.salt_pepper_enabled is True
            assert rd.salt_pepper_probability == 0.10


class TestPresets:
    """Validation of all predefined disturbance presets."""

    @pytest.mark.parametrize(
        "preset_name",
        ["NOMINAL", "DIFFICULT", "SEVERE", "RECOVERY", "ADVERSARIAL", "CUSTOM"],
    )
    def test_preset_resolution_and_validation(self, preset_name):
        cfg = get_preset_config(preset_name)
        assert isinstance(cfg, DisturbanceConfig)
        # Should execute without error on 640x480 frame
        pipeline = DisturbancePipeline(cfg, SeedManager(seed=42))
        clean = np.full((480, 640), 128, dtype=np.uint8)
        out, telem = pipeline.apply(clean, sim_time=0.1, sim_dt=1/60.0)
        assert out.shape == (480, 640)
