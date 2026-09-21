"""
HORIZON Sensor Response Model
================================
Models electronic sensor response: exposure time and gain.

These are deterministic operations with no stochastic component.
They are applied to the clean optical frame before the disturbance pipeline.

Transfer functions:
  Exposure: I_out = clip(I_in * (exposure_ms / baseline_ms), 0, 255)
            baseline_ms = 1.0 ms reference exposure
            Over-exposure (exposure_ms > baseline_ms): brighter → saturation
            Under-exposure (exposure_ms < baseline_ms): darker

  Gain (dB): I_out = clip(I_in * G, 0, 255)
             G = 10^(gain_db / 20)   [voltage gain → linear amplitude]
             0 dB → G = 1.0 (unity, no change)
             +6 dB → G ≈ 2.0 (double amplitude)
             -6 dB → G ≈ 0.5 (half amplitude)

Application order: exposure first, then gain. Both are clipped to uint8.

Notes:
  - Exposure and gain both interact with saturation (255 ceiling) and dark floor (0).
  - These models do NOT include read noise or dark current.
    Those are sensor noise effects and belong in the disturbance pipeline.
  - The model is linear. Non-linear sensor response (gamma) is not modeled.
"""

from __future__ import annotations

import math

import numpy as np


class SensorResponse:
    """Applies exposure and gain to a clean sensor frame.

    Both operations are deterministic and require no random state.

    Parameters:
        exposure_ms: Sensor integration time in milliseconds (> 0).
                     1.0 ms = baseline (unity exposure).
        gain_db: Electronic gain in decibels.
                 0.0 dB = unity gain (no change).
                 Valid range: [-60, +60] dB.
        baseline_exposure_ms: Reference exposure for unity scaling (default 1.0 ms).
    """

    _MAX_GAIN_DB = 60.0  # Maximum valid gain dB
    _MIN_GAIN_DB = -60.0

    def __init__(
        self,
        exposure_ms: float = 1.0,
        gain_db: float = 0.0,
        baseline_exposure_ms: float = 1.0,
    ) -> None:
        if exposure_ms <= 0:
            raise ValueError(f"exposure_ms must be > 0, got {exposure_ms}")
        if not (self._MIN_GAIN_DB <= gain_db <= self._MAX_GAIN_DB):
            raise ValueError(
                f"gain_db must be in [{self._MIN_GAIN_DB}, {self._MAX_GAIN_DB}], got {gain_db}"
            )
        if baseline_exposure_ms <= 0:
            raise ValueError(
                f"baseline_exposure_ms must be > 0, got {baseline_exposure_ms}"
            )

        self._exposure_ms = float(exposure_ms)
        self._gain_db = float(gain_db)
        self._baseline_ms = float(baseline_exposure_ms)

        # Pre-compute linear gain factor
        self._gain_linear = 10.0 ** (self._gain_db / 20.0)
        self._exposure_scale = self._exposure_ms / self._baseline_ms
        self._combined_scale = self._exposure_scale * self._gain_linear

    @property
    def exposure_ms(self) -> float:
        return self._exposure_ms

    @property
    def gain_db(self) -> float:
        return self._gain_db

    @property
    def gain_linear(self) -> float:
        """Linear amplitude gain factor (voltage ratio: 10^(gain_db/20))."""
        return self._gain_linear

    @property
    def exposure_scale(self) -> float:
        """Exposure scale factor (exposure_ms / baseline_ms)."""
        return self._exposure_scale

    @property
    def combined_scale(self) -> float:
        """Combined scale factor = exposure_scale * gain_linear."""
        return self._combined_scale

    @property
    def is_unity(self) -> bool:
        """True if exposure and gain together produce no change (scale == 1.0)."""
        return abs(self._combined_scale - 1.0) < 1e-9

    def apply_exposure(self, frame: np.ndarray) -> np.ndarray:
        """Apply exposure scaling to a frame.

        I_out = clip(I_in * (exposure_ms / baseline_ms), 0, 255)

        Args:
            frame: 2D uint8 grayscale frame.

        Returns:
            Exposure-adjusted uint8 frame.
        """
        if abs(self._exposure_scale - 1.0) < 1e-9:
            return frame.copy()
        scaled = frame.astype(np.float64) * self._exposure_scale
        return np.clip(np.rint(scaled), 0, 255).astype(np.uint8)

    def apply_gain(self, frame: np.ndarray) -> np.ndarray:
        """Apply electronic gain to a frame.

        I_out = clip(I_in * G, 0, 255)  where G = 10^(gain_db/20)

        Args:
            frame: 2D uint8 grayscale frame.

        Returns:
            Gain-adjusted uint8 frame.
        """
        if abs(self._gain_linear - 1.0) < 1e-9:
            return frame.copy()
        scaled = frame.astype(np.float64) * self._gain_linear
        return np.clip(np.rint(scaled), 0, 255).astype(np.uint8)

    def apply(self, frame: np.ndarray) -> np.ndarray:
        """Apply exposure then gain to a frame (combined operation).

        Order: exposure → gain (both then clipped to uint8).
        Uses a single combined scale factor for efficiency.

        Args:
            frame: 2D uint8 grayscale frame.

        Returns:
            Adjusted uint8 frame.
        """
        if self.is_unity:
            return frame.copy()
        scaled = frame.astype(np.float64) * self._combined_scale
        return np.clip(np.rint(scaled), 0, 255).astype(np.uint8)

    def summary(self) -> str:
        """Return human-readable sensor response summary."""
        return (
            f"SensorResponse:\n"
            f"  exposure={self._exposure_ms:.3f} ms  "
            f"(baseline={self._baseline_ms:.3f} ms, scale={self._exposure_scale:.4f}x)\n"
            f"  gain={self._gain_db:+.2f} dB  (linear={self._gain_linear:.4f}x)\n"
            f"  combined_scale={self._combined_scale:.4f}x\n"
            f"  is_unity={self.is_unity}"
        )


def apply_sensor_response(
    frame: np.ndarray,
    exposure_ms: float = 1.0,
    gain_db: float = 0.0,
) -> np.ndarray:
    """Convenience function to apply exposure and gain to a sensor frame."""
    sr = SensorResponse(exposure_ms=exposure_ms, gain_db=gain_db)
    return sr.apply(frame)
