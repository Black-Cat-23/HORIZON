"""
Error Metrics Module
====================
Calculates pixel tracking error, RMSE, and angular pointing error in microradians.
"""

from __future__ import annotations
import math
from typing import Sequence
import numpy as np


class ErrorMetrics:
    """Calculates tracking error metrics and angular conversions."""

    @staticmethod
    def compute_rmse(errors: Sequence[float]) -> float:
        if not errors:
            return 0.0
        arr = np.array(errors, dtype=np.float64)
        return float(np.sqrt(np.mean(arr ** 2)))

    @staticmethod
    def pixel_to_microradians(pixel_error: float, fov_deg: float = 4.0, sensor_width_px: int = 640) -> float:
        fov_rad = math.radians(fov_deg)
        rad_per_px = fov_rad / sensor_width_px
        return pixel_error * rad_per_px * 1e6
