"""
HORIZON Phase 10B: Frame-Level Failure Forensics
=================================================
Detects tracking quality degradation or lock-loss events, classifies the
failure cause strictly from evidence available in PipelineMeasurementRecord,
and provides a frame inspection window (before / failure / after) for replay.

Strict Invariants:
  - Zero modification to HYBRID, IMM-EKF, PAT, or controller mathematics.
  - Zero alteration of source video frames.
  - Classification is evidence-based only — no guessing.
    If evidence is insufficient, category is UNKNOWN.
  - All thresholds are dynamic (derived from observed statistics) except for
    physics-based constants (e.g., Mahalanobis gate, image border margin).
"""

from __future__ import annotations

import collections
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Deque, Dict, List, Optional, Sequence, Tuple

import numpy as np

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────────────────
# 1. Failure Category Enum
# ──────────────────────────────────────────────────────────────────────────────

class FailureCategory(Enum):
    """Evidence-based failure classification categories.

    Only assigned when supporting evidence is present in the measurement record.
    UNKNOWN is reserved for cases where a failure condition is met but no
    specific category has sufficient evidence.
    """

    PERCEPTION_FAILURE      = "PERCEPTION_FAILURE"
    """Both classical and neural paths returned no valid detection."""

    MEASUREMENT_REJECTION   = "MEASUREMENT_REJECTION"
    """Measurement was detected but rejected by the estimator's innovation gate."""

    ESTIMATION_UNCERTAINTY  = "ESTIMATION_UNCERTAINTY"
    """State covariance trace exceeded a physically significant threshold."""

    TIMING_FAILURE          = "TIMING_FAILURE"
    """Frame dt deviated severely from the expected video frame period."""

    FOV_EXIT                = "FOV_EXIT"
    """Target lost while last known position was at or near the image boundary."""

    ACTUATOR_LIMIT          = "ACTUATOR_LIMIT"
    """Controller commanded rates saturated the actuator limits."""

    PAT_TRANSITION          = "PAT_TRANSITION"
    """PAT mode changed between consecutive frames (degradation transition)."""

    REACQUISITION_FAILURE   = "REACQUISITION_FAILURE"
    """PAT remained in REACQUIRE mode for an extended consecutive streak without recovery."""

    PROCESSING_OVERLOAD     = "PROCESSING_OVERLOAD"
    """End-to-end pipeline latency exceeded a significant threshold, indicating overload."""

    UNKNOWN                 = "UNKNOWN"
    """Failure condition detected but no single category has supporting evidence."""


# ──────────────────────────────────────────────────────────────────────────────
# 2. FailureEvent — immutable per-frame failure snapshot
# ──────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class FailureEvent:
    """Complete state snapshot at a frame where tracking quality degraded or lock was lost.

    Stores every field specified by HORIZON Phase 10B without modifying the
    underlying source data or PipelineMeasurementRecord.
    """

    frame_id: int
    """Sequential source video frame index."""

    timestamp: float
    """Authoritative video presentation timestamp (seconds)."""

    measurement: Optional[Tuple[float, float]]
    """Centroid measurement (u, v) in Common Frame space, or None if undetected."""

    confidence: float
    """Fused HYBRID detection confidence [0.0, 1.0]."""

    measurement_quality: Optional[Dict[str, Any]]
    """Candidate optical quality metrics dict (SNR, circularity, flux, etc.)."""

    estimate: Optional[Tuple[float, float]]
    """Filtered position estimate (x, y) in Common Frame pixels from IMM-EKF."""

    covariance: Optional[Any]
    """4×4 state covariance matrix (or None if estimator not engaged)."""

    innovation: Optional[Tuple[float, float]]
    """Estimator innovation residual (y_u, y_v) in pixels."""

    pat_state: Optional[str]
    """PAT mode string at failure frame (e.g. 'TRACK', 'DEGRADED', 'REACQUIRE')."""

    controller_command: Tuple[float, float]
    """Shadow pointing command (pan_rate_deg_s, tilt_rate_deg_s)."""

    latency_total_ms: float
    """End-to-end sensor-to-command latency in milliseconds for this frame."""

    fps_instantaneous: float
    """Instantaneous frames-per-second derived from video dt (not wall-clock)."""

    category: FailureCategory
    """Evidence-based failure category classification."""

    evidence: Dict[str, Any]
    """Dictionary of supporting evidence fields that justify the classification."""

    def to_dict(self) -> Dict[str, Any]:
        """Serialize failure event to a JSON-compatible dictionary."""
        return {
            "frame_id": self.frame_id,
            "timestamp": round(self.timestamp, 6),
            "measurement": (
                (round(self.measurement[0], 4), round(self.measurement[1], 4))
                if self.measurement is not None
                else None
            ),
            "confidence": round(self.confidence, 4),
            "measurement_quality": self.measurement_quality,
            "estimate": (
                (round(self.estimate[0], 4), round(self.estimate[1], 4))
                if self.estimate is not None
                else None
            ),
            "covariance": (
                self.covariance.tolist()
                if hasattr(self.covariance, "tolist")
                else self.covariance
            ),
            "innovation": (
                (round(self.innovation[0], 4), round(self.innovation[1], 4))
                if self.innovation is not None
                else None
            ),
            "pat_state": self.pat_state,
            "controller_command": {
                "pan_rate_deg_s": round(self.controller_command[0], 4),
                "tilt_rate_deg_s": round(self.controller_command[1], 4),
            },
            "latency_total_ms": round(self.latency_total_ms, 3),
            "fps_instantaneous": round(self.fps_instantaneous, 3),
            "category": self.category.value,
            "evidence": self.evidence,
        }


