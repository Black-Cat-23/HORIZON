"""
HORIZON Beacon Model
============================
Optical beacon representation with subpixel geometric area-overlap rasterization
and parameterized optical PSF support.
"""

from __future__ import annotations

import math
from typing import Optional, Tuple
import numpy as np

from simulator.camera.psf import render_psf, PSFModel


class Beacon:
    """Optical beacon target representation.

    Parameters:
        target_id: Unique integer identifier.
        size_px: Square beacon edge length in pixels (valid range: 5–20).
        intensity: Optical peak intensity (0–255).
        shape: Beacon geometry ("square" for Phase 1).
        psf_model: PSF model ('box' or 'gaussian').
        psf_sigma_px: Gaussian PSF sigma in pixels.
        psf_background_adu: Constant background ADU added during PSF rendering.
    """

    def __init__(
        self,
        target_id: int = 1,
        size_px: float = 10.0,
        intensity: int = 255,
        shape: str = "square",
        psf_model: str = "box",
        psf_sigma_px: float = 1.5,
        psf_background_adu: float = 0.0,
    ) -> None:
        if not (5.0 <= size_px <= 20.0):
            raise ValueError(f"Beacon size must be in range [5, 20], got {size_px}")
        if not (0 <= intensity <= 255):
            raise ValueError(f"Beacon intensity must be in range [0, 255], got {intensity}")
        if shape != "square":
            raise ValueError(f"Only 'square' shape supported in Phase 1, got '{shape}'")
        if psf_model not in ("box", "gaussian"):
            raise ValueError(f"psf_model must be 'box' or 'gaussian', got '{psf_model}'")

        self._target_id = target_id
        self._size_px = float(size_px)
        self._intensity = int(intensity)
        self._shape = shape
        self._psf_model = psf_model
        self._psf_sigma_px = float(psf_sigma_px)
        self._psf_background_adu = float(psf_background_adu)

    @property
    def target_id(self) -> int:
        return self._target_id

    @property
    def size_px(self) -> float:
        return self._size_px

    @property
    def intensity(self) -> int:
        return self._intensity

    @property
    def shape(self) -> str:
        return self._shape

    @property
    def psf_model(self) -> str:
        return self._psf_model

    @property
    def psf_sigma_px(self) -> float:
        return self._psf_sigma_px

    @property
    def psf_background_adu(self) -> float:
        return self._psf_background_adu

    def render_into(
        self,
        frame: np.ndarray,
        x: float,
        y: float,
        background_level: int = 0,
        psf_model: Optional[str] = None,
        psf_sigma_px: Optional[float] = None,
        psf_background_adu: Optional[float] = None,
    ) -> None:
        """Rasterize the beacon into a 2D uint8 NumPy grayscale image.

        Args:
            frame: Target 2D NumPy array of shape (height, width), dtype uint8.
            x: Continuous center X coordinate in world pixels.
            y: Continuous center Y coordinate in world pixels.
            background_level: Ambient background grayscale value (0–255).
            psf_model: Override default PSF model ('box' or 'gaussian').
            psf_sigma_px: Override default Gaussian sigma.
            psf_background_adu: Override default background ADU.
        """
        model = psf_model if psf_model is not None else self._psf_model
        sigma = psf_sigma_px if psf_sigma_px is not None else self._psf_sigma_px
        bg_adu = psf_background_adu if psf_background_adu is not None else self._psf_background_adu

        # Delegate to optical PSF module
        render_psf(
            frame=frame,
            center_x=x,
            center_y=y,
            intensity=float(self._intensity),
            size_px=self._size_px,
            model=model,
            sigma_px=sigma,
            background_adu=bg_adu,
        )
