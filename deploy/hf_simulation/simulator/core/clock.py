"""
HORIZON Deterministic Simulation Clock
===============================================
Fixed-timestep clock that is completely independent of wall-clock time.
Produces identical results for identical configuration regardless of
execution speed, GUI frame rate, or system load.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


class FixedTimestepClock:
    """Deterministic fixed-timestep simulation clock.

    The clock advances in discrete, equal-sized steps determined solely
    by the configured simulation frequency. It has no dependency on
    wall-clock time, rendering speed, or any external timing source.

    Attributes:
        frequency_hz: Simulation update frequency in Hz.
        dt: Fixed timestep in seconds (1 / frequency_hz).
        current_frame: Current frame index (0-based).
        current_time: Current simulation time in seconds.
    """

    def __init__(self, frequency_hz: float) -> None:
        """Initialize the clock.

        Args:
            frequency_hz: Simulation frequency in Hz. Must be > 0.

        Raises:
            ValueError: If frequency_hz <= 0.
        """
        if frequency_hz <= 0:
            raise ValueError(
                f"frequency_hz must be > 0, got {frequency_hz}"
            )

        self._frequency_hz: float = frequency_hz
        self._dt: float = 1.0 / frequency_hz
        self._current_frame: int = 0
        self._current_time: float = 0.0

        logger.debug(
            "Clock initialized: frequency=%.1f Hz, dt=%.6f s",
            self._frequency_hz, self._dt,
        )

    @property
    def frequency_hz(self) -> float:
        """Simulation frequency in Hz."""
        return self._frequency_hz

    @property
    def dt(self) -> float:
        """Fixed timestep in seconds."""
        return self._dt

    @property
    def current_frame(self) -> int:
        """Current frame index (0-based)."""
        return self._current_frame

    @property
    def current_time(self) -> float:
        """Current simulation time in seconds."""
        return self._current_time

    def step(self) -> None:
        """Advance the clock by one fixed timestep.

        Increments the frame counter and accumulates time deterministically.
        Time is recomputed from frame * dt to avoid floating-point drift.
        """
        self._current_frame += 1
        # Recompute from frame index to prevent accumulated float error
        self._current_time = self._current_frame * self._dt

    def reset(self) -> None:
        """Reset the clock to initial state (frame 0, time 0.0)."""
        self._current_frame = 0
        self._current_time = 0.0
        logger.debug("Clock reset.")

    def __repr__(self) -> str:
        return (
            f"FixedTimestepClock(freq={self._frequency_hz}Hz, "
            f"frame={self._current_frame}, "
            f"time={self._current_time:.6f}s)"
        )
