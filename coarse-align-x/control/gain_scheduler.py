"""
PAT Mode and Confidence-Aware Gain Scheduler.
HORIZON — SIH 2026 PS SIH26169 (PDF Section 6.6)

Adapts PID gains (kp, ki, kd) and velocity feedforward (kff) dynamically based on
PAT operational mode (TRACK, ACQUIRE, DEGRADED, SEARCH, REACQUIRE) and real-time
track quality / estimation confidence.

Engineering Rationale:
- In TRACK: Tight response (high kp, active ki, tuned kd, active feedforward) minimizes pointing error.
- In ACQUIRE: Smooth pull-in response with gentle integral and increased damping to avoid overshoot.
- In DEGRADED: Relaxed kp, zero ki (freezes integrator against noise windup), and heavy kd damping
  so the gimbal does not chase transient sensor noise or outliers.
- In SEARCH / REACQUIRE: Closed-loop PID is disengaged; open-loop trajectory rates govern actuation.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional
import numpy as np

from pat.state import PATMode


@dataclass
class ScheduledGains:
    """Container for active controller gains."""
    kp: float
    ki: float
    kd: float
    kff: float = 0.0

    def to_dict(self) -> Dict[str, float]:
        return {
            "kp": self.kp,
            "ki": self.ki,
            "kd": self.kd,
            "kff": self.kff,
        }


class GainScheduler:
    """
    Gain scheduling engine that dynamically selects and modulates controller gains.
    """

    def __init__(
        self,
        kp_track: float = 1.5,
        ki_track: float = 0.08,
        kd_track: float = 0.12,
        kff_track: float = 0.6,
        kp_acquire: float = 1.0,
        ki_acquire: float = 0.02,
        kd_acquire: float = 0.18,
        kff_acquire: float = 0.3,
        kp_degraded: float = 0.45,
        ki_degraded: float = 0.0,
        kd_degraded: float = 0.28,
        kff_degraded: float = 0.0,
    ) -> None:
        self.gains_track = ScheduledGains(kp=kp_track, ki=ki_track, kd=kd_track, kff=kff_track)
        self.gains_acquire = ScheduledGains(kp=kp_acquire, ki=ki_acquire, kd=kd_acquire, kff=kff_acquire)
        self.gains_degraded = ScheduledGains(kp=kp_degraded, ki=ki_degraded, kd=kd_degraded, kff=kff_degraded)
        self.gains_inactive = ScheduledGains(kp=0.0, ki=0.0, kd=0.0, kff=0.0)

    def get_gains(
        self,
        mode: PATMode,
        track_quality: float = 0.0,
        continuous_interpolation: bool = False,
    ) -> ScheduledGains:
        """
        Retrieves scheduled gains for current PATMode.
        
        Args:
            mode: Current PAT operational mode.
            track_quality: Track quality metric in [0.0, 1.0].
            continuous_interpolation: If True and in TRACK mode, smoothly interpolates gains
                                      between DEGRADED and TRACK regimes based on track quality.
        """
        if mode in (PATMode.SEARCH, PATMode.REACQUIRE):
            return self.gains_inactive

        if mode == PATMode.ACQUIRE:
            return self.gains_acquire

        if mode == PATMode.DEGRADED:
            return self.gains_degraded

        if mode == PATMode.TRACK:
            if not continuous_interpolation or track_quality <= 0.0:
                return self.gains_track

            # Continuous modulation: interpolate between DEGRADED baseline and full TRACK gains
            # Transition region between track_quality = 0.3 (degraded boundary) and 0.8 (full lock)
            q = float(np.clip((track_quality - 0.3) / 0.5, 0.0, 1.0))
            
            kp = self.gains_degraded.kp + q * (self.gains_track.kp - self.gains_degraded.kp)
            ki = self.gains_degraded.ki + q * (self.gains_track.ki - self.gains_degraded.ki)
            kd = self.gains_degraded.kd - q * (self.gains_degraded.kd - self.gains_track.kd)
            kff = self.gains_degraded.kff + q * (self.gains_track.kff - self.gains_degraded.kff)

            return ScheduledGains(kp=kp, ki=ki, kd=kd, kff=kff)

        return self.gains_inactive

