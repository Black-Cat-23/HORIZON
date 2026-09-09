import numpy as np
from typing import Tuple

from simulator.core.seed_manager import SeedManager
from .kolmogorov import ryotv_variance

class ScintillationEngine:
    """Generates log‑normal intensity modulation factor per frame.

    For weak turbulence (σ_R^2 < 1) the intensity factor I = exp(X) where
    X ~ N(-σ_R^2/2, σ_R^2). The process follows a first‑order AR(1)
    correlation with time constant τ (same as tip‑tilt).
    """

    def __init__(self, config, seed_mgr: SeedManager):
        self.enabled = config.enabled and config.scintillation_enabled
        self._config = config
        self._rng = seed_mgr.get_rng("turbulence_scintillation")
        self._prev = None
        # Compute Rytov variance once
        self._sigma_R2 = ryotv_variance(
            cn2=config.cn2,
            wavelength_m=config.wavelength_m,
            path_length_m=config.path_length_m,
        )
        # Clamp for strong fluctuations per spec
        if self._sigma_R2 > config.strong_fluctuation_clamp:
            self._sigma_R2 = config.strong_fluctuation_clamp
        self._tau = (
            config.correlation_time_s
            if config.correlation_time_s is not None
            else correlation_time(
                fried_parameter(config.cn2, config.wavelength_m, config.path_length_m),
                config.wind_speed_m_s,
            )
        )
        # Pre‑compute distribution parameters
        self._mu = -0.5 * self._sigma_R2
        self._sigma = np.sqrt(self._sigma_R2)

    def reset(self) -> None:
        self._prev = None

    def factor(self, dt: float) -> float:
        """Return multiplicative scintillation factor for the current frame.
        If disabled, returns 1.0.
        """
        if not self.enabled:
            return 1.0
        if self._prev is None:
            # initialize from stationary distribution
            self._prev = self._rng.normal(self._mu, self._sigma)
            return float(np.exp(self._prev))
        alpha = np.exp(-dt / self._tau)
        noise = self._rng.normal(0.0, self._sigma)
        self._prev = self._prev * alpha + noise * np.sqrt(1 - alpha ** 2)
        return float(np.exp(self._prev))

