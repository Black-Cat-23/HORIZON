"""
HORIZON Temporary Beacon Occlusion Engine
===========================================
Models temporary optical beacon occlusion events (e.g. cloud passage, structural blockage, solar panel transit).

Supports:
  - "complete" : Complete attenuation of the optical target region to background level
  - "partial"  : Partial attenuation / spatial masking across the beacon ROI

Timeline properties:
  - start_time_s : Exact simulation timestamp when occlusion event begins
  - duration_s   : Event active duration in seconds
  - severity     : Occlusion fraction in [0.0, 1.0]

Zero ground-truth contamination — modifies rendered optical image during event window.
"""

from __future__ import annotations

from typing import Tuple
import numpy as np

from simulator.disturbances.config import OcclusionConfig


class TemporaryOcclusionEngine:
    """Generates deterministic temporary target occlusion events.

    Parameters:
        config: OcclusionConfig dataclass.
    """

    def __init__(self, config: OcclusionConfig) -> None:
        self._config = config

    @property
    def config(self) -> OcclusionConfig:
        return self._config

    def is_active(self, sim_time: float) -> bool:
        """True if occlusion event is active at sim_time."""
        if not self._config.enabled or self._config.duration_s <= 0.0:
            return False
        t_start = self._config.start_time_s
        t_end = t_start + self._config.duration_s
        return t_start <= sim_time <= t_end

    def compute_attenuation(self, sim_time: float) -> float:
        """Compute instantaneous target attenuation factor (0.0 = full occlusion, 1.0 = clear)."""
        if not self.is_active(sim_time):
            return 1.0

        sev = max(0.0, min(1.0, self._config.severity))
        if self._config.type.lower() == "complete":
            return max(0.0, 1.0 - sev)
        else:  # partial
            # Soft smooth trapezoidal envelope over event duration
            t_rel = (sim_time - self._config.start_time_s) / self._config.duration_s
            # 10% ramp-in, 80% steady, 10% ramp-out
            if t_rel < 0.1:
                env = t_rel / 0.1
            elif t_rel > 0.9:
                env = (1.0 - t_rel) / 0.1
            else:
                env = 1.0
            return max(0.0, 1.0 - sev * env)

    def apply(self, frame: np.ndarray, sim_time: float, background_level: int = 0) -> Tuple[np.ndarray, float]:
        """Apply occlusion attenuation to an optical frame.

        Args:
            frame: 2D uint8 NumPy grayscale image.
            sim_time: Current simulation timestamp in seconds.
            background_level: Ambient background grayscale ADU.

        Returns:
            Tuple of (occluded_frame, realized_transmission_factor).
        """
        factor = self.compute_attenuation(sim_time)
        if abs(factor - 1.0) < 1e-6:
            return frame.copy(), 1.0

        bg = float(background_level)
        # Attenuate bright foreground pixels towards background level
        f_double = frame.astype(np.float64)
        occluded = bg + factor * (f_double - bg)
        out = np.clip(np.rint(occluded), 0, 255).astype(np.uint8)
        return out, factor