# ──────────────────────────────────────────────────────────────────────────────
# 3. ForensicWindow — inspection buffer around a failure frame
# ──────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class ForensicWindow:
    """Inspection window of PipelineMeasurementRecords surrounding a failure event.

    Source frames are NEVER modified. This is purely a reference window into
    the existing measurement record history.
    """

    event: FailureEvent
    """The failure event at the center of this inspection window."""

    frames_before: List[Any]  # List[PipelineMeasurementRecord]
    """Measurement records from frames immediately before the failure."""

    frames_after: List[Any]   # List[PipelineMeasurementRecord]
    """Measurement records from frames immediately after the failure (filled lazily)."""

    def summary(self) -> str:
        """Return a compact text summary of the forensic window."""
        lines = [
            f"[ForensicWindow] frame={self.event.frame_id} ts={self.event.timestamp:.3f}s "
            f"category={self.event.category.value}",
            f"  before={len(self.frames_before)} frames  after={len(self.frames_after)} frames",
            f"  confidence={self.event.confidence:.3f}  latency={self.event.latency_total_ms:.1f}ms",
            f"  evidence={self.event.evidence}",
        ]
        return "\n".join(lines)


# ──────────────────────────────────────────────────────────────────────────────
# 4. FailureClassifier — stateless, evidence-only classification
# ──────────────────────────────────────────────────────────────────────────────

# Physics-based constants (not tunable per-scenario)
_MAHALANOBIS_GATE: float = 9.0        # 3-sigma gate squared → √9 = 3σ
_BORDER_MARGIN_PX: float = 10.0       # px from image edge to consider boundary
_COMMON_FRAME_W: int = 640
_COMMON_FRAME_H: int = 480


