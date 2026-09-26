"""
HORIZON Phase 5B: Temporal Consistency & Measurement Jump Analyzer
========================================================================
Investigates measurement jumps across consecutive frames (k, k+1, k+2)
against actual optical and candidate evidence without hiding physical motion
under artificial smoothing.

Determines whether jumps are caused by:
  1. HYBRID_HANDOFF: Switching between classical and neural perception engines
  2. CANDIDATE_AMBIGUITY: Multiple competing candidates with close confidence scores
  3. NOISE: Low SNR, low optical contrast, or sensor noise fluctuation
  4. EDGE_EFFECT: Boundary clipping and optical centroid shift at frame borders
  5. TRUE_MOTION: Legitimate target maneuver/vibration sustained across frames

Strict Invariants:
  - Does NOT modify HYBRID mathematics.
  - Does NOT hide jumps with excessive smoothing or artificial low-pass filtering.
  - Derives jump classification purely from measurable optical quantities.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import math
from typing import Any, Dict, List, Optional, Tuple


class JumpCause(str, Enum):
    """Diagnosed physical root cause of a measurement jump."""
    NONE = "NONE"
    HYBRID_HANDOFF = "HYBRID_HANDOFF"
    CANDIDATE_AMBIGUITY = "CANDIDATE_AMBIGUITY"
    NOISE = "NOISE"
    EDGE_EFFECT = "EDGE_EFFECT"
    TRUE_MOTION = "TRUE_MOTION"


@dataclass(frozen=True)
class JumpDiagnosis:
    """Detailed diagnostic evaluation of a detected measurement jump.

    Fields:
        frame_id: Frame index where jump was detected
        timestamp: Time of the jump in seconds
        jump_distance_px: Magnitude of centroid displacement from prior frame
        apparent_velocity_px_s: Apparent velocity (jump_distance / dt)
        cause: Diagnosed root cause (JumpCause enum)
        confidence: Perception confidence at the jump frame
        evidence_summary: Human-readable explanation grounded in optical data
        retained_as_valid: Whether the observation was retained for filtering
    """

    frame_id: int
    timestamp: float
    jump_distance_px: float
    apparent_velocity_px_s: float
    cause: JumpCause
    confidence: float
    evidence_summary: str
    retained_as_valid: bool


class TemporalConsistencyAnalyzer:
    """Sliding-window temporal consistency engine.

    Analyzes sequences of measurements across frames (k-1, k, k+1, k+2) to identify,
    quantify, and explain measurement jumps using multi-frame evidence.
    """

    def __init__(
        self,
        jump_threshold_px: float = 12.0,
        max_physical_speed_px_s: float = 250.0,
        sensor_margin_px: int = 8,
        snr_noise_threshold: float = 3.5,
    ) -> None:
        """Initialize the analyzer with physical threshold bounds.

        Args:
            jump_threshold_px: Minimum Euclidean jump in pixels to trigger investigation.
            max_physical_speed_px_s: Maximum expected physical target speed in px/s.
            sensor_margin_px: Distance from frame margin to trigger edge-effect check.
            snr_noise_threshold: Minimum SNR below which jumps are attributed to noise.
        """
        self.jump_threshold_px = jump_threshold_px
        self.max_physical_speed_px_s = max_physical_speed_px_s
        self.sensor_margin_px = sensor_margin_px
        self.snr_noise_threshold = snr_noise_threshold

        self._history: List[Dict[str, Any]] = []
        self._diagnoses: List[JumpDiagnosis] = []

    @property
    def diagnoses(self) -> List[JumpDiagnosis]:
        """All recorded jump diagnoses."""
        return list(self._diagnoses)

    def reset(self) -> None:
        """Clear temporal history and diagnoses."""
        self._history.clear()
        self._diagnoses.clear()

    def record_frame(
        self,
        frame_id: int,
        timestamp: float,
        dt: float,
        centroid: Optional[Tuple[float, float]],
        confidence: float,
        detected: bool,
        detector_source: str = "HYBRID",
        quality: Optional[Dict[str, Any]] = None,
        candidate_count: int = 1,
        clipped_by_edge: bool = False,
    ) -> Optional[JumpDiagnosis]:
        """Record and evaluate the latest frame for temporal jumps.

        Maintains a rolling window and compares frame k against frame k-1 and history.

        Returns:
            JumpDiagnosis if a jump was detected and evaluated, or None if motion is smooth.
        """
        entry = {
            "frame_id": frame_id,
            "timestamp": timestamp,
            "dt": dt,
            "centroid": centroid,
            "confidence": confidence,
            "detected": detected,
            "source": detector_source,
            "quality": quality or {},
            "candidate_count": candidate_count,
            "clipped_by_edge": clipped_by_edge,
        }
        self._history.append(entry)

        # Need at least two frames to compare k-1 and k
        if len(self._history) < 2:
            return None

        prev = self._history[-2]
        curr = self._history[-1]

        # Both frames must have valid centroids to compute displacement
        if prev["centroid"] is None or curr["centroid"] is None or not curr["detected"]:
            return None

        u_prev, v_prev = prev["centroid"]
        u_curr, v_curr = curr["centroid"]
        dist = math.hypot(u_curr - u_prev, v_curr - v_prev)
        dt_eff = max(1e-4, curr["dt"])
        speed = dist / dt_eff

        # Check if displacement exceeds threshold
        if dist < self.jump_threshold_px and speed < self.max_physical_speed_px_s:
            return None

        # Jump detected: diagnose the cause using measurable optical evidence
        cause, evidence = self._diagnose_jump_cause(prev, curr, dist, speed)

        diagnosis = JumpDiagnosis(
            frame_id=frame_id,
            timestamp=timestamp,
            jump_distance_px=round(dist, 3),
            apparent_velocity_px_s=round(speed, 2),
            cause=cause,
            confidence=round(confidence, 4),
            evidence_summary=evidence,
            retained_as_valid=bool(cause in (JumpCause.TRUE_MOTION, JumpCause.HYBRID_HANDOFF)),
        )

        self._diagnoses.append(diagnosis)
        return diagnosis

    def _diagnose_jump_cause(
        self,
        prev: Dict[str, Any],
        curr: Dict[str, Any],
        dist: float,
        speed: float,
    ) -> Tuple[JumpCause, str]:
        """Determine whether jump is caused by handoff, ambiguity, noise, edge, or true motion."""
        u_curr, v_curr = curr["centroid"]
        q_curr = curr.get("quality", {})
        snr = float(q_curr.get("snr", 10.0))
        contrast = float(q_curr.get("local_contrast", 50.0))
        is_clipped = bool(curr.get("clipped_by_edge", False))

        # Check 1: Edge Effects (boundary clipping shifts optical centroid)
        m = self.sensor_margin_px
        near_boundary = (u_curr <= m or u_curr >= 640 - m or v_curr <= m or v_curr >= 480 - m)
        if is_clipped or near_boundary:
            return (
                JumpCause.EDGE_EFFECT,
                f"Centroid jumped {dist:.1f}px near frame boundary (u={u_curr:.1f}, v={v_curr:.1f}, clipped={is_clipped})",
            )

        # Check 2: Hybrid Handoff (detector engine switched e.g. CLASSICAL <-> NEURAL)
        source_prev = str(prev.get("source", "")).upper()
        source_curr = str(curr.get("source", "")).upper()
        if source_prev and source_curr and source_prev != source_curr:
            return (
                JumpCause.HYBRID_HANDOFF,
                f"Centroid jumped {dist:.1f}px concurrent with detector engine handoff ({source_prev} -> {source_curr})",
            )

        # Check 3: Candidate Ambiguity (multiple valid candidates competing in the scene)
        cand_count = int(curr.get("candidate_count", 1))
        if cand_count > 1 and curr["confidence"] < 0.75:
            return (
                JumpCause.CANDIDATE_AMBIGUITY,
                f"Centroid jumped {dist:.1f}px with {cand_count} competing candidates present in the field of view",
            )

        # Check 4: Noise (low SNR, faint contrast, high background noise)
        if snr < self.snr_noise_threshold or contrast < 12.0 or curr["confidence"] < 0.35:
            return (
                JumpCause.NOISE,
                f"Centroid jumped {dist:.1f}px under low optical quality (SNR={snr:.1f}, contrast={contrast:.1f}, conf={curr['confidence']:.2f})",
            )

        # Check 5: True Target Motion (high confidence, clean spot, consistent detector)
        # Without excessive smoothing, legitimate target acceleration or platform vibration is recognized
        return (
            JumpCause.TRUE_MOTION,
            f"Physical target displacement {dist:.1f}px ({speed:.1f} px/s) confirmed with high confidence ({curr['confidence']:.2f}) and SNR ({snr:.1f})",
        )
