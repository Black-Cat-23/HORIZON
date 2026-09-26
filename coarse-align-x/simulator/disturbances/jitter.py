"""
HORIZON Camera Jitter Engine
===================================
Simulates optical line-of-sight image-plane high-frequency jitter disturbance.
Strictly conforms to official SIH26169 limits:
  - Maximum jitter: ±20.0 pixels per frame.
  - Does NOT alter ground truth target or camera gimbal state.
  - Uses isolated deterministic NumPy child generator.
"""

from __future__ import annotations

from typing import Tuple
import cv2
import numpy as np

from simulator.disturbances.config import CameraJitterConfig


class CameraJitterEngine:
    """Computes and applies image-plane high-frequency camera jitter disturbance.

    Parameters:
        config: Validated CameraJitterConfig.
        rng: Deterministic NumPy Generator child stream.
    """

    def __init__(self, config: CameraJitterConfig, rng: np.random.Generator) -> None:
        self._config = config
        self._rng = rng
        self._time_s: float = 0.0
        self._prev_colored_x: float = 0.0
        self._prev_colored_y: float = 0.0

    def step(self, frame: np.ndarray, dt: float = 1.0 / 60.0) -> Tuple[np.ndarray, float, float]:
        """Compute jitter displacement and apply image translation.

        Args:
            frame: 640×480 monochrome sensor frame.
            dt: Frame time delta in seconds (default 1/60s).

        Returns:
            Tuple of (jittered_frame, jitter_x_px, jitter_y_px)
        """
        if not self._config.enabled:
            return frame.copy(), 0.0, 0.0

        max_x = min(float(self._config.max_x_px), 20.0)
        max_y = min(float(self._config.max_y_px), 20.0)

        if max_x <= 0.0 and max_y <= 0.0:
            return frame.copy(), 0.0, 0.0

        self._time_s += float(dt)
        dist = str(self._config.distribution).lower()

        if dist == "normal":
            sigma_x = max_x / 3.0 if max_x > 0 else 0.0
            sigma_y = max_y / 3.0 if max_y > 0 else 0.0
            jx = float(self._rng.normal(0.0, sigma_x)) if sigma_x > 0 else 0.0
            jy = float(self._rng.normal(0.0, sigma_y)) if sigma_y > 0 else 0.0
        elif dist == "harmonic":
            freqs = self._config.harmonic_freqs or (18.0, 36.0, 72.0)
            amps = self._config.harmonic_amps or (2.5, 1.2, 0.6)
            jx = sum(a * np.sin(2.0 * np.pi * f * self._time_s) for f, a in zip(freqs, amps))
            jy = sum(a * np.cos(2.0 * np.pi * f * self._time_s + 0.4) for f, a in zip(freqs, amps))
        elif dist == "colored":
            # 1/f Pink noise approximation via AR(1) IIR filter (alpha = 0.85)
            alpha = 0.85
            white_x = float(self._rng.normal(0.0, max_x / 3.0))
            white_y = float(self._rng.normal(0.0, max_y / 3.0))
            self._prev_colored_x = alpha * self._prev_colored_x + (1.0 - alpha) * white_x
            self._prev_colored_y = alpha * self._prev_colored_y + (1.0 - alpha) * white_y
            jx = self._prev_colored_x
            jy = self._prev_colored_y
        elif dist == "mil_std_810g":
            # MIL-STD-810G composite: harmonic tones + random wideband PSD noise
            freqs = (15.0, 45.0, 120.0)
            amps = (max_x * 0.4, max_x * 0.25, max_x * 0.15)
            harmonic_x = sum(a * np.sin(2.0 * np.pi * f * self._time_s) for f, a in zip(freqs, amps))
            harmonic_y = sum(a * np.cos(2.0 * np.pi * f * self._time_s + 0.7) for f, a in zip(freqs, amps))
            rand_x = float(self._rng.normal(0.0, max_x * 0.2))
            rand_y = float(self._rng.normal(0.0, max_y * 0.2))
            jx = harmonic_x + rand_x
            jy = harmonic_y + rand_y
        else:
            # Uniform distribution in [-max_px, +max_px]
            jx = float(self._rng.uniform(-max_x, max_x)) if max_x > 0 else 0.0
            jy = float(self._rng.uniform(-max_y, max_y)) if max_y > 0 else 0.0

        # Strict clamping to official ±20.0 px limit
        jx = max(min(jx, 20.0), -20.0)
        jy = max(min(jy, 20.0), -20.0)

        # Apply image affine translation
        h, w = frame.shape[:2]
        m = np.array([[1.0, 0.0, jx], [0.0, 1.0, jy]], dtype=np.float32)
        jittered = cv2.warpAffine(
            frame,
            m,
            (w, h),
            flags=cv2.INTER_LINEAR,
            borderMode=cv2.BORDER_CONSTANT,
            borderValue=0,
        )

        return jittered, jx, jy
