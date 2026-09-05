"""
HORIZON Beacon Model
============================
Optical beacon representation with subpixel geometric area-overlap rasterization.
"""

from __future__ import annotations

import math
from typing import Tuple
import numpy as np


class Beacon:
    """Optical beacon target representation.

    Parameters:
        target_id: Unique integer identifier.
        size_px: Square beacon edge length in pixels (valid range: 5–20).
        intensity: Optical peak intensity (0–255).
        shape: Beacon geometry ("square" for Phase 1).
    """

    def __init__(
        self,
        target_id: int = 1,
        size_px: float = 10.0,
        intensity: int = 255,
        shape: str = "square",
    ) -> None:
        if not (5.0 <= size_px <= 20.0):
            raise ValueError(f"Beacon size must be in range [5, 20], got {size_px}")
        if not (0 <= intensity <= 255):
            raise ValueError(f"Beacon intensity must be in range [0, 255], got {intensity}")
        if shape != "square":
            raise ValueError(f"Only 'square' shape supported in Phase 1, got '{shape}'")

        self._target_id = target_id
        self._size_px = float(size_px)
        self._intensity = int(intensity)
        self._shape = shape

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

    def render_into(
        self, frame: np.ndarray, x: float, y: float, background_level: int = 0
    ) -> None:
        """Rasterize the beacon into a 2D uint8 NumPy grayscale image with subpixel anti-aliasing.

        Uses exact analytical 2D box area-overlap integration so subpixel motion
        is rendered smoothly without aliasing artifacts.

        Args:
            frame: Target 2D NumPy array of shape (height, width), dtype uint8.
            x: Continuous center X coordinate in world pixels.
            y: Continuous center Y coordinate in world pixels.
            background_level: Ambient background grayscale value (0–255).
        """
        h, w = frame.shape[:2]
        half_s = self._size_px / 2.0

        # Exact continuous bounding box
        x_min = x - half_s
        x_max = x + half_s
        y_min = y - half_s
        y_max = y + half_s

        # Integer grid span of affected pixels
        col_start = max(0, int(math.floor(x_min)))
        col_end = min(w, int(math.ceil(x_max)))
        row_start = max(0, int(math.floor(y_min)))
        row_end = min(h, int(math.ceil(y_max)))

        if col_start >= col_end or row_start >= row_end:
            return  # Target is entirely outside frame

        # Compute 1D overlap along X and Y for affected pixel coordinates
        cols = np.arange(col_start, col_end, dtype=np.float64)
        rows = np.arange(row_start, row_end, dtype=np.float64)

        # Overlap in X: length of intersection between [col, col+1] and [x_min, x_max]
        overlap_x = np.clip(np.minimum(cols + 1.0, x_max) - np.maximum(cols, x_min), 0.0, 1.0)
        # Overlap in Y: length of intersection between [row, row+1] and [y_min, y_max]
        overlap_y = np.clip(np.minimum(rows + 1.0, y_max) - np.maximum(rows, y_min), 0.0, 1.0)

        # 2D outer product gives fraction of each pixel covered by the beacon
        coverage = np.outer(overlap_y, overlap_x)

        # Blend onto existing frame
        current_region = frame[row_start:row_end, col_start:col_end].astype(np.float64)
        target_val = float(self._intensity)
        blended = current_region + coverage * (target_val - current_region)

        frame[row_start:row_end, col_start:col_end] = np.clip(blended, 0.0, 255.0).astype(np.uint8)
