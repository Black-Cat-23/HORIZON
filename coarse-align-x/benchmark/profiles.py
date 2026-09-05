"""
Algorithm Profiles Engine
=========================
Defines B0, B1, B2, and OURS baseline algorithm profiles and scenarios.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

from simulator.core.config import AppConfig, TrajectoryConfig, TargetConfig, SimulationConfig
from simulator.disturbances.config import (
    AtmosphereConfig,
    CameraJitterConfig,
    DisturbanceConfig,
    GaussianNoiseConfig,
    PlatformMotionConfig,
    PoissonNoiseConfig,
    SaltPepperConfig,
)


ALGORITHMS = ["B0", "B1", "B2", "OURS"]


@dataclass
class ScenarioPreset:
    """Pre-configured experiment scenarios."""

    scenario_id: str
    description: str
    trajectory_type: str
    target_size_px: int
    gaussian_sigma: float
    salt_pepper_amount: float
    jitter_sigma_px: float
    platform_motion: bool
    haze_factor: float
    distractor_count: int


SCENARIO_PRESETS: Dict[str, ScenarioPreset] = {
    "nominal": ScenarioPreset(
        scenario_id="nominal",
        description="Nominal clear conditions with minimal baseline noise",
        trajectory_type="circular",
        target_size_px=10,
        gaussian_sigma=2.0,
        salt_pepper_amount=0.0,
        jitter_sigma_px=0.5,
        platform_motion=False,
        haze_factor=0.0,
        distractor_count=0,
    ),
    "moderate": ScenarioPreset(
        scenario_id="moderate",
        description="Moderate atmospheric noise, sensor jitter, and distractor",
        trajectory_type="figure8",
        target_size_px=10,
        gaussian_sigma=10.0,
        salt_pepper_amount=0.01,
        jitter_sigma_px=2.0,
        platform_motion=True,
        haze_factor=0.2,
        distractor_count=1,
    ),
    "severe": ScenarioPreset(
        scenario_id="severe",
        description="Severe combined disturbances: high noise, rain/haze, jitter & distractors",
        trajectory_type="random",
        target_size_px=8,
        gaussian_sigma=20.0,  # Official max limit is 20.0
        salt_pepper_amount=0.04,
        jitter_sigma_px=4.5,
        platform_motion=True,
        haze_factor=0.5,
        distractor_count=2,
    ),
    "low_light": ScenarioPreset(
        scenario_id="low_light",
        description="Low light conditions with high background noise",
        trajectory_type="straight",
        target_size_px=6,
        gaussian_sigma=18.0,
        salt_pepper_amount=0.02,
        jitter_sigma_px=1.5,
        platform_motion=False,
        haze_factor=0.4,
        distractor_count=0,
    ),
}


def build_app_config_for_scenario(
    scenario_id: str,
    seed: int = 42,
    duration: float = 10.0,
    frequency: float = 60.0,
) -> AppConfig:
    """Build a resolved AppConfig object for a given scenario and seed."""
    preset = SCENARIO_PRESETS.get(scenario_id, SCENARIO_PRESETS["nominal"])

    simulation = SimulationConfig(
        frequency_hz=frequency,
        seed=seed,
        duration_seconds=duration,
    )
    target = TargetConfig(
        size_px=preset.target_size_px,
        intensity=255,
    )
    trajectory = TrajectoryConfig(type=preset.trajectory_type)

    # Reconstruct frozen disturbance dataclasses
    g_sigma = min(20.0, preset.gaussian_sigma)
    gaussian_cfg = GaussianNoiseConfig(enabled=g_sigma > 0, sigma=g_sigma)
    sp_cfg = SaltPepperConfig(enabled=preset.salt_pepper_amount > 0, probability=preset.salt_pepper_amount)
    jitter_cfg = CameraJitterConfig(
        enabled=preset.jitter_sigma_px > 0,
        max_x_px=min(20.0, preset.jitter_sigma_px),
        max_y_px=min(20.0, preset.jitter_sigma_px),
    )
    platform_cfg = PlatformMotionConfig(enabled=preset.platform_motion)
    atmo_cfg = AtmosphereConfig(enabled=preset.haze_factor > 0, condition="haze" if preset.haze_factor > 0 else "clear")

    disturbance = DisturbanceConfig(
        enabled=True,
        gaussian=gaussian_cfg,
        salt_pepper=sp_cfg,
        camera_jitter=jitter_cfg,
        platform_motion=platform_cfg,
        atmosphere=atmo_cfg,
    )

    base = AppConfig()

    return AppConfig(
        world=base.world,
        camera=base.camera,
        target=target,
        simulation=simulation,
        trajectory=trajectory,
        logging=base.logging,
        ground_truth=base.ground_truth,
        disturbance=disturbance,
    )


def get_algorithm_profile(algorithm: str) -> Dict[str, Any]:
    """Get component configurations for specified algorithm profile."""
    alg = algorithm.upper()
    if alg not in ALGORITHMS:
        raise ValueError(f"Unknown algorithm '{algorithm}'. Must be one of {ALGORITHMS}")

    if alg == "B0":
        return {
            "name": "B0",
            "description": "Naive open-loop baseline",
            "perception_engine": "NONE",
            "estimator_type": "NONE",
            "pat_mode": "OPEN_LOOP",
        }
    elif alg == "B1":
        return {
            "name": "B1",
            "description": "Classical threshold perception + Kalman filter + Baseline PAT",
            "perception_engine": "CLASSICAL",
            "estimator_type": "KALMAN",
            "pat_mode": "CLOSED_LOOP",
        }
    elif alg == "B2":
        return {
            "name": "B2",
            "description": "Neural YOLOv8n ONNX perception + Kalman filter + Baseline PAT",
            "perception_engine": "NEURAL",
            "estimator_type": "KALMAN",
            "pat_mode": "CLOSED_LOOP",
        }
    else:  # OURS
        return {
            "name": "OURS",
            "description": "Hybrid perception + Refinement + Kalman filter + Closed-Loop PAT",
            "perception_engine": "HYBRID",
            "estimator_type": "KALMAN",
            "pat_mode": "CLOSED_LOOP",
        }
