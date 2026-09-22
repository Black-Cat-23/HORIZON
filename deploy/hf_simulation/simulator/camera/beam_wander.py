"""
HORIZON Beam-Wander Engine
============================
Models slow optical displacement of the apparent beacon centroid.

Physical interpretation:
  Optical beam-wander is a low-frequency spatial displacement of the
  apparent source position caused by thermally-induced index-of-refraction
  gradients along the optical path. It is:
    - Slower than camera jitter (< 1 Hz vs. ≥ 30 Hz)
    - Distinct from platform motion (which shifts the image globally)
    - Distinct from sensor noise (which adds per-pixel randomness)

This disturbance is modeled as an Ornstein-Uhlenbeck (OU) process:

    dx(t) = -theta * x(t) * dt + sigma * sqrt(dt) * N(0, 1)
    dy(t) = -theta * y(t) * dt + sigma * sqrt(dt) * N(0, 1)

Parameters:
    theta:  Mean-reversion rate [rad/s]. Controls time constant τ = 1/theta.
            Default: 0.1 rad/s → τ = 10 s (slow drift with 10-second memory).
    sigma:  RMS displacement amplitude [pixels]. Default: 1.0 px RMS.

Stationary distribution: N(0, sigma²/(2*theta)) per axis.
Expected amplitude: sigma_RMS = sigma / sqrt(2*theta).

The wander displacement (wander_x, wander_y) is in WORLD coordinates (pixels)
and is added to the target's true world position before rendering. This displaces
the apparent centroid from the true position without affecting ground truth.

Crucially:
  - Ground truth target position is NOT modified.
  - The wander is observable only in the rendered image.
  - Wander is separate from image-plane jitter and platform motion.

Coordinate convention: World pixels. +X right, +Y down.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class BeamWanderConfig:
    """Ornstein-Uhlenbeck beam-wander disturbance configuration.

    Attributes:
        enabled: Toggle beam-wander disturbance.
        sigma_px: RMS displacement amplitude in world pixels.
                  Must be >= 0. 0.0 = no wander.
        theta_rad_s: OU mean-reversion rate in rad/s.
                     Must be > 0. Larger = faster reversion (shorter memory).
    """
    enabled: bool = False
    sigma_px: float = 1.0
    theta_rad_s: float = 0.1   # τ = 1/theta = 10 s time constant

    def __post_init__(self) -> None:
        if self.sigma_px < 0:
            raise ValueError(f"sigma_px must be >= 0, got {self.sigma_px}")
        if self.theta_rad_s <= 0:
            raise ValueError(f"theta_rad_s must be > 0, got {self.theta_rad_s}")


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

class BeamWanderEngine:
    """Generates slow OU-process optical beam-wander displacement.

    The engine maintains stateful x and y wander values updated each
    simulation step. The wander is in world pixels.

    Parameters:
        config: BeamWanderConfig.
        rng: Deterministic NumPy Generator child stream.
    """

    def __init__(
        self,
        config: Optional[BeamWanderConfig] = None,
        rng: Optional[np.random.Generator] = None,
        std_dev_px: Optional[float] = None,
        correlation_time_s: Optional[float] = None,
    ) -> None:
        if config is None:
            sigma = std_dev_px if std_dev_px is not None else 1.0
            tau = correlation_time_s if correlation_time_s is not None else 0.5
            theta = 1.0 / tau if tau > 0 else 0.1
            config = BeamWanderConfig(enabled=True, sigma_px=sigma, theta_rad_s=theta)
        
        self._config = config
        self._rng = rng if rng is not None else np.random.default_rng()
        self._wander_x: float = 0.0
        self._wander_y: float = 0.0

    @property
    def wander_x(self) -> float:
        """Current horizontal wander displacement (world pixels)."""
        return self._wander_x

    @property
    def wander_y(self) -> float:
        """Current vertical wander displacement (world pixels)."""
        return self._wander_y

    @property
    def wander_magnitude(self) -> float:
        """Current wander magnitude (world pixels)."""
        return math.sqrt(self._wander_x ** 2 + self._wander_y ** 2)

    @property
    def stationary_rms(self) -> float:
        """Expected stationary RMS per axis: sigma / sqrt(2 * theta).

        This is the RMS amplitude at statistical equilibrium (long run).
        """
        return self._config.sigma_px / math.sqrt(2.0 * self._config.theta_rad_s)

    def step(self, dt: float) -> tuple[float, float]:
        """Advance beam-wander by one simulation step.

        Applies the OU update rule:
            x_new = x - theta * x * dt + sigma * sqrt(dt) * N(0, 1)

        Args:
            dt: Simulation timestep in seconds.

        Returns:
            (wander_x, wander_y): Current wander displacement in world pixels.
        """
        if not self._config.enabled or self._config.sigma_px < 1e-9:
            return 0.0, 0.0

        theta = self._config.theta_rad_s
        sigma = self._config.sigma_px
        sqrt_dt = math.sqrt(dt)

        # OU update
        noise_x = float(self._rng.standard_normal())
        noise_y = float(self._rng.standard_normal())

        self._wander_x = (
            self._wander_x - theta * self._wander_x * dt + sigma * sqrt_dt * noise_x
        )
        self._wander_y = (
            self._wander_y - theta * self._wander_y * dt + sigma * sqrt_dt * noise_y
        )

        return self._wander_x, self._wander_y

    def reset(self) -> None:
        """Reset wander to zero (boresight-aligned)."""
        self._wander_x = 0.0
        self._wander_y = 0.0

    def summary(self) -> str:
        """Return human-readable beam-wander state summary."""
        status = "ENABLED" if self._config.enabled else "DISABLED"
        tau = 1.0 / self._config.theta_rad_s
        return (
            f"BeamWanderEngine [{status}]\n"
            f"  sigma={self._config.sigma_px:.3f} px  "
            f"theta={self._config.theta_rad_s:.4f} rad/s  "
            f"tau={tau:.2f} s\n"
            f"  stationary_rms={self.stationary_rms:.3f} px/axis\n"
            f"  current: x={self._wander_x:.4f} px, y={self._wander_y:.4f} px  "
            f"mag={self.wander_magnitude:.4f} px"
        )
