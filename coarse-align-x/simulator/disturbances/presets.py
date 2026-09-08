"""
HORIZON Disturbance Presets & Adversarial Scenarios
===================================================
Predefined, fully-expanded disturbance configuration presets and adversarial scenario profiles:
  - NOMINAL: Clean baseline, zero disturbances
  - DIFFICULT: Moderate multi-source disturbances
  - SEVERE: High-intensity disturbances within official bounds
  - RECOVERY: Atmospheric loss / reacquisition scenario
  - ADVERSARIAL: Extreme boundary conditions (all official limits tested)
  - DISTRACTOR_BURST: False optical target burst event
  - OCCLUSION_EVENT: Temporary complete beacon occlusion
  - BRIGHTNESS_FADE: Deep optical scintillation / atmospheric fading event
  - JITTER_BURST: Transient high-amplitude structural jitter burst
  - PLATFORM_SWING: Large coupled platform motion surge
  - COMBINED_TURBULENCE: Beam wander + scintillation + haze + jitter simultaneously
  - CUSTOM: User-defined configuration
"""

from __future__ import annotations

from simulator.disturbances.config import (
    AtmosphereConfig,
    BeamWanderConfig,
    CameraJitterConfig,
    DistractorConfig,
    DisturbanceConfig,
    DisturbanceCorrelationConfig,
    GaussianNoiseConfig,
    InjectionScheduleConfig,
    IntensityFluctuationConfig,
    OcclusionConfig,
    PlatformMotionConfig,
    PoissonNoiseConfig,
    SaltPepperConfig,
)


