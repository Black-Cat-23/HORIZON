"""
HORIZON Temporal Intensity Fluctuation Engine
=============================================
Models time-varying optical beacon intensity fluctuations (scintillation & slow envelope fading).

Modes:
  - "slow"  : Low-frequency sinusoidal / drifting intensity envelope (f ~ 0.1-0.5 Hz)
  - "fast"  : High-frequency log-normal scintillation noise (f ~ 10-50 Hz)
  - "mixed" : Superposition of slow atmospheric envelope fading and fast scintillation

Math model:
  multiplier = 1.0 - depth * fade_factor
  I_eff(t) = clip(I0 * multiplier, 0, 255)

Zero ground-truth state contamination — acts purely on rendered optical frame intensities.
"""

from __future__ import annotations

import math
from typing import Tuple
import numpy as np

from simulator.disturbances.config import IntensityFluctuationConfig


class IntensityFluctuationEngine:
    """Generates deterministic temporal beacon intensity modulation.

    Parameters:
        config: IntensityFluctuationConfig dataclass.
        rng: Deterministic NumPy Random Generator stream.
    """

    def __init__(self, config: IntensityFluctuationConfig, rng: np.random.Generator) -> None:
        self._config = config
        self._rng = rng
        self._phase_slow: float = float(rng.uniform(0.0, 2.0 * math.pi))
        self._phase_fast: float = float(rng.uniform(0.0, 2.0 * math.pi))

    @property
    def config(self) -> IntensityFluctuationConfig:
        return self._config

    def compute_multiplier(self, sim_time: float) -> float:
        """Compute the instantaneous intensity scaling multiplier in [0.0, 1.0].

        Args:
            sim_time: Current simulation timestamp in seconds.

        Returns:
            Scalar multiplier factor (1.0 = full unattenuated intensity).
        """
        if not self._config.enabled or self._config.depth <= 0.0:
            return 1.0

        depth = min(1.0, max(0.0, self._config.depth))
        freq = self._config.frequency_hz
        mode = self._config.mode.lower()

        if mode == "slow":
            # Low-frequency smooth envelope
            w_slow = 2.0 * math.pi * (freq * 0.1)
            slow_val = 0.5 * (1.0 + math.sin(w_slow * sim_time + self._phase_slow))
            fade = slow_val

        elif mode == "fast":
            # High-frequency fast scintillation
            w_fast = 2.0 * math.pi * freq
            fast_val = 0.5 * (1.0 + math.sin(w_fast * sim_time + self._phase_fast))
            # Log-normal noise perturbation
            stoch = float(self._rng.lognormal(mean=0.0, sigma=0.15))
            fade = min(1.0, fast_val * stoch)

        else:  # mixed
            # Superposition: slow envelope x fast fluctuation
            w_slow = 2.0 * math.pi * (freq * 0.1)
            w_fast = 2.0 * math.pi * freq
            slow_val = 0.5 * (1.0 + math.sin(w_slow * sim_time + self._phase_slow))
            fast_val = 0.5 * (1.0 + math.sin(w_fast * sim_time + self._phase_fast))
            fade = 0.6 * slow_val + 0.4 * fast_val

        multiplier = max(0.0, min(1.0, 1.0 - depth * fade))
        return float(multiplier)

    def apply(self, frame: np.ndarray, sim_time: float) -> Tuple[np.ndarray, float]:
        """Apply temporal intensity modulation to a rendered grayscale optical frame.

        Args:
            frame: 2D uint8 NumPy grayscale image.
            sim_time: Current simulation timestamp in seconds.

        Returns:
            Tuple of (modulated_frame, realized_multiplier).
        """
        mult = self.compute_multiplier(sim_time)
        if abs(mult - 1.0) < 1e-6:
            return frame.copy(), 1.0

        modulated = np.clip(np.rint(frame.astype(np.float64) * mult), 0, 255).astype(np.uint8)
        return modulated, mult
