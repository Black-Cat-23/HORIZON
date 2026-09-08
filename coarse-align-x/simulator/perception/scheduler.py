"""
Compute-Adaptive Perception Scheduler
======================================
Wraps perception detectors and decides per frame whether full hybrid
(classical + neural + fusion) detection is required, or whether a cheap
classical-only fast path is safe, based on current PAT confidence state.

Strict Invariant: Zero ground-truth leakage. Inputs are PATMode, track_quality,
and consecutive_hits — all already computed by PATModeManager without any
access to true target position.
"""

from dataclasses import dataclass
from typing import Optional, Tuple
import numpy as np

from simulator.perception.detector import ClassicalBeaconDetector, DetectionResult
from simulator.perception.neural_detector import NeuralBeaconDetector
from simulator.perception.hybrid_fusion import HybridPerceptionFusion


@dataclass(frozen=True)
class SchedulerConfig:
    """
    Configuration for the Adaptive Perception Scheduler.
    
    high_quality_threshold: Minimum track_quality (0-1) to be eligible for fast path.
    min_stable_hits: Minimum consecutive_hits to be eligible for fast path.
    recalibration_period_frames: Force full hybrid at least this often even if stable.
    escalate_on_low_confidence: Force full hybrid if fast-path classical result is weak.
    classical_escalation_confidence: Below this, escalate this frame.
    escalate_on_multiple_candidates: Ambiguity in the frame -> escalate.
    always_full_modes: Modes that always require full hybrid perception.
    """
    high_quality_threshold: float = 0.75
    min_stable_hits: int = 5
    recalibration_period_frames: int = 10
    escalate_on_low_confidence: bool = True
    classical_escalation_confidence: float = 0.5
    escalate_on_multiple_candidates: bool = True
    always_full_modes: Tuple[str, ...] = ("SEARCH", "ACQUIRE", "DEGRADED", "REACQUIRE")


class AdaptivePerceptionScheduler:
    """
    Decides frame-by-frame whether to use the cheap classical path or full hybrid.
    """
    def __init__(
        self,
        classical_detector: ClassicalBeaconDetector,
        neural_detector: NeuralBeaconDetector,
        hybrid_fusion: HybridPerceptionFusion,
        config: Optional[SchedulerConfig] = None
    ):
        self._classical = classical_detector
        self._neural = neural_detector
        self._fusion = hybrid_fusion
        self._config = config or SchedulerConfig()
        self._frames_since_full_hybrid = 0

    def run_hybrid_fusion(
        self,
        frame: np.ndarray,
        timestamp: float,
        collect_diagnostics: bool = False,
    ) -> DetectionResult:
        """Executes the full hybrid pipeline."""
        class_res = self._classical.detect(frame, timestamp, collect_diagnostics)
        neur_res = self._neural.detect(frame, timestamp, collect_diagnostics)
        return self._fusion.fuse(neur_res, class_res)

    def detect(
        self,
        frame: np.ndarray,
        timestamp: float,
        pat_mode: str,
        track_quality: float,
        consecutive_hits: int,
        collect_diagnostics: bool = False,
    ) -> Tuple[DetectionResult, str]:
        """
        Returns (DetectionResult, compute_mode) where compute_mode is
        "FULL_HYBRID" or "CLASSICAL_FAST_PATH".
        """
        # 1. Eligibility Check
        needs_full_hybrid = False
        if pat_mode in self._config.always_full_modes:
            needs_full_hybrid = True
        elif track_quality < self._config.high_quality_threshold:
            needs_full_hybrid = True
        elif consecutive_hits < self._config.min_stable_hits:
            needs_full_hybrid = True
        elif self._frames_since_full_hybrid >= self._config.recalibration_period_frames:
            needs_full_hybrid = True

        if needs_full_hybrid:
            self._frames_since_full_hybrid = 0
            res = self.run_hybrid_fusion(frame, timestamp, collect_diagnostics)
            return res, "FULL_HYBRID"

        # 2. Fast Path Attempt
        res = self._classical.detect(frame, timestamp, collect_diagnostics)

        # 3. Escalation Check
        escalate = False
        if not res.detected:
            escalate = True
        elif self._config.escalate_on_low_confidence and res.confidence < self._config.classical_escalation_confidence:
            escalate = True
        elif self._config.escalate_on_multiple_candidates and res.candidate_count > 1:
            escalate = True

        if escalate:
            # Immediately re-run full hybrid for this frame
            self._frames_since_full_hybrid = 0
            full_res = self.run_hybrid_fusion(frame, timestamp, collect_diagnostics)
            return full_res, "FULL_HYBRID"

        # Fast path succeeded safely
        self._frames_since_full_hybrid += 1
        return res, "CLASSICAL_FAST_PATH"