def get_preset_config(name: str) -> DisturbanceConfig:
    """Retrieve an explicit, fully resolved DisturbanceConfig by preset name."""
    preset = name.upper()

    if preset == "NOMINAL":
        return DisturbanceConfig(
            enabled=False,
            salt_pepper=SaltPepperConfig(enabled=False, probability=0.0),
            gaussian=GaussianNoiseConfig(enabled=False, sigma=0.0),
            poisson=PoissonNoiseConfig(enabled=False, peak_photons=100.0),
            camera_jitter=CameraJitterConfig(enabled=False, max_x_px=0.0, max_y_px=0.0),
            platform_motion=PlatformMotionConfig(enabled=False, velocity_x=0.0, velocity_y=0.0),
            atmosphere=AtmosphereConfig(enabled=False, condition="clear"),
        )

    elif preset == "DIFFICULT":
        # Moderate multi-disturbance scenario (PROJECT DEFAULT values)
        return DisturbanceConfig(
            enabled=True,
            salt_pepper=SaltPepperConfig(enabled=True, probability=0.03),
            gaussian=GaussianNoiseConfig(enabled=True, sigma=6.0),
            poisson=PoissonNoiseConfig(enabled=True, peak_photons=80.0),
            camera_jitter=CameraJitterConfig(enabled=True, max_x_px=5.0, max_y_px=5.0),
            platform_motion=PlatformMotionConfig(
                enabled=True, model="linear", velocity_x=40.0, velocity_y=20.0
            ),
            atmosphere=AtmosphereConfig(enabled=True, condition="haze"),
        )

    elif preset == "SEVERE":
        # High intensity disturbances within official bounds (PROJECT DEFAULT values)
        return DisturbanceConfig(
            enabled=True,
            salt_pepper=SaltPepperConfig(enabled=True, probability=0.08),
            gaussian=GaussianNoiseConfig(enabled=True, sigma=15.0),  # <= 20
            poisson=PoissonNoiseConfig(enabled=True, peak_photons=30.0),
            camera_jitter=CameraJitterConfig(enabled=True, max_x_px=14.0, max_y_px=14.0),
            platform_motion=PlatformMotionConfig(
                enabled=True, model="linear", velocity_x=80.0, velocity_y=50.0
            ),
            atmosphere=AtmosphereConfig(enabled=True, condition="fog"),
        )

    elif preset == "RECOVERY":
        # Specific scenario for optical target fading and reacquisition
        return DisturbanceConfig(
            enabled=True,
            salt_pepper=SaltPepperConfig(enabled=False, probability=0.0),
            gaussian=GaussianNoiseConfig(enabled=True, sigma=8.0),
            poisson=PoissonNoiseConfig(enabled=False, peak_photons=50.0),
            camera_jitter=CameraJitterConfig(enabled=True, max_x_px=16.0, max_y_px=16.0),
            platform_motion=PlatformMotionConfig(
                enabled=True, model="linear", velocity_x=60.0, velocity_y=30.0
            ),
            atmosphere=AtmosphereConfig(enabled=True, condition="low_light"),
        )

    elif preset == "ADVERSARIAL":
        # Extreme boundary conditions enforcing official SIH maximums:
        return DisturbanceConfig(
            enabled=True,
            salt_pepper=SaltPepperConfig(enabled=True, probability=0.10),
            gaussian=GaussianNoiseConfig(enabled=True, sigma=20.0),  # OFFICIAL MAX
            poisson=PoissonNoiseConfig(enabled=True, peak_photons=20.0),
            camera_jitter=CameraJitterConfig(enabled=True, max_x_px=20.0, max_y_px=20.0),  # OFFICIAL MAX
            platform_motion=PlatformMotionConfig(
                enabled=True,
                model="linear",
                max_dx_px_per_frame=20.0,  # OFFICIAL MAX
                max_dy_px_per_frame=20.0,  # OFFICIAL MAX
                velocity_x=120.0,
                velocity_y=80.0,
            ),
            atmosphere=AtmosphereConfig(enabled=True, condition="rain"),
        )

    # -----------------------------------------------------------------------
    # Phase 3 Adversarial Scenario Profiles
    # -----------------------------------------------------------------------
    elif preset == "DISTRACTOR_BURST":
        return DisturbanceConfig(
            enabled=True,
            gaussian=GaussianNoiseConfig(enabled=True, sigma=5.0),
            distractors=DistractorConfig(enabled=True, type="multiple_spots", count=3, intensity=245),
            injection_schedule=InjectionScheduleConfig(enabled=True, injection_mode="pulsed", pulse_period_s=3.0),
        )

    elif preset == "OCCLUSION_EVENT":
        return DisturbanceConfig(
            enabled=True,
            gaussian=GaussianNoiseConfig(enabled=True, sigma=4.0),
            occlusion=OcclusionConfig(enabled=True, type="complete", start_time_s=1.5, duration_s=1.5, severity=1.0),
        )

    elif preset == "BRIGHTNESS_FADE":
        return DisturbanceConfig(
            enabled=True,
            intensity_fluctuation=IntensityFluctuationConfig(enabled=True, mode="mixed", depth=0.8, frequency_hz=3.0),
            atmosphere=AtmosphereConfig(enabled=True, condition="haze", severity=0.7),
        )

    elif preset == "JITTER_BURST":
        return DisturbanceConfig(
            enabled=True,
            camera_jitter=CameraJitterConfig(enabled=True, max_x_px=18.0, max_y_px=18.0, distribution="normal"),
            injection_schedule=InjectionScheduleConfig(enabled=True, injection_mode="pulsed", pulse_period_s=2.0, pulse_duty_cycle=0.4),
        )

    elif preset == "PLATFORM_SWING":
        return DisturbanceConfig(
            enabled=True,
            platform_motion=PlatformMotionConfig(enabled=True, model="linear", velocity_x=150.0, velocity_y=90.0),
            correlation=DisturbanceCorrelationConfig(enabled=True, platform_jitter_coupling=0.7),
        )

    elif preset == "COMBINED_TURBULENCE":
        return DisturbanceConfig(
            enabled=True,
            beam_wander=BeamWanderConfig(enabled=True, std_dev_px=3.5, correlation_time_s=0.4),
            intensity_fluctuation=IntensityFluctuationConfig(enabled=True, mode="mixed", depth=0.6, frequency_hz=8.0),
            atmosphere=AtmosphereConfig(enabled=True, condition="fog", severity=0.6),
            camera_jitter=CameraJitterConfig(enabled=True, max_x_px=8.0, max_y_px=8.0),
            gaussian=GaussianNoiseConfig(enabled=True, sigma=10.0),
        )

    elif preset == "CUSTOM":
        return DisturbanceConfig(enabled=True)

    raise ValueError(
        f"Unknown disturbance preset: '{name}'. "
        f"Valid presets: NOMINAL, DIFFICULT, SEVERE, RECOVERY, ADVERSARIAL, DISTRACTOR_BURST, OCCLUSION_EVENT, BRIGHTNESS_FADE, JITTER_BURST, PLATFORM_SWING, COMBINED_TURBULENCE, CUSTOM"
    )
