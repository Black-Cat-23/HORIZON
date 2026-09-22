"""
HORIZON Atmospheric Degradation Engine
=============================================
Mathematical atmospheric degradation model supporting official SIH26169 conditions:
  - CLEAR
  - HAZE
  - FOG
  - RAIN
  - LOW_LIGHT

Per SIH26169 specification, atmospheric degradation is defined as a reduction
in contrast and brightness. All preset numerical values are designated as
PROJECT DEFAULTS.
"""

from __future__ import annotations

from typing import Optional, Tuple
import cv2
import numpy as np

from simulator.disturbances.config import ATMOSPHERE_PRESETS, AtmosphereConfig


def apply_atmospheric_degradation(
    frame: np.ndarray,
    config: AtmosphereConfig,
) -> Tuple[np.ndarray, float, float]:
    """Apply atmospheric contrast and brightness reduction to an image frame.

    Degradation Model:
      normalized = frame / 255.0
      degraded   = normalized * contrast_factor + brightness_factor
      out        = clip(degraded, 0.0, 1.0) * 255.0

    For CLEAR: contrast_factor = 1.0, brightness_factor = 0.0 produces the exact
    unaltered input frame.

    Args:
        frame: Grayscale uint8 frame (480×640).
        config: AtmosphereConfig instance.

    Returns:
        Tuple of (degraded_frame, resolved_contrast_factor, resolved_brightness_factor)
    """
    if not config.enabled:
        return frame.copy(), 1.0, 0.0

    condition = config.condition.lower()
    defaults = ATMOSPHERE_PRESETS.get(condition, ATMOSPHERE_PRESETS["clear"])

    # Resolve contrast factor (user override takes precedence, else project default)
    contrast = (
        float(config.contrast_factor)
        if config.contrast_factor is not None
        else defaults["contrast_factor"]
    )

    # Resolve brightness offset factor
    brightness = (
        float(config.brightness_factor)
        if config.brightness_factor is not None
        else defaults["brightness_factor"]
    )

    # Fast path for identity (Clear with no overrides)
    if abs(contrast - 1.0) < 1e-9 and abs(brightness - 0.0) < 1e-9:
        return frame.copy(), contrast, brightness

    norm = frame.astype(np.float64) / 255.0
    degraded = norm * contrast + brightness
    clipped = np.clip(degraded, 0.0, 1.0) * 255.0
    return np.rint(clipped).astype(np.uint8), contrast, brightness


class KolmogorovPhaseScreenEngine:
    """Generates 2D Kolmogorov atmospheric turbulence phase screens.

    Uses Split-Step Fourier Method (SSFM) with Von Kármán spectrum modeling:
      Phi(k) = 0.023 * r0^(-5/3) * (k^2 + k0^2)^(-11/6) * exp(-k^2 / km^2)

    Attributes:
        r0_m: Fried parameter in meters (smaller r0 = stronger turbulence).
        cn2: Structure constant of refractive index fluctuations (m^-2/3).
    """

    def __init__(
        self,
        r0_m: float = 0.15,
        grid_size: int = 128,
        rng: Optional[np.random.Generator] = None,
    ) -> None:
        self.r0_m = max(0.01, float(r0_m))
        self.grid_size = grid_size
        self._rng = rng or np.random.default_rng(42)
        self._phase_screen: Optional[np.ndarray] = None
        self._generate_screen()

    def _generate_screen(self) -> None:
        """Generate static 2D Kolmogorov phase screen using spectral filtering."""
        N = self.grid_size
        kx = np.fft.fftfreq(N) * 2.0 * np.pi
        ky = np.fft.fftfreq(N) * 2.0 * np.pi
        k_x, k_y = np.meshgrid(kx, ky)
        k = np.sqrt(k_x**2 + k_y**2)
        k[0, 0] = 1e-6  # Prevent division by zero at DC

        # Von Kármán spatial spectrum
        L0 = 10.0  # Outer scale (meters)
        l0 = 0.005 # Inner scale (meters)
        k0 = 2.0 * np.pi / L0
        km = 5.92 / l0

        spectrum = 0.023 * (self.r0_m ** (-5.0 / 3.0)) * ((k**2 + k0**2) ** (-11.0 / 6.0)) * np.exp(-(k**2) / (km**2))
        spectrum[0, 0] = 0.0

        # Random complex Gaussian field
        white_noise = self._rng.normal(0.0, 1.0, (N, N)) + 1j * self._rng.normal(0.0, 1.0, (N, N))
        phase_freq = white_noise * np.sqrt(spectrum)
        phase_screen = np.real(np.fft.ifft2(phase_freq))
        self._phase_screen = (phase_screen - np.min(phase_screen)) / (np.ptp(phase_screen) + 1e-9)

    def apply_speckle_boiling(
        self,
        frame: np.ndarray,
        time_s: float,
        wind_speed_m_s: float = 5.0,
    ) -> np.ndarray:
        """Modulate frame wavefront intensity via dynamic drifting phase screen."""
        if self._phase_screen is None:
            return frame.copy()

        h, w = frame.shape[:2]
        shift_x = int((wind_speed_m_s * time_s * 20.0) % self.grid_size)
        shifted_screen = np.roll(self._phase_screen, shift_x, axis=1)

        screen_resized = cv2.resize(shifted_screen, (w, h), interpolation=cv2.INTER_CUBIC)
        speckle_modulation = 0.75 + 0.5 * screen_resized  # [0.75, 1.25] envelope

        degraded = frame.astype(np.float64) * speckle_modulation
        return np.clip(degraded, 0, 255).astype(np.uint8)