class FailureClassifier:
    """Evidence-based failure category classifier.

    Stateless: given a record and contextual statistics, returns a category
    and a dict of supporting evidence. No guessing — UNKNOWN if no category fits.

    Args:
        mahalanobis_gate: Innovation gate threshold (default 3σ → 9.0 for squared distance).
        border_margin_px: Pixels from image edge considered boundary region.
        reacquire_streak_threshold: Consecutive REACQUIRE frames before classifying REACQUISITION_FAILURE.
        overload_multiplier: Factor above median latency to classify PROCESSING_OVERLOAD.
        dt_deviation_factor: Factor above median dt to classify TIMING_FAILURE.
    """

    def __init__(
        self,
        mahalanobis_gate: float = _MAHALANOBIS_GATE,
        border_margin_px: float = _BORDER_MARGIN_PX,
        reacquire_streak_threshold: int = 10,
        overload_multiplier: float = 3.0,
        dt_deviation_factor: float = 3.0,
    ) -> None:
        self._mahal_gate = mahalanobis_gate
        self._border_margin = border_margin_px
        self._reacq_threshold = reacquire_streak_threshold
        self._overload_mult = overload_multiplier
        self._dt_dev_factor = dt_deviation_factor

    def classify(
        self,
        record: Any,
        previous_record: Optional[Any] = None,
        median_total_ms: Optional[float] = None,
        median_dt: Optional[float] = None,
        reacquire_consecutive_count: int = 0,
        last_known_centroid: Optional[Tuple[float, float]] = None,
    ) -> Tuple[FailureCategory, Dict[str, Any]]:
        """Classify the failure category for a single frame record.

        Classification priority (first match wins):
          1. TIMING_FAILURE — frame timing anomaly invalidates all other evidence
          2. PROCESSING_OVERLOAD — pipeline overloaded
          3. PAT_TRANSITION — mode changed (degradation event)
          4. REACQUISITION_FAILURE — extended reacquire streak
          5. ACTUATOR_LIMIT — saturated commands
          6. MEASUREMENT_REJECTION — detected but gated out
          7. PERCEPTION_FAILURE — both paths null
          8. FOV_EXIT — lost while near image edge
          9. ESTIMATION_UNCERTAINTY — covariance diverged
         10. UNKNOWN — failure confirmed but no matching evidence

        Args:
            record: PipelineMeasurementRecord for the current frame.
            previous_record: Record from the immediately preceding frame.
            median_total_ms: Running median total latency for overload detection.
            median_dt: Running median dt for timing anomaly detection.
            reacquire_consecutive_count: How many consecutive REACQUIRE frames have elapsed.
            last_known_centroid: Last detected centroid before a miss (for FOV exit).

        Returns:
            Tuple of (FailureCategory, evidence_dict).
        """
        evidence: Dict[str, Any] = {}

        # ── TIMING_FAILURE ────────────────────────────────────────────────────
        if median_dt is not None and median_dt > 0 and record.dt > 0:
            ratio = record.dt / median_dt
            if ratio > self._dt_dev_factor or ratio < 1.0 / self._dt_dev_factor:
                evidence = {
                    "frame_dt_s": round(record.dt, 6),
                    "median_dt_s": round(median_dt, 6),
                    "dt_ratio": round(ratio, 3),
                    "threshold_factor": self._dt_dev_factor,
                }
                return FailureCategory.TIMING_FAILURE, evidence

        # ── PROCESSING_OVERLOAD ───────────────────────────────────────────────
        if median_total_ms is not None and median_total_ms > 0:
            lat_ms = (
                record.latency_breakdown_ms.get("total_ms", 0.0)
                if record.latency_breakdown_ms is not None
                else 0.0
            )
            if lat_ms > 0 and lat_ms > self._overload_mult * median_total_ms:
                evidence = {
                    "total_latency_ms": round(lat_ms, 3),
                    "median_latency_ms": round(median_total_ms, 3),
                    "overload_multiplier": self._overload_mult,
                }
                return FailureCategory.PROCESSING_OVERLOAD, evidence

        # ── PAT_TRANSITION ────────────────────────────────────────────────────
        if previous_record is not None:
            prev_pat = previous_record.pat_mode
            curr_pat = record.pat_mode
            if (
                prev_pat is not None
                and curr_pat is not None
                and prev_pat != curr_pat
                # Only degrade transitions count as failure events
                and curr_pat in ("DEGRADED", "REACQUIRE", "SEARCH")
            ):
                evidence = {
                    "previous_pat_mode": prev_pat,
                    "current_pat_mode": curr_pat,
                }
                return FailureCategory.PAT_TRANSITION, evidence

        # ── REACQUISITION_FAILURE ─────────────────────────────────────────────
        if (
            record.pat_mode == "REACQUIRE"
            and reacquire_consecutive_count >= self._reacq_threshold
        ):
            evidence = {
                "pat_mode": record.pat_mode,
                "consecutive_reacquire_frames": reacquire_consecutive_count,
                "threshold": self._reacq_threshold,
            }
            return FailureCategory.REACQUISITION_FAILURE, evidence

        # ── ACTUATOR_LIMIT ────────────────────────────────────────────────────
        if record.is_saturated:
            evidence = {
                "is_saturated": True,
                "commanded_pan_rate": round(record.commanded_pan_rate, 4),
                "commanded_tilt_rate": round(record.commanded_tilt_rate, 4),
            }
            return FailureCategory.ACTUATOR_LIMIT, evidence

        # ── MEASUREMENT_REJECTION ─────────────────────────────────────────────
        if (
            record.detected
            and record.innovation_mahalanobis is not None
            and record.innovation_mahalanobis > self._mahal_gate
        ):
            evidence = {
                "detected": True,
                "innovation_mahalanobis": round(record.innovation_mahalanobis, 4),
                "gate_threshold": self._mahal_gate,
                "innovation": (
                    (round(record.innovation[0], 4), round(record.innovation[1], 4))
                    if record.innovation is not None
                    else None
                ),
            }
            return FailureCategory.MEASUREMENT_REJECTION, evidence

        # ── PERCEPTION_FAILURE ────────────────────────────────────────────────
        if not record.detected:
            c_conf = record.classical_confidence or 0.0
            n_conf = record.neural_confidence or 0.0
            evidence = {
                "detected": False,
                "classical_confidence": round(c_conf, 4),
                "neural_confidence": round(n_conf, 4),
                "confidence": round(record.confidence, 4),
            }
            # ── FOV_EXIT  ─────────────────────────────────────────────────────
            # Sub-case: was the last known position at the image border?
            if last_known_centroid is not None:
                lx, ly = last_known_centroid
                near_left   = lx < self._border_margin
                near_right  = lx > (_COMMON_FRAME_W - self._border_margin)
                near_top    = ly < self._border_margin
                near_bottom = ly > (_COMMON_FRAME_H - self._border_margin)
                if near_left or near_right or near_top or near_bottom:
                    evidence["last_known_centroid"] = (round(lx, 2), round(ly, 2))
                    evidence["near_border"] = {
                        "left": near_left, "right": near_right,
                        "top": near_top, "bottom": near_bottom,
                    }
                    return FailureCategory.FOV_EXIT, evidence

            return FailureCategory.PERCEPTION_FAILURE, evidence

        # ── ESTIMATION_UNCERTAINTY ────────────────────────────────────────────
        if record.covariance is not None:
            try:
                cov_arr = np.asarray(record.covariance, dtype=float)
                if cov_arr.ndim == 2 and cov_arr.shape[0] >= 2:
                    pos_trace = float(cov_arr[0, 0] + cov_arr[1, 1])
                    # Threshold: position uncertainty > 50px 1-sigma (trace > 2500 px²)
                    _COV_TRACE_THRESHOLD = 2500.0
                    if pos_trace > _COV_TRACE_THRESHOLD:
                        evidence = {
                            "covariance_position_trace_px2": round(pos_trace, 2),
                            "threshold_px2": _COV_TRACE_THRESHOLD,
                            "sigma_pos_px": round(float(np.sqrt(pos_trace / 2.0)), 2),
                        }
                        return FailureCategory.ESTIMATION_UNCERTAINTY, evidence
            except Exception:
                pass

        # ── UNKNOWN ───────────────────────────────────────────────────────────
        # A failure condition was met (caller confirmed this), but no category
        # has enough evidence to be assigned definitively.
        evidence = {
            "note": "Failure condition met but insufficient evidence for specific category.",
            "confidence": round(record.confidence, 4),
            "detected": record.detected,
            "pat_mode": record.pat_mode,
        }
        return FailureCategory.UNKNOWN, evidence


