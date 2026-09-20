"""
HORIZON Dynamic Disturbance Injection Scheduler Engine
======================================================
Computes time-varying disturbance gain g(t) in [0.0, 1.0] for dynamic disturbance injection.

Supported Modes:
  - "immediate": Full disturbance active from start (g(t) = 1.0)
  - "ramped"   : Smooth linear transition from 0.0 to 1.0 over ramp_duration_s
  - "pulsed"   : Periodic square-wave burst injection (active during pulse_duty_cycle)
  - "scheduled": Active only after start_time_s
"""

from __future__ import annotations

import math
from simulator.disturbances.config import InjectionScheduleConfig


class InjectionSchedulerEngine:
    """Computes dynamic disturbance gain scaling g(t).

    Parameters:
        config: InjectionScheduleConfig dataclass.
    """

    def __init__(self, config: InjectionScheduleConfig) -> None:
        self._config = config

    @property
    def config(self) -> InjectionScheduleConfig:
        return self._config

    def compute_gain(self, sim_time: float) -> float:
        """Compute instantaneous disturbance injection gain multiplier in [0.0, 1.0].

        Args:
            sim_time: Current simulation timestamp in seconds.

        Returns:
            Disturbance gain multiplier (0.0 = completely suppressed, 1.0 = 100% active).
        """
        if not self._config.enabled or self._config.injection_mode == "immediate":
            return 1.0

        mode = self._config.injection_mode.lower()
        t_start = self._config.start_time_s

        if sim_time < t_start:
            return 0.0

        t_rel = sim_time - t_start

        if mode == "ramped":
            ramp = self._config.ramp_duration_s
            if ramp <= 0.0:
                return 1.0
            return max(0.0, min(1.0, t_rel / ramp))

        elif mode == "pulsed":
            period = max(0.1, self._config.pulse_period_s)
            duty = max(0.0, min(1.0, self._config.pulse_duty_cycle))
            cycle_pos = (t_rel % period) / period
            return 1.0 if cycle_pos <= duty else 0.0

        elif mode == "scheduled":
            return 1.0

        return 1.0
