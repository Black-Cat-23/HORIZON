"""
Event Metrics Module
====================
Calculates acquisition time, reacquisition time, and lock retention rates.
"""

from __future__ import annotations
from typing import Optional, Sequence
import numpy as np


class EventMetrics:
    """Calculates acquisition, reacquisition, and lock retention rates."""

    @staticmethod
    def compute_lock_retention(track_frames: int, eligible_frames: int) -> float:
        if eligible_frames <= 0:
            return 0.0
        return float(track_frames / eligible_frames)
