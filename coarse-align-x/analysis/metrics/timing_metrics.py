"""
Timing Metrics Module
=====================
Calculates processing latencies and FPS.
"""

from __future__ import annotations
from typing import Sequence
import numpy as np


class TimingMetrics:
    """Calculates frame processing latency and frames-per-second."""

    @staticmethod
    def compute_fps(latency_ms: float) -> float:
        if latency_ms <= 0.0:
            return 0.0
        return 1000.0 / latency_ms
