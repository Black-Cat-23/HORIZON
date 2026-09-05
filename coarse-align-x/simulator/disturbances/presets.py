"""
HORIZON Disturbance Presets
==================================
Predefined, fully-expanded disturbance configuration presets:
  - NOMINAL: Clean baseline, zero disturbances
  - DIFFICULT: Moderate multi-source disturbances
  - SEVERE: High-intensity disturbances within official bounds
  - RECOVERY: Atmospheric loss / reacquisition scenario
  - ADVERSARIAL: Extreme boundary conditions (all official limits tested)
  - CUSTOM: User-defined configuration

All non-official values are labelled PROJECT DEFAULTS.
"""

from __future__ import annotations

from simulator.disturbances.config import (
    AtmosphereConfig,
    CameraJitterConfig,
    DisturbanceConfig,
    GaussianNoiseConfig,
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
        # Gaussian sigma = 20.0, S&P = 0.10, Jitter = 20.0, Platform max = 20.0 px/frame
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

    elif preset == "CUSTOM":
        return DisturbanceConfig(enabled=True)

    raise ValueError(
        f"Unknown disturbance preset: '{name}'. "
        f"Valid presets: NOMINAL, DIFFICULT, SEVERE, RECOVERY, ADVERSARIAL, CUSTOM"
    )
