"""HORIZON Phase 11.3 Scenario Definitions & Data Models
======================================================
Defines the required 13 scenario configurations mapping directly to backend AppConfig instances.
Generates trajectory preview geometry mathematically from trajectory parameters.
"""

from __future__ import annotations
from dataclasses import dataclass, field
import math
from typing import List, Tuple

from simulator.core.config import (
    AppConfig,
    CircularTrajectoryConfig,
    FigureEightTrajectoryConfig,
    RandomTrajectoryConfig,
    SimulationConfig,
    SinusoidalTrajectoryConfig,
    SpiralTrajectoryConfig,
    StraightTrajectoryConfig,
    TargetConfig,
    TrajectoryConfig,
)
from simulator.disturbances.presets import get_preset_config


@dataclass
class ScenarioDefinition:
    scenario_id: str
    name: str  # Sentence case
    objective: str
    difficulty: str  # "Nominal", "Moderate", "Severe", "Adversarial", "Custom"
    param_summary: str
    config: AppConfig

    def generate_preview_path(self, num_points: int = 100) -> List[Tuple[float, float]]:
        """Generate static (x, y) world coordinates for preview rendering."""
        t_type = self.config.trajectory.type
        pts: List[Tuple[float, float]] = []

        if t_type == "straight":
            cfg = self.config.trajectory.straight
            x0, y0 = 1000.0, 1000.0
            vx, vy = cfg.velocity_x, cfg.velocity_y
            dt = 10.0 / num_points
            for i in range(num_points):
                t = i * dt
                pts.append((x0 + vx * t, y0 + vy * t))

        elif t_type == "circular":
            cfg = self.config.trajectory.circular
            cx, cy = cfg.center_x, cfg.center_y
            r = cfg.radius
            w = cfg.angular_velocity
            dt = (2.0 * math.pi / w) / num_points if w > 0 else 0.1
            for i in range(num_points):
                t = i * dt
                pts.append((cx + r * math.cos(w * t), cy + r * math.sin(w * t)))

        elif t_type == "figure8":
            cfg = self.config.trajectory.figure8
            cx, cy = cfg.center_x, cfg.center_y
            ax, ay = cfg.amplitude_x, cfg.amplitude_y
            w = cfg.angular_velocity
            dt = (2.0 * math.pi / w) / num_points if w > 0 else 0.1
            for i in range(num_points):
                t = i * dt
                pts.append((cx + ax * math.sin(w * t), cy + ay * math.sin(2.0 * w * t)))

        elif t_type == "sinusoidal":
            cfg = self.config.trajectory.sinusoidal
            x0, y0 = cfg.initial_x, cfg.initial_y
            vx = cfg.velocity_x
            amp = cfg.amplitude
            w = cfg.angular_velocity
            dt = 10.0 / num_points
            for i in range(num_points):
                t = i * dt
                pts.append((x0 + vx * t, y0 + amp * math.sin(w * t)))

        elif t_type == "spiral":
            cfg = self.config.trajectory.spiral
            cx, cy = cfg.center_x, cfg.center_y
            r0 = cfg.initial_radius
            rate = cfg.expansion_rate
            w = cfg.angular_velocity
            dt = 10.0 / num_points
            for i in range(num_points):
                t = i * dt
                r = r0 + rate * t
                pts.append((cx + r * math.cos(w * t), cy + r * math.sin(w * t)))

        else:  # Random or fallback
            cx, cy = 1000.0, 1000.0
            r = 150.0
            for i in range(num_points):
                angle = (i / num_points) * 2.0 * math.pi * 3.0
                pts.append((cx + (r + math.sin(i*0.5)*20.0) * math.cos(angle), cy + (r + math.sin(i*0.5)*20.0) * math.sin(angle)))

        return pts


