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

    def step(self, frame: np.ndarray) -> Tuple[np.ndarray, float, float]:
        """Compute jitter displacement and apply image translation.

        Args:
            frame: 640×480 monochrome sensor frame.

        Returns:
            Tuple of (jittered_frame, jitter_x_px, jitter_y_px)
        """
        if not self._config.enabled:
            return frame.copy(), 0.0, 0.0

        max_x = min(float(self._config.max_x_px), 20.0)
        max_y = min(float(self._config.max_y_px), 20.0)

        if max_x <= 0.0 and max_y <= 0.0:
            return frame.copy(), 0.0, 0.0

        if self._config.distribution == "normal":
            # Zero-mean normal distribution with 3-sigma at max_px
            sigma_x = max_x / 3.0 if max_x > 0 else 0.0
            sigma_y = max_y / 3.0 if max_y > 0 else 0.0
            jx = float(self._rng.normal(0.0, sigma_x)) if sigma_x > 0 else 0.0
            jy = float(self._rng.normal(0.0, sigma_y)) if sigma_y > 0 else 0.0
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
