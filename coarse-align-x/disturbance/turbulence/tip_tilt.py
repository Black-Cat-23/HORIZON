import numpy as np
from typing import Tuple

from simulator.core.seed_manager import SeedManager
from .kolmogorov import tip_tilt_std_px, correlation_time, fried_parameter

class TipTiltEngine:
    """Generates correlated tip‑tilt offsets for each frame.

    The process is a first‑order autoregressive (AR(1)) Gaussian random walk:
        tt_k = tt_{k-1} * exp(-dt / tau) + N(0, sigma) * sqrt(1 - exp(-2*dt/tau))
    where sigma is the tip‑tilt standard deviation in pixels.
    """

    def __init__(self, config, seed_mgr: SeedManager, fov_deg: float, frame_width_px: int):
        self.enabled = config.enabled and config.tip_tilt_enabled
        self._config = config
        self._rng = seed_mgr.get_rng("turbulence_tip_tilt")
        self._prev = np.array([0.0, 0.0])
        self.fov_deg = fov_deg
        self.frame_width_px = frame_width_px
        # Pre‑compute parameters
        self._r0 = fried_parameter(config.cn2, config.wavelength_m, config.path_length_m)
        self._sigma_px = tip_tilt_std_px(
            r0_m=self._r0,
            aperture_m=config.aperture_diameter_m,
            wavelength_m=config.wavelength_m,
            fov_deg=fov_deg,
            frame_width_px=frame_width_px,
        )
        self._tau = (
            config.correlation_time_s
            if config.correlation_time_s is not None
            else correlation_time(self._r0, config.wind_speed_m_s)
        )

    def reset(self) -> None:
        self._prev = np.array([0.0, 0.0])

    def step(self, dt: float) -> Tuple[float, float]:
        """Return tip‑tilt offset (x_px, y_px) for the current frame.
        If disabled, returns (0.0, 0.0).
        """
        if not self.enabled:
            return 0.0, 0.0
        alpha = np.exp(-dt / self._tau)
        # generate independent Gaussian samples for x and y
        noise = self._rng.normal(0.0, self._sigma_px, size=2)
        current = self._prev * alpha + noise * np.sqrt(1 - alpha ** 2)
        self._prev = current
        return float(current[0]), float(current[1])

