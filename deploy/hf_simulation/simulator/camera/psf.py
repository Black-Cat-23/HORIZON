"""
HORIZON Point Spread Function (PSF) Model
==========================================
Parameterized optical PSF for beacon rendering.

Supported models:
  - "box"      : Exact area-overlap rasterization (default, identical to legacy Beacon.render_into)
  - "gaussian" : Analytical 2D Gaussian PSF with configurable sigma

All models are deterministic for a fixed configuration.
No randomness is introduced by the PSF itself.

Mathematical reference:
  Box:      I(x,y) = intensity × coverage(x,y)
            where coverage is the fraction of pixel (x,y) covered by the beacon square.

  Gaussian: I(x,y) = amplitude × intensity × exp(-r²/(2σ²)) + background_adu
            where r² = (x - x0)² + (y - y0)²
            Integrated flux matches the box model for fair comparison:
            amplitude = 1 / (2π σ²) × size_px²    [normalized]

Coordinate convention: image pixels (u,v) in IMAGE coordinate system.
See simulator/camera/coordinate_contract.py.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional

import numpy as np


# ---------------------------------------------------------------------------
# PSF Configuration
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class PSFConfig:
    """Point Spread Function configuration for beacon rendering.

    Attributes:
        model: PSF model name — "box" (default) or "gaussian".
        spot_sigma_px: Gaussian sigma in pixels. 0.0 = delta function (very sharp).
                       Only used when model="gaussian". Default 1.5 px.
        amplitude: Peak amplitude scale factor (1.0 = full input intensity).
                   Default 1.0.
        background_adu: Constant background ADU offset added to PSF region.
                        0.0 = no background pedestal. Default 0.0.
    """
    model: str = "box"
    spot_sigma_px: float = 1.5
    amplitude: float = 1.0
    background_adu: float = 0.0

    def __post_init__(self) -> None:
        if self.model not in ("box", "gaussian"):
            raise ValueError(
                f"PSF model must be 'box' or 'gaussian', got '{self.model}'"
            )
        if self.spot_sigma_px < 0.0:
            raise ValueError(
                f"spot_sigma_px must be >= 0, got {self.spot_sigma_px}"
            )
        if self.amplitude <= 0.0:
            raise ValueError(
                f"amplitude must be > 0, got {self.amplitude}"
            )
        if self.background_adu < 0.0:
            raise ValueError(
                f"background_adu must be >= 0, got {self.background_adu}"
            )


# ---------------------------------------------------------------------------
# PSF Engine
# ---------------------------------------------------------------------------

class PointSpreadFunction:
    """Renders a beacon optical source into a frame using the configured PSF model.

    Parameters:
        config: PSFConfig specifying model, sigma, amplitude, and background.
    """

    def __init__(self, config: Optional[PSFConfig] = None) -> None:
        self._config = config or PSFConfig()  # Default = box model

    @property
    def config(self) -> PSFConfig:
        return self._config

    @property
    def model(self) -> str:
        return self._config.model

    def apply(
        self,
        frame: np.ndarray,
        x: float,
        y: float,
        intensity: int,
        size_px: float,
    ) -> None:
        """Render a beacon into a frame using the configured PSF model.

        Modifies `frame` in-place (matching Beacon.render_into() contract).

        Args:
            frame: 2D uint8 NumPy array (height × width). Modified in-place.
            x: Continuous center X coordinate in world pixels.
            y: Continuous center Y coordinate in world pixels.
            intensity: Beacon peak intensity (0–255).
            size_px: Beacon square edge length in pixels (defines spatial extent).
        """
        if self._config.model == "box":
            self._apply_box(frame, x, y, intensity, size_px)
        elif self._config.model == "gaussian":
            self._apply_gaussian(frame, x, y, intensity, size_px)

    def _apply_box(
        self,
        frame: np.ndarray,
        x: float,
        y: float,
        intensity: int,
        size_px: float,
    ) -> None:
        """Box PSF: exact area-overlap rasterization (identical to legacy Beacon.render_into).

        This is the backward-compatible default — bit-for-bit identical output.
        """
        h, w = frame.shape[:2]
        half_s = size_px / 2.0

        x_min = x - half_s
        x_max = x + half_s
        y_min = y - half_s
        y_max = y + half_s

        col_start = max(0, int(math.floor(x_min)))
        col_end = min(w, int(math.ceil(x_max)))
        row_start = max(0, int(math.floor(y_min)))
        row_end = min(h, int(math.ceil(y_max)))

        if col_start >= col_end or row_start >= row_end:
            return

        cols = np.arange(col_start, col_end, dtype=np.float64)
        rows = np.arange(row_start, row_end, dtype=np.float64)

        overlap_x = np.clip(
            np.minimum(cols + 1.0, x_max) - np.maximum(cols, x_min), 0.0, 1.0
        )
        overlap_y = np.clip(
            np.minimum(rows + 1.0, y_max) - np.maximum(rows, y_min), 0.0, 1.0
        )

        coverage = np.outer(overlap_y, overlap_x)
        current_region = frame[row_start:row_end, col_start:col_end].astype(np.float64)
        target_val = float(intensity) * self._config.amplitude
        blended = current_region + coverage * (target_val - current_region)
        frame[row_start:row_end, col_start:col_end] = np.clip(blended, 0, 255).astype(np.uint8)

    def _apply_gaussian(
        self,
        frame: np.ndarray,
        x: float,
        y: float,
        intensity: int,
        size_px: float,
    ) -> None:
        """Gaussian PSF: 2D isotropic Gaussian centered at (x, y).

        Formula:
            G(r) = amplitude * intensity * exp(-r² / (2σ²)) + background_adu

        where σ = spot_sigma_px, r² = (col - x)² + (row - y)²

        Rendering extends over a bounding box of 3σ (99.7% of total flux).
        Background is added as a constant pedestal within the rendered region.
        """
        if self._config.spot_sigma_px < 1e-6:
            # Near-delta PSF: fall back to box model for stability
            self._apply_box(frame, x, y, intensity, size_px)
            return

        h, w = frame.shape[:2]
        sigma = self._config.spot_sigma_px
        amplitude = self._config.amplitude
        background = self._config.background_adu

        # Render extent: 3σ radius from center (captures 99.7% flux)
        render_radius = max(size_px / 2.0, 3.0 * sigma)
        col_start = max(0, int(math.floor(x - render_radius)))
        col_end = min(w, int(math.ceil(x + render_radius)))
        row_start = max(0, int(math.floor(y - render_radius)))
        row_end = min(h, int(math.ceil(y + render_radius)))

        if col_start >= col_end or row_start >= row_end:
            return

        # Coordinate grids centered at (x, y)
        cols = np.arange(col_start, col_end, dtype=np.float64) + 0.5  # pixel center
        rows = np.arange(row_start, row_end, dtype=np.float64) + 0.5

        dc = cols - x
        dr = rows - y
        r2 = dc[np.newaxis, :] ** 2 + dr[:, np.newaxis] ** 2

        # Gaussian values
        g = amplitude * float(intensity) * np.exp(-r2 / (2.0 * sigma ** 2)) + background

        # Blend with existing frame (don't go below background or above 255)
        current_region = frame[row_start:row_end, col_start:col_end].astype(np.float64)
        blended = np.maximum(current_region, g)  # Gaussian on top of background
        frame[row_start:row_end, col_start:col_end] = np.clip(blended, 0, 255).astype(np.uint8)

    def summary(self) -> str:
        """Return human-readable PSF model summary."""
        if self._config.model == "box":
            return (
                f"PointSpreadFunction [BOX]\n"
                f"  Exact area-overlap rasterization (backward compatible)\n"
                f"  amplitude={self._config.amplitude:.3f}"
            )
        else:
            return (
                f"PointSpreadFunction [GAUSSIAN]\n"
                f"  sigma={self._config.spot_sigma_px:.3f} px\n"
                f"  amplitude={self._config.amplitude:.3f}\n"
                f"  background={self._config.background_adu:.1f} ADU"
            )


# ---------------------------------------------------------------------------
# Pre-defined PSF presets
# ---------------------------------------------------------------------------

#: Default box PSF — backward compatible, identical to legacy Beacon.render_into()
BOX_PSF: PSFConfig = PSFConfig(model="box")

#: Narrow Gaussian — well-focused optical system (σ = 1.0 px)
NARROW_GAUSSIAN_PSF: PSFConfig = PSFConfig(model="gaussian", spot_sigma_px=1.0)

#: Moderate Gaussian — typical seeing-limited optical system (σ = 2.0 px)
MODERATE_GAUSSIAN_PSF: PSFConfig = PSFConfig(model="gaussian", spot_sigma_px=2.0)

#: Wide Gaussian with background pedestal — degraded optics simulation
DEGRADED_PSF: PSFConfig = PSFConfig(model="gaussian", spot_sigma_px=3.0, background_adu=5.0)

# Alias for backward compatibility
PSFModel = PointSpreadFunction


def render_psf(
    frame: np.ndarray,
    center_x: float,
    center_y: float,
    intensity: float,
    size_px: float,
    model: str = "box",
    sigma_px: float = 1.5,
    background_adu: float = 0.0,
) -> None:
    """Convenience function to render a beacon into frame using specified PSF parameters."""
    cfg = PSFConfig(
        model=model,
        spot_sigma_px=sigma_px,
        background_adu=background_adu,
    )
    psf = PointSpreadFunction(config=cfg)
    psf.apply(
        frame=frame,
        x=center_x,
        y=center_y,
        intensity=intensity,
        size_px=size_px,
    )
