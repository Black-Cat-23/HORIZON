"""
PAT (Pointing, Acquisition, Tracking) State and Enums.
HORIZON Phase 6
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Tuple, Dict, Any


class PATMode(Enum):
    """
    Strongly-typed enum for PAT system modes.
    """
    SEARCH = "SEARCH"
    ACQUIRE = "ACQUIRE"
    TRACK = "TRACK"
    DEGRADED = "DEGRADED"
    REACQUIRE = "REACQUIRE"


@dataclass
class PATState:
    """
    Current state container for the PAT Mode Manager.
    """
    mode: PATMode = PATMode.SEARCH
    previous_mode: PATMode = PATMode.SEARCH
    mode_duration_s: float = 0.0
    mode_duration_frames: int = 0
    consecutive_hits: int = 0
    consecutive_misses: int = 0
    track_quality: float = 0.0
    transition_reason: str = "INITIALIZATION"
    active_search_strategy: str = "NONE"
    search_position_deg: Tuple[float, float] = (0.0, 0.0)
    pan_error_deg: float = 0.0
    tilt_error_deg: float = 0.0
    commanded_pan_rate: float = 0.0
    commanded_tilt_rate: float = 0.0
    actual_pan_rate: float = 0.0
    actual_tilt_rate: float = 0.0
    is_saturated: bool = False
    prediction_only: bool = False
    track_age_s: float = 0.0
    time_since_last_measurement_s: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pat_state": self.mode.value,
            "previous_pat_state": self.previous_mode.value,
            "mode_duration_s": self.mode_duration_s,
            "mode_duration_frames": self.mode_duration_frames,
            "consecutive_hits": self.consecutive_hits,
            "consecutive_misses": self.consecutive_misses,
            "track_quality": self.track_quality,
            "transition_reason": self.transition_reason,
            "active_search_strategy": self.active_search_strategy,
            "search_position_deg": self.search_position_deg,
            "pan_error_deg": self.pan_error_deg,
            "tilt_error_deg": self.tilt_error_deg,
            "commanded_pan_rate": self.commanded_pan_rate,
            "commanded_tilt_rate": self.commanded_tilt_rate,
            "actual_pan_rate": self.actual_pan_rate,
            "actual_tilt_rate": self.actual_tilt_rate,
            "is_saturated": self.is_saturated,
            "prediction_only": self.prediction_only,
            "track_age_s": self.track_age_s,
            "time_since_last_measurement_s": self.time_since_last_measurement_s,
        }
