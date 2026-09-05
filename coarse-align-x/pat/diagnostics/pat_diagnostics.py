"""
PAT Diagnostics, Events, and Telemetry Evaluator.
HORIZON Phase 6
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import numpy as np
from ..state import PATMode


@dataclass
class PATEvent:
    """
    Log record for PAT state transitions and significant system events.
    """
    timestamp_s: float
    event_type: str
    old_state: PATMode
    new_state: PATMode
    reason: str
    track_quality: float
    details: Dict[str, Any] = field(default_factory=dict)


class PATDiagnostics:
    """
    Evaluator for PAT state metrics, event logging, track-quality scoring,
    acquisition times, reacquisition times, and lock retention ratio.
    """

    def __init__(self):
        self.events: List[PATEvent] = []
        self.search_start_time_s: Optional[float] = None
        self.first_track_time_s: Optional[float] = None
        self.target_lost_time_s: Optional[float] = None
        self.reacquisition_start_time_s: Optional[float] = None
        
        self.total_experiment_duration_s: float = 0.0
        self.total_tracking_duration_s: float = 0.0

    def log_event(
        self,
        timestamp_s: float,
        event_type: str,
        old_state: PATMode,
        new_state: PATMode,
        reason: str,
        track_quality: float,
        details: Optional[Dict[str, Any]] = None,
    ) -> PATEvent:
        event = PATEvent(
            timestamp_s=timestamp_s,
            event_type=event_type,
            old_state=old_state,
            new_state=new_state,
            reason=reason,
            track_quality=track_quality,
            details=details or {},
        )
        self.events.append(event)

        # Timers tracking
        if event_type == "SEARCH_STARTED" and self.search_start_time_s is None:
            self.search_start_time_s = timestamp_s
        elif event_type in ("ACQUISITION_CONFIRMED", "TRACK_STARTED") and self.first_track_time_s is None:
            self.first_track_time_s = timestamp_s
        elif event_type in ("TARGET_LOST", "REACQUISITION_STARTED"):
            self.target_lost_time_s = timestamp_s
            self.reacquisition_start_time_s = timestamp_s
        elif event_type in ("REACQUISITION_CONFIRMED", "TRACK_RESTORED"):
            pass

        return event

    def compute_track_quality(
        self,
        perception_confidence: float,
        mahalanobis_d2: float,
        position_covariance_trace: float,
        consecutive_misses: int,
    ) -> float:
        """
        Calculates a quantitative track-quality score Q_track in [0, 1].
        Formula:
          Q = w1 * c + w2 * max(0, 1 - d^2 / 16.0) + w3 * exp(-trace(P_pos) / 1000.0) + w4 * (1 / (1 + misses))
        """
        w1, w2, w3, w4 = 0.35, 0.25, 0.20, 0.20

        # Component 1: Detector confidence
        c_score = np.clip(perception_confidence, 0.0, 1.0)

        # Component 2: Innovation gate score
        d_score = np.clip(1.0 - (mahalanobis_d2 / 16.0), 0.0, 1.0)

        # Component 3: Covariance uncertainty score
        p_score = math_exp = float(np.exp(-np.clip(position_covariance_trace, 0.0, 10000.0) / 1000.0))

        # Component 4: Miss count score
        m_score = 1.0 / (1.0 + max(0, consecutive_misses))

        q_track = w1 * c_score + w2 * d_score + w3 * p_score + w4 * m_score
        return float(np.clip(q_track, 0.0, 1.0))

    def update_durations(self, dt: float, current_mode: PATMode) -> None:
        self.total_experiment_duration_s += dt
        if current_mode in (PATMode.TRACK, PATMode.DEGRADED):
            self.total_tracking_duration_s += dt

    def get_acquisition_time(self) -> Optional[float]:
        if self.search_start_time_s is not None and self.first_track_time_s is not None:
            return self.first_track_time_s - self.search_start_time_s
        return None

    def get_lock_retention_ratio(self) -> float:
        if self.total_experiment_duration_s <= 0.0:
            return 0.0
        return float(np.clip(self.total_tracking_duration_s / self.total_experiment_duration_s, 0.0, 1.0))