def get_default_scenarios() -> List[ScenarioDefinition]:
    """Return the exact 13 required scenario definitions."""

    # Base AppConfig helper
    def make_config(traj_type: str, preset_name: str) -> AppConfig:
        f8_cfg = FigureEightTrajectoryConfig(amplitude_x=220.0, amplitude_y=140.0, angular_velocity=0.6)
        circ_cfg = CircularTrajectoryConfig(radius=150.0, angular_velocity=0.6)
        str_cfg = StraightTrajectoryConfig(velocity_x=120.0, velocity_y=40.0)
        rand_cfg = RandomTrajectoryConfig()

        traj_cfg = TrajectoryConfig(
            type=traj_type,
            figure8=f8_cfg if traj_type == "figure8" else FigureEightTrajectoryConfig(),
            circular=circ_cfg if traj_type == "circular" else CircularTrajectoryConfig(),
            straight=str_cfg if traj_type == "straight" else StraightTrajectoryConfig(),
            random=rand_cfg if traj_type == "random" else RandomTrajectoryConfig(),
        )

        return AppConfig(
            trajectory=traj_cfg,
            disturbance=get_preset_config(preset_name),
            simulation=SimulationConfig(frequency_hz=30.0, duration_seconds=30.0, seed=42),
            target=TargetConfig(size_px=10, intensity=255),
        )

    return [
        ScenarioDefinition(
            scenario_id="nominal_acq",
            name="Nominal acquisition",
            objective="Verify baseline optical acquisition and lock-on under zero disturbances.",
            difficulty="Nominal",
            param_summary="Target: 10px · Motion: Figure-8 · Disturbance: Nominal",
            config=make_config("figure8", "NOMINAL"),
        ),
        ScenarioDefinition(
            scenario_id="straight",
            name="Straight track",
            objective="Verify constant-velocity linear trajectory estimation and gimbal tracking.",
            difficulty="Nominal",
            param_summary="Target: 10px · Motion: Straight line · Disturbance: Nominal",
            config=make_config("straight", "NOMINAL"),
        ),
        ScenarioDefinition(
            scenario_id="circular",
            name="Circular track",
            objective="Verify radial centripetal acceleration tracking and phase lag response.",
            difficulty="Nominal",
            param_summary="Target: 10px · Motion: Circular · Disturbance: Nominal",
            config=make_config("circular", "NOMINAL"),
        ),
        ScenarioDefinition(
            scenario_id="figure8",
            name="Figure-8 track",
            objective="Verify dual-axis harmonic motion tracking with zero-velocity inflection points.",
            difficulty="Moderate",
            param_summary="Target: 10px · Motion: Figure-8 · Disturbance: Nominal",
            config=make_config("figure8", "NOMINAL"),
        ),
        ScenarioDefinition(
            scenario_id="random",
            name="Random track",
            objective="Verify stochastic maneuvering target tracking and Kalman process noise adaptation.",
            difficulty="Moderate",
            param_summary="Target: 10px · Motion: Random walk · Disturbance: Nominal",
            config=make_config("random", "NOMINAL"),
        ),
        ScenarioDefinition(
            scenario_id="low_light",
            name="Low light",
            objective="Test optical beacon detection under low photon flux and high shot noise.",
            difficulty="Moderate",
            param_summary="Target: 8px · Motion: Figure-8 · Disturbance: Low light",
            config=make_config("figure8", "RECOVERY"),
        ),
        ScenarioDefinition(
            scenario_id="fog_haze",
            name="Fog / haze",
            objective="Evaluate contrast reduction, scattering, and blurring from atmospheric haze.",
            difficulty="Moderate",
            param_summary="Target: 10px · Motion: Figure-8 · Disturbance: Haze",
            config=make_config("figure8", "DIFFICULT"),
        ),
        ScenarioDefinition(
            scenario_id="jitter",
            name="Camera jitter",
            objective="Assess high-frequency angular sensor jitter compensation by feedforward control.",
            difficulty="Moderate",
            param_summary="Target: 10px · Motion: Straight line · Disturbance: Jitter",
            config=make_config("straight", "DIFFICULT"),
        ),
        ScenarioDefinition(
            scenario_id="platform_motion",
            name="Platform motion",
            objective="Test moving vehicle mount dynamics and platform velocity disturbance rejection.",
            difficulty="Severe",
            param_summary="Target: 10px · Motion: Circular · Disturbance: Platform motion",
            config=make_config("circular", "SEVERE"),
        ),
        ScenarioDefinition(
            scenario_id="multi_distractor",
            name="Multi-distractor",
            objective="Verify clutter rejection and target data association in dense noise.",
            difficulty="Severe",
            param_summary="Target: 10px · Motion: Figure-8 · Disturbance: Severe noise",
            config=make_config("figure8", "SEVERE"),
        ),
        ScenarioDefinition(
            scenario_id="recovery",
            name="Disturbance recovery",
            objective="Verify PAT state machine reacquisition lifecycle during forced target blackout.",
            difficulty="Severe",
            param_summary="Target: 10px · Motion: Figure-8 · Disturbance: Recovery spiral",
            config=make_config("figure8", "RECOVERY"),
        ),
        ScenarioDefinition(
            scenario_id="severe_combined",
            name="Severe combined",
            objective="Stress test full system under max official noise, jitter, and platform motion.",
            difficulty="Adversarial",
            param_summary="Target: 10px · Motion: Figure-8 · Disturbance: Adversarial",
            config=make_config("figure8", "ADVERSARIAL"),
        ),
        ScenarioDefinition(
            scenario_id="custom",
            name="Custom",
            objective="User-defined experimental parameters across all trajectory and disturbance domains.",
            difficulty="Custom",
            param_summary="Target: User · Motion: Custom · Disturbance: Custom",
            config=make_config("figure8", "NOMINAL"),
        ),
    ]
