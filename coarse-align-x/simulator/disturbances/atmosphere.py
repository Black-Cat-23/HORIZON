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
