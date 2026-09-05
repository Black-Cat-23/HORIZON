"""
HORIZON Disturbance Pipeline
===================================
Central orchestrator for the Phase 3 disturbance engine.
Enforces an explicit, testable, deterministic sequence of optical and sensor degradations:
  1. Platform Motion Stage (Continuous, stateful translation)
  2. Atmospheric Degradation Stage (Contrast & brightness reduction)
  3. Sensor Noise Injection Stage:
     - Salt & Pepper impulse noise
     - Additive Gaussian noise (sigma <= 20 px)
     - Poisson photon shot noise
  4. Camera Jitter Stage (Zero-mean image-plane displacement <= ±20 px)

All operations preserve the original clean sensor frame and never mutate
ground truth state.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional, Tuple
import numpy as np

from simulator.core.seed_manager import SeedManager
from simulator.disturbances.atmosphere import apply_atmospheric_degradation
from simulator.disturbances.config import DisturbanceConfig, validate_disturbance_config
from simulator.disturbances.jitter import CameraJitterEngine
from simulator.disturbances.noise import (
    apply_gaussian_noise,
    apply_poisson_noise,
    apply_salt_and_pepper_noise,
)
from simulator.disturbances.platform import PlatformMotionEngine


@dataclass(frozen=True)
class DisturbanceTelemetry:
    """Per-frame disturbance execution telemetry."""
    disturbance_enabled: bool
    salt_pepper_enabled: bool
    salt_pepper_probability: float
    gaussian_enabled: bool
    gaussian_sigma: float
    poisson_enabled: bool
    poisson_parameter: float
    camera_jitter_enabled: bool
    camera_jitter_x: float
    camera_jitter_y: float
    platform_motion_enabled: bool
    platform_model: str
    platform_offset_x: float
    platform_offset_y: float
    platform_velocity_x: float
    platform_velocity_y: float
    atmosphere_enabled: bool
    atmosphere_condition: str
    contrast_factor: float
    brightness_factor: float


class DisturbancePipeline:
    """Orchestrates deterministic disturbance transformations on camera frames.

    Parameters:
        config: DisturbanceConfig dataclass.
        seed_mgr: SeedManager instance from Phase 1.
    """

    def __init__(self, config: DisturbanceConfig, seed_mgr: SeedManager) -> None:
        validate_disturbance_config(config)
        self._config = config
        self._seed_mgr = seed_mgr

        # Derive independent deterministic child RNG streams
        self._rng_sp = seed_mgr.get_rng("salt_pepper")
        self._rng_gauss = seed_mgr.get_rng("gaussian")
        self._rng_poisson = seed_mgr.get_rng("poisson")
        self._rng_jitter = seed_mgr.get_rng("jitter")
        self._rng_platform = seed_mgr.get_rng("platform")

        # Sub-engines
        self._jitter_engine = CameraJitterEngine(config.camera_jitter, self._rng_jitter)
        self._platform_engine = PlatformMotionEngine(config.platform_motion, self._rng_platform)

    @property
    def config(self) -> DisturbanceConfig:
        return self._config

    def reset(self) -> None:
        """Reset stateful disturbance engines (e.g. platform motion)."""
        self._platform_engine.reset()

    def apply(
        self,
        clean_frame: np.ndarray,
        sim_time: float,
        sim_dt: float,
    ) -> Tuple[np.ndarray, DisturbanceTelemetry]:
        """Execute the disturbance pipeline on a clean 640×480 sensor frame.

        Args:
            clean_frame: Uncorrupted 640×480 uint8 camera frame.
            sim_time: Current simulation time in seconds.
            sim_dt: Timestep duration in seconds.

        Returns:
            Tuple of:
              - disturbed_frame: 640×480 uint8 degraded frame
              - telemetry: DisturbanceTelemetry instance with exact metadata applied
        """
        # If overall disturbance is disabled, return clean copy with neutral telemetry
        if not self._config.enabled:
            telemetry = DisturbanceTelemetry(
                disturbance_enabled=False,
                salt_pepper_enabled=False,
                salt_pepper_probability=0.0,
                gaussian_enabled=False,
                gaussian_sigma=0.0,
                poisson_enabled=False,
                poisson_parameter=0.0,
                camera_jitter_enabled=False,
                camera_jitter_x=0.0,
                camera_jitter_y=0.0,
                platform_motion_enabled=False,
                platform_model=self._config.platform_motion.model,
                platform_offset_x=0.0,
                platform_offset_y=0.0,
                platform_velocity_x=0.0,
                platform_velocity_y=0.0,
                atmosphere_enabled=False,
                atmosphere_condition=self._config.atmosphere.condition,
                contrast_factor=1.0,
                brightness_factor=0.0,
            )
            return clean_frame.copy(), telemetry

        # Working copy for pipeline transformations
        frame = clean_frame.copy()

        # -------------------------------------------------------------
        # Stage 1: Platform Motion (Continuous Stateful Image Displacement)
        # -------------------------------------------------------------
        frame, p_ox, p_oy, p_vx, p_vy = self._platform_engine.step(
            frame=frame, dt=sim_dt, sim_time=sim_time
        )

        # -------------------------------------------------------------
        # Stage 2: Atmospheric Degradation (Contrast & Brightness Reduction)
        # -------------------------------------------------------------
        frame, contrast_factor, brightness_factor = apply_atmospheric_degradation(
            frame=frame, config=self._config.atmosphere
        )

        # -------------------------------------------------------------
        # Stage 3: Sensor Noise Injection
        # -------------------------------------------------------------
        # 3a. Salt & Pepper
        if self._config.salt_pepper.enabled and self._config.salt_pepper.probability > 0.0:
            frame = apply_salt_and_pepper_noise(
                frame=frame,
                probability=self._config.salt_pepper.probability,
                rng=self._rng_sp,
            )

        # 3b. Gaussian Noise (Additive N(0, sigma^2))
        if self._config.gaussian.enabled and self._config.gaussian.sigma > 0.0:
            frame = apply_gaussian_noise(
                frame=frame,
                sigma=self._config.gaussian.sigma,
                rng=self._rng_gauss,
            )

        # 3c. Poisson Shot Noise
        if self._config.poisson.enabled:
            frame = apply_poisson_noise(
                frame=frame,
                peak_photons=self._config.poisson.peak_photons,
                rng=self._rng_poisson,
            )

        # -------------------------------------------------------------
        # Stage 4: Camera Image-Plane Jitter (Zero-mean high frequency)
        # -------------------------------------------------------------
        frame, jitter_x, jitter_y = self._jitter_engine.step(frame=frame)

        # Ensure output invariants: strictly uint8 and 2D
        disturbed_frame = np.ascontiguousarray(frame, dtype=np.uint8)

        telemetry = DisturbanceTelemetry(
            disturbance_enabled=True,
            salt_pepper_enabled=self._config.salt_pepper.enabled,
            salt_pepper_probability=self._config.salt_pepper.probability,
            gaussian_enabled=self._config.gaussian.enabled,
            gaussian_sigma=self._config.gaussian.sigma,
            poisson_enabled=self._config.poisson.enabled,
            poisson_parameter=self._config.poisson.peak_photons,
            camera_jitter_enabled=self._config.camera_jitter.enabled,
            camera_jitter_x=jitter_x,
            camera_jitter_y=jitter_y,
            platform_motion_enabled=self._config.platform_motion.enabled,
            platform_model=self._config.platform_motion.model,
            platform_offset_x=p_ox,
            platform_offset_y=p_oy,
            platform_velocity_x=p_vx,
            platform_velocity_y=p_vy,
            atmosphere_enabled=self._config.atmosphere.enabled,
            atmosphere_condition=self._config.atmosphere.condition,
            contrast_factor=contrast_factor,
            brightness_factor=brightness_factor,
        )

        return disturbed_frame, telemetry
