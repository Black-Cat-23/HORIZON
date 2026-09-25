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


import cv2

def apply_atmospheric_degradation(
    frame: np.ndarray,
    config: AtmosphereConfig,
    rng: Optional[np.random.Generator] = None,
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
        rng: Optional random number generator for rain.

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
    if abs(contrast - 1.0) < 1e-9 and abs(brightness - 0.0) < 1e-9 and condition != "rain":
        return frame.copy(), contrast, brightness

    norm = frame.astype(np.float64) / 255.0
    degraded = norm * contrast + brightness
    clipped = np.clip(degraded, 0.0, 1.0) * 255.0
    out_frame = np.rint(clipped).astype(np.uint8)

    if condition == "rain":
        # Draw rain streaks
        if rng is None:
            rng = np.random.default_rng()
        
        # Num streaks depends on severity (0 to 1) -> let's say up to 200 streaks
        num_streaks = int(50 + 150 * config.severity)
        
        # Create an empty overlay for rain (black)
        rain_overlay = np.zeros_like(out_frame)
        h, w = out_frame.shape
        
        for _ in range(num_streaks):
            x1 = rng.integers(0, w)
            y1 = rng.integers(0, h)
            
            # length 10 to 20 px
            length = rng.integers(10, 21)
            
            # angle ~70-80 degrees from horizontal -> mostly vertical, slight tilt
            # let's say angle is drawn from normal(75, 5) degrees
            angle_deg = rng.normal(75.0, 5.0)
            angle_rad = np.radians(angle_deg)
            
            x2 = int(x1 + length * np.cos(angle_rad))
            y2 = int(y1 + length * np.sin(angle_rad))
            
            # streak intensity 150 to 255
            intensity = rng.integers(150, 256)
            
            cv2.line(rain_overlay, (x1, y1), (x2, y2), int(intensity), 1, cv2.LINE_AA)
            
        # Motion blur on the rain
        rain_overlay = cv2.blur(rain_overlay, (3, 3))
        
        # Alpha blend (rain is bright, so use screen/add or simple alpha)
        # alpha ~ 0.5 to 0.8 based on severity
        alpha = 0.5 + 0.3 * config.severity
        
        # Add overlay
        out_frame = cv2.addWeighted(out_frame, 1.0, rain_overlay, alpha, 0)

    return out_frame, contrast, brightness
