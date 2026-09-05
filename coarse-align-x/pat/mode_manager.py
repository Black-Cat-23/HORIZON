"""
PAT Mode Manager & Finite State Machine.
HORIZON Phase 6
"""

from typing import Optional, Dict, Any, Tuple
from .state import PATMode, PATState
from .thresholds import PATThresholds
from .search.search_manager import SearchManager
from .acquisition.acquisition_manager import AcquisitionManager
from .tracking.track_manager import PATTrackManager
from .recovery.reacquisition import ReacquisitionManager
from .diagnostics.pat_diagnostics import PATDiagnostics


class PATModeManager:
    """
    Central PAT Mode Manager enforcing the exact state machine transition logic:
    SEARCH -> ACQUIRE -> TRACK -> DEGRADED -> REACQUIRE -> TRACK (or SEARCH)
    Zero ground truth leakage: state transitions are governed exclusively by 
    detector output, Kalman state estimate, track quality, and camera state.
    """

    def __init__(self, thresholds: Optional[PATThresholds] = None):
        self.thresholds = thresholds or PATThresholds()
        self.state = PATState()
        
        self.search_manager = SearchManager()
        self.acquisition_manager = AcquisitionManager(self.thresholds)
        self.track_manager = PATTrackManager()
        self.reacquisition_manager = ReacquisitionManager(self.thresholds)
        self.diagnostics = PATDiagnostics()

        # Initialize event
        self.diagnostics.log_event(
            timestamp_s=0.0,
            event_type="SEARCH_STARTED",
            old_state=PATMode.SEARCH,
            new_state=PATMode.SEARCH,
            reason="System initialization",
            track_quality=0.0,
        )

    def transition_to(self, new_mode: PATMode, timestamp_s: float, reason: str) -> None:
        if self.state.mode == new_mode:
            return

        old_mode = self.state.mode
        self.state.previous_mode = old_mode
        self.state.mode = new_mode
        self.state.mode_duration_s = 0.0
        self.state.mode_duration_frames = 0
        self.state.transition_reason = reason

        # Map state transition to event log
        event_map = {
            (PATMode.SEARCH, PATMode.ACQUIRE): "CANDIDATE_FOUND",
            (PATMode.ACQUIRE, PATMode.TRACK): "ACQUISITION_CONFIRMED",
            (PATMode.ACQUIRE, PATMode.SEARCH): "ACQUISITION_FAILED",
            (PATMode.TRACK, PATMode.DEGRADED): "TRACK_DEGRADED",
            (PATMode.DEGRADED, PATMode.TRACK): "TRACK_RESTORED",
            (PATMode.DEGRADED, PATMode.REACQUIRE): "TARGET_LOST",
            (PATMode.REACQUIRE, PATMode.ACQUIRE): "REACQUISITION_CANDIDATE",
            (PATMode.REACQUIRE, PATMode.SEARCH): "SEARCH_TIMEOUT",
        }
        event_type = event_map.get((old_mode, new_mode), f"TRANSITION_TO_{new_mode.value}")

        self.diagnostics.log_event(
            timestamp_s=timestamp_s,
            event_type=event_type,
            old_state=old_mode,
            new_state=new_mode,
            reason=reason,
            track_quality=self.state.track_quality,
        )

        # Reset managers upon mode entry
        if new_mode == PATMode.SEARCH:
            self.search_manager.reset_active_strategy(
                self.state.search_position_deg[0], self.state.search_position_deg[1]
            )
            self.acquisition_manager.reset()
            self.reacquisition_manager.reset()
        elif new_mode == PATMode.ACQUIRE:
            self.acquisition_manager.reset()
        elif new_mode == PATMode.REACQUIRE:
            self.reacquisition_manager.start_reacquisition(
                self.state.search_position_deg[0], self.state.search_position_deg[1]
            )

    def process_step(
        self,
        dt: float,
        timestamp_s: float,
        detection_valid: bool,
        detection_confidence: float,
        mahalanobis_d2: float,
        covariance_trace: float,
        estimated_u_px: float,
        estimated_v_px: float,
        estimated_vx_px_s: float,
        estimated_vy_px_s: float,
        current_pan_deg: float,
        current_tilt_deg: float,
        suppress_detection: bool = False,
    ) -> PATState:
        """
        Executes one PAT Mode Manager cycle.
        """
        # Apply controlled detection blackout test mode if active
        if suppress_detection:
            detection_valid = False
            detection_confidence = 0.0

        # Update durations
        self.state.mode_duration_s += dt
        self.state.mode_duration_frames += 1
        self.diagnostics.update_durations(dt, self.state.mode)

        # Hit / Miss tracking
        if detection_valid:
            self.state.consecutive_hits += 1
            self.state.consecutive_misses = 0
            self.state.time_since_last_measurement_s = 0.0
            self.state.prediction_only = False
        else:
            self.state.consecutive_hits = 0
            self.state.consecutive_misses += 1
            self.state.time_since_last_measurement_s += dt
            self.state.prediction_only = True

        # Calculate track quality
        self.state.track_quality = self.diagnostics.compute_track_quality(
            perception_confidence=detection_confidence,
            mahalanobis_d2=mahalanobis_d2,
            position_covariance_trace=covariance_trace,
            consecutive_misses=self.state.consecutive_misses,
        )

        # Compute pointing error in degrees from estimated target position
        pan_err, tilt_err = self.track_manager.compute_pointing_error(estimated_u_px, estimated_v_px)
        self.state.pan_error_deg = pan_err
        self.state.tilt_error_deg = tilt_err

        # Execute State Machine Transitions
        mode = self.state.mode

        if mode == PATMode.SEARCH:
            self.state.active_search_strategy = self.search_manager.active_strategy_name
            if detection_valid and detection_confidence >= self.thresholds.min_acquisition_confidence:
                self.transition_to(PATMode.ACQUIRE, timestamp_s, "Candidate detection observed during search")

        elif mode == PATMode.ACQUIRE:
            candidate_pos = (estimated_u_px, estimated_v_px) if detection_valid else None
            confirmed = self.acquisition_manager.process_frame(
                detection_valid, detection_confidence, mahalanobis_d2, candidate_pos
            )
            if confirmed:
                self.transition_to(PATMode.TRACK, timestamp_s, "N consecutive valid detections confirmed")
            elif not self.acquisition_manager.candidate_active and self.state.mode_duration_frames > 5:
                self.transition_to(PATMode.SEARCH, timestamp_s, "Acquisition candidate invalid or lost")

        elif mode == PATMode.TRACK:
            if self.state.consecutive_misses >= self.thresholds.degraded_miss_frames or self.state.track_quality < self.thresholds.min_track_quality:
                self.transition_to(PATMode.DEGRADED, timestamp_s, "Detection missed or track quality degraded")

        elif mode == PATMode.DEGRADED:
            if detection_valid and self.state.track_quality >= self.thresholds.min_track_quality:
                self.transition_to(PATMode.TRACK, timestamp_s, "Valid detection recovered")
            elif self.state.consecutive_misses >= self.thresholds.reacquire_trigger_frames:
                # Set reacquisition search center to predicted angle
                pred_pan_deg = current_pan_deg + pan_err
                pred_tilt_deg = current_tilt_deg + tilt_err
                self.state.search_position_deg = (pred_pan_deg, pred_tilt_deg)
                self.transition_to(PATMode.REACQUIRE, timestamp_s, "Persistent detection loss triggered reacquisition")

        elif mode == PATMode.REACQUIRE:
            self.state.active_search_strategy = "SPIRAL_REACQUIRE"
            if detection_valid and detection_confidence >= self.thresholds.min_acquisition_confidence:
                self.transition_to(PATMode.ACQUIRE, timestamp_s, "Candidate re-detected during reacquisition search")
            else:
                _, _, timed_out = self.reacquisition_manager.process_step(dt, current_pan_deg, current_tilt_deg)
                if timed_out or self.state.mode_duration_s >= self.thresholds.reacquire_timeout_s:
                    self.transition_to(PATMode.SEARCH, timestamp_s, "Reacquisition search timed out")

        return self.state
