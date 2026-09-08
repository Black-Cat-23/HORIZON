"""
HORIZON Disturbance Pipeline
===================================
Central orchestrator for the Phase 3 disturbance engine.
Enforces an explicit, testable, deterministic sequence of optical and sensor degradations:
  1. Platform Motion Stage (Continuous, stateful translation)
  2. Temporary Target Occlusion Stage (Partial / Complete cloud/structure blockage)
  3. Atmospheric Degradation Stage (Contrast & brightness reduction with continuous severity)
  4. Temporal Intensity Fluctuation Stage (Slow envelope + fast scintillation)
  5. False Optical Target Distractor Stage (Small spots, blobs, reflections, clusters)
  6. Sensor Noise Injection Stage:
     - Salt & Pepper impulse noise
     - Additive Gaussian noise (sigma <= 20 px)
     - Poisson photon shot noise
  7. Camera Jitter Stage (Zero-mean image-plane displacement <= ±20 px)
  8. Injection Scheduler Stage (Immediate, Ramped, Pulsed, Scheduled gain)
  9. Counterfactual Ablation (Seed-exact single-channel removal for ablation analysis)

All operations preserve the original clean sensor frame and never mutate
ground truth state.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
import numpy as np

from simulator.core.seed_manager import SeedManager
from simulator.disturbances.atmosphere import apply_atmospheric_degradation
from simulator.disturbances.config import DisturbanceConfig, validate_disturbance_config
from simulator.disturbances.correlation import DisturbanceCorrelationEngine
from simulator.disturbances.distractor import FalseTargetDistractorEngine
from simulator.disturbances.injection_scheduler import InjectionSchedulerEngine
from simulator.disturbances.intensity_fluctuation import IntensityFluctuationEngine
from simulator.disturbances.jitter import CameraJitterEngine
from simulator.disturbances.noise import (
    apply_gaussian_noise,
    apply_poisson_noise,
    apply_salt_and_pepper_noise,
)
from simulator.disturbances.occlusion import TemporaryOcclusionEngine
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
    # Phase 3 Extensions
    injection_gain: float = 1.0
    intensity_multiplier: float = 1.0
    occlusion_transmission: float = 1.0
    distractor_count: int = 0
    ablated_module: Optional[str] = None


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
        self._rng_intensity = seed_mgr.get_rng("intensity_fluctuation")
        self._rng_distractor = seed_mgr.get_rng("distractor")
        self._rng_correlation = seed_mgr.get_rng("correlation")

        # Sub-engines
        self._jitter_engine = CameraJitterEngine(config.camera_jitter, self._rng_jitter)
        self._platform_engine = PlatformMotionEngine(config.platform_motion, self._rng_platform)
        self._intensity_engine = IntensityFluctuationEngine(config.intensity_fluctuation, self._rng_intensity)
        self._occlusion_engine = TemporaryOcclusionEngine(config.occlusion)
        self._distractor_engine = FalseTargetDistractorEngine(config.distractors, self._rng_distractor)
        self._correlation_engine = DisturbanceCorrelationEngine(config.correlation, self._rng_correlation)
        self._scheduler_engine = InjectionSchedulerEngine(config.injection_schedule)

    @property
    def config(self) -> DisturbanceConfig:
        return self._config

    def reset(self) -> None:
        """Reset stateful disturbance engines."""
        self._platform_engine.reset()

    def apply(
        self,
        clean_frame: np.ndarray,
        sim_time: float,
        sim_dt: float,
        ablate_module: Optional[str] = None,
    ) -> Tuple[np.ndarray, DisturbanceTelemetry]:
        """Execute the disturbance pipeline on a clean 640×480 sensor frame.

        Args:
            clean_frame: Uncorrupted 640×480 uint8 camera frame.
            sim_time: Current simulation time in seconds.
            sim_dt: Timestep duration in seconds.
            ablate_module: Optional module name to skip for counterfactual ablation analysis.

        Returns:
            Tuple of (disturbed_frame, telemetry).
        """
        # Compute injection gain from scheduler
        injection_gain = self._scheduler_engine.compute_gain(sim_time)

        # If overall disturbance is disabled or injection gain is zero, return clean copy
        if not self._config.enabled or injection_gain <= 0.0:
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
                injection_gain=injection_gain,
                ablated_module=ablate_module,
            )
            return clean_frame.copy(), telemetry

        # Working copy for pipeline transformations
        frame = clean_frame.copy()

        # -------------------------------------------------------------
        # Stage 1: Platform Motion
        # -------------------------------------------------------------
        if ablate_module != "platform_motion":
            frame, p_ox, p_oy, p_vx, p_vy = self._platform_engine.step(
                frame=frame, dt=sim_dt, sim_time=sim_time
            )
        else:
            p_ox, p_oy, p_vx, p_vy = 0.0, 0.0, 0.0, 0.0

        # -------------------------------------------------------------
        # Stage 2: Temporary Occlusion
        # -------------------------------------------------------------
        if ablate_module != "occlusion":
            frame, transmission = self._occlusion_engine.apply(frame, sim_time)
        else:
            transmission = 1.0

        # -------------------------------------------------------------
        # Stage 3: Atmospheric Degradation
        # -------------------------------------------------------------
        if ablate_module != "atmosphere":
            frame, contrast_factor, brightness_factor = apply_atmospheric_degradation(
                frame=frame, config=self._config.atmosphere
            )
        else:
            contrast_factor, brightness_factor = 1.0, 0.0

        # -------------------------------------------------------------
        # Stage 4: Temporal Intensity Fluctuation
        # -------------------------------------------------------------
        if ablate_module != "intensity_fluctuation":
            frame, intensity_mult = self._intensity_engine.apply(frame, sim_time)
        else:
            intensity_mult = 1.0

        # -------------------------------------------------------------
        # Stage 5: False Optical Targets (Distractors)
        # -------------------------------------------------------------
        if ablate_module != "distractors":
            frame, distractor_cnt = self._distractor_engine.apply(frame, sim_dt)
        else:
            distractor_cnt = 0

        # -------------------------------------------------------------
        # Stage 6: Sensor Noise Injection
        # -------------------------------------------------------------
        # 6a. Salt & Pepper
        if ablate_module != "salt_pepper" and self._config.salt_pepper.enabled and self._config.salt_pepper.probability > 0.0:
            frame = apply_salt_and_pepper_noise(
                frame=frame,
                probability=self._config.salt_pepper.probability * injection_gain,
                rng=self._rng_sp,
            )

        # 6b. Gaussian Noise
        if ablate_module != "gaussian" and self._config.gaussian.enabled and self._config.gaussian.sigma > 0.0:
            frame = apply_gaussian_noise(
                frame=frame,
                sigma=self._config.gaussian.sigma * injection_gain,
                rng=self._rng_gauss,
            )

        # 6c. Poisson Shot Noise
        if ablate_module != "poisson" and self._config.poisson.enabled:
            frame = apply_poisson_noise(
                frame=frame,
                peak_photons=self._config.poisson.peak_photons,
                rng=self._rng_poisson,
            )

        # -------------------------------------------------------------
        # Stage 7: Camera Image-Plane Jitter
        # -------------------------------------------------------------
        if ablate_module != "camera_jitter":
            frame, jitter_x, jitter_y = self._jitter_engine.step(frame=frame)
        else:
            jitter_x, jitter_y = 0.0, 0.0

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
            injection_gain=injection_gain,
            intensity_multiplier=intensity_mult,
            occlusion_transmission=transmission,
            distractor_count=distractor_cnt,
            ablated_module=ablate_module,
        )

        return disturbed_frame, telemetry