# ──────────────────────────────────────────────────────────────────────────────
# 5. FailureForensicsEngine — stateful accumulator with rolling buffer
# ──────────────────────────────────────────────────────────────────────────────

class FailureForensicsEngine:
    """Stateful failure detection and forensic window engine.

    Maintains a rolling buffer of recent `PipelineMeasurementRecord`s.
    On each ingested frame, checks failure conditions and:
      - Creates a `FailureEvent` snapshot.
      - Stores a `ForensicWindow` with frames_before from the rolling buffer.
      - Lazily fills frames_after as subsequent records arrive.

    Args:
        window_before: Number of frames before failure to include in inspection window.
        window_after: Number of frames after failure to include in inspection window.
        classifier: FailureClassifier instance. Default uses physics-based constants.
        confidence_drop_threshold: Confidence below which detection is considered a failure.
        track_quality_degraded_threshold: PAT track_quality below which degradation is flagged.
    """

    def __init__(
        self,
        window_before: int = 10,
        window_after: int = 10,
        classifier: Optional[FailureClassifier] = None,
        confidence_drop_threshold: float = 0.3,
        track_quality_degraded_threshold: float = 0.4,
    ) -> None:
        self._window_before = max(1, window_before)
        self._window_after = max(1, window_after)
        self._classifier = classifier or FailureClassifier()
        self._confidence_threshold = confidence_drop_threshold
        self._quality_threshold = track_quality_degraded_threshold

        # Rolling buffer of recent records (capacity = window_before + 1)
        self._buffer: Deque[Any] = collections.deque(maxlen=self._window_before + 1)

        # Latency and dt statistics for dynamic threshold calibration
        self._latency_samples: List[float] = []
        self._dt_samples: List[float] = []

        # Consecutive REACQUIRE counter
        self._reacquire_streak: int = 0

        # Last confirmed centroid (for FOV exit classification)
        self._last_known_centroid: Optional[Tuple[float, float]] = None

        # Failure event storage
        self._events: List[FailureEvent] = []

        # Forensic windows (mutable during after-fill)
        self._windows: List[_MutableForensicWindow] = []

    # ── Public API ─────────────────────────────────────────────────────────────

    @property
    def events(self) -> List[FailureEvent]:
        """All detected failure events in chronological order."""
        return list(self._events)

    @property
    def forensic_windows(self) -> List[ForensicWindow]:
        """All completed forensic windows in chronological order."""
        return [w.to_frozen() for w in self._windows]

    def get_window_for(self, frame_id: int) -> Optional[ForensicWindow]:
        """Look up the forensic window for a specific failure frame_id."""
        for w in self._windows:
            if w.event.frame_id == frame_id:
                return w.to_frozen()
        return None

    def reset(self) -> None:
        """Clear all accumulated state."""
        self._buffer.clear()
        self._latency_samples.clear()
        self._dt_samples.clear()
        self._reacquire_streak = 0
        self._last_known_centroid = None
        self._events.clear()
        self._windows.clear()

    def ingest(self, record: Any) -> Optional[FailureEvent]:
        """Ingest one PipelineMeasurementRecord.

        Updates statistics, checks for failure conditions, and if a failure is
        detected, creates a FailureEvent and ForensicWindow.

        Args:
            record: Fully populated PipelineMeasurementRecord from the pipeline.

        Returns:
            FailureEvent if this frame is a failure frame, else None.
        """
        # Update calibration statistics
        if record.dt > 0:
            self._dt_samples.append(float(record.dt))
        if record.latency_breakdown_ms is not None:
            lat = record.latency_breakdown_ms.get("total_ms", 0.0)
            if lat > 0:
                self._latency_samples.append(float(lat))

        # Update consecutive REACQUIRE streak
        if record.pat_mode == "REACQUIRE":
            self._reacquire_streak += 1
        else:
            self._reacquire_streak = 0

        # Update last known centroid
        if record.detected and record.centroid is not None:
            self._last_known_centroid = record.centroid

        # Lazily fill after-frames for open forensic windows
        self._fill_after_frames(record)

        # Determine previous record from buffer tip
        previous_record = self._buffer[-1] if self._buffer else None

        # Add current record to the rolling buffer
        self._buffer.append(record)

        # ── Check failure conditions ──────────────────────────────────────────
        is_failure = self._is_failure_frame(record, previous_record)

        event: Optional[FailureEvent] = None
        if is_failure:
            median_dt = float(np.median(self._dt_samples)) if len(self._dt_samples) >= 3 else None
            median_lat = float(np.median(self._latency_samples)) if len(self._latency_samples) >= 3 else None

            category, evidence = self._classifier.classify(
                record=record,
                previous_record=previous_record,
                median_total_ms=median_lat,
                median_dt=median_dt,
                reacquire_consecutive_count=self._reacquire_streak,
                last_known_centroid=self._last_known_centroid if not record.detected else None,
            )

            fps_inst = (1.0 / record.dt) if record.dt > 0 else 0.0
            lat_total = (
                record.latency_breakdown_ms.get("total_ms", 0.0)
                if record.latency_breakdown_ms is not None
                else 0.0
            )

            event = FailureEvent(
                frame_id=record.frame_id,
                timestamp=record.timestamp,
                measurement=record.centroid,
                confidence=float(record.confidence),
                measurement_quality=record.candidate_quality,
                estimate=record.estimated_state,
                covariance=record.covariance,
                innovation=record.innovation,
                pat_state=record.pat_mode,
                controller_command=(
                    float(record.commanded_pan_rate),
                    float(record.commanded_tilt_rate),
                ),
                latency_total_ms=float(lat_total),
                fps_instantaneous=fps_inst,
                category=category,
                evidence=evidence,
            )

            self._events.append(event)

            # Build forensic window with before-frames from buffer
            # (buffer already contains the current record at tip; exclude it)
            frames_before = list(self._buffer)[:-1]  # All except the current (failure) frame
            mutable_window = _MutableForensicWindow(
                event=event,
                frames_before=frames_before,
                remaining_after=self._window_after,
            )
            self._windows.append(mutable_window)

            logger.warning(
                "[FORENSICS] frame=%d ts=%.3fs category=%s evidence=%s",
                record.frame_id,
                record.timestamp,
                category.value,
                evidence,
            )

        return event

    # ── Internal helpers ───────────────────────────────────────────────────────

    def _is_failure_frame(self, record: Any, previous_record: Optional[Any]) -> bool:
        """Return True if this frame constitutes a tracking quality failure.

        Failure conditions (any one is sufficient):
          1. Not detected (beacon lost).
          2. Confidence below threshold.
          3. PAT mode is DEGRADED, REACQUIRE, or SEARCH (not initial SEARCH).
          4. Estimator in REACQUIRE streak beyond threshold.
          5. Controller saturated.
          6. Measurement rejected (high Mahalanobis).
          7. PAT mode degraded from previous frame.
        """
        # 1. Beacon undetected
        if not record.detected:
            return True

        # 2. Low confidence
        if float(record.confidence) < self._confidence_threshold:
            return True

        # 3. PAT mode indicates degradation (not normal TRACK)
        if record.pat_mode in ("DEGRADED", "REACQUIRE"):
            return True

        # 4. REACQUIRE streak
        if self._reacquire_streak >= self._classifier._reacq_threshold:
            return True

        # 5. Actuator saturation
        if record.is_saturated:
            return True

        # 6. Measurement rejected by innovation gate
        if (
            record.detected
            and record.innovation_mahalanobis is not None
            and record.innovation_mahalanobis > self._classifier._mahal_gate
        ):
            return True

        # 7. PAT mode transitioned to a worse state
        if previous_record is not None:
            prev_pat = previous_record.pat_mode
            curr_pat = record.pat_mode
            if (
                prev_pat is not None
                and curr_pat is not None
                and prev_pat != curr_pat
                and curr_pat in ("DEGRADED", "REACQUIRE", "SEARCH")
            ):
                return True

        return False

    def _fill_after_frames(self, record: Any) -> None:
        """Append the current record to any open forensic windows awaiting after-frames."""
        for w in self._windows:
            if w.remaining_after > 0:
                w.frames_after.append(record)
                w.remaining_after -= 1


# ──────────────────────────────────────────────────────────────────────────────
# 6. Internal mutable window (converted to frozen ForensicWindow on access)
# ──────────────────────────────────────────────────────────────────────────────

class _MutableForensicWindow:
    """Internal mutable container for accumulating after-frames."""

    def __init__(
        self,
        event: FailureEvent,
        frames_before: List[Any],
        remaining_after: int,
    ) -> None:
        self.event = event
        self.frames_before: List[Any] = list(frames_before)
        self.frames_after: List[Any] = []
        self.remaining_after: int = remaining_after

    def to_frozen(self) -> ForensicWindow:
        return ForensicWindow(
            event=self.event,
            frames_before=list(self.frames_before),
            frames_after=list(self.frames_after),
        )
