"""
HORIZON Cross-Channel Disturbance Correlation Engine
=====================================================
Supports independent vs. correlated stochastic disturbance channels.

Examples:
  - Platform motion correlated with camera jitter (mechanical coupling)
  - Brightness fluctuation correlated with atmospheric severity (optical fading)

Generates multivariate Gaussian random variables using Cholesky factorization.
Uncorrelated (independent) by default unless correlation coefficients > 0.
"""

from __future__ import annotations

import math
from typing import Tuple
import numpy as np

from simulator.disturbances.config import DisturbanceCorrelationConfig


class DisturbanceCorrelationEngine:
    """Generates cross-channel correlated stochastic noise streams.

    Parameters:
        config: DisturbanceCorrelationConfig dataclass.
        rng: Deterministic NumPy Random Generator.
    """

    def __init__(self, config: DisturbanceCorrelationConfig, rng: np.random.Generator) -> None:
        self._config = config
        self._rng = rng

    @property
    def config(self) -> DisturbanceCorrelationConfig:
        return self._config

    def sample_coupled_noise(self, coupling_coeff: float) -> Tuple[float, float]:
        """Sample two standard zero-mean unit-variance Gaussian variables (z1, z2) with correlation rho.

        Formula:
          z1 ~ N(0, 1)
          z2 = rho * z1 + sqrt(1 - rho²) * N(0, 1)

        Returns:
            Tuple of correlated samples (z1, z2).
        """
        rho = max(0.0, min(1.0, float(coupling_coeff)))
        z1 = float(self._rng.normal(0.0, 1.0))

        if rho < 1e-6:
            z2 = float(self._rng.normal(0.0, 1.0))
        else:
            w = float(self._rng.normal(0.0, 1.0))
            z2 = rho * z1 + math.sqrt(1.0 - rho ** 2) * w

        return z1, z2

    def get_coupled_platform_jitter_scale(self) -> Tuple[float, float]:
        """Get correlated scaling multipliers for platform motion and camera jitter."""
        if not self._config.enabled or self._config.platform_jitter_coupling <= 0.0:
            return 1.0, 1.0

        z1, z2 = self.sample_coupled_noise(self._config.platform_jitter_coupling)
        # Convert standard normal to positive scale factors around 1.0
        scale1 = max(0.2, 1.0 + 0.3 * z1)
        scale2 = max(0.2, 1.0 + 0.3 * z2)
        return scale1, scale2
