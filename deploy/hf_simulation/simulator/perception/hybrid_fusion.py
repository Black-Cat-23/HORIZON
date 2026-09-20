"""
HORIZON Hybrid Perception Fusion Interface (Detector C)
===============================================================
Combines Neural Detector confidence, Classical optical PSF consistency check,
and Temporal trajectory prediction consistency into a unified fused score.

Strict Invariant: Zero ground-truth access or leakage.
"""

from __future__ import annotations

import math
from typing import Optional, Tuple
import numpy as np

from simulator.perception.detector import DetectionResult


class HybridPerceptionFusion:
    """Combines Neural confidence, Classical optical features, and Temporal kinematic consistency."""

    def __init__(
        self,
        weight_neural: float = 0.50,
        weight_optical: float = 0.30,
        weight_temporal: float = 0.20,
    ) -> None:
        self.w_neural = weight_neural
        self.w_optical = weight_optical
        self.w_temporal = weight_temporal

    def fuse(
        self,
        neural_result: DetectionResult,
        classical_result: DetectionResult,
        predicted_pos: Optional[Tuple[float, float]] = None,
        pos_uncertainty: float = 10.0,
    ) -> DetectionResult:
        """Fuse Neural and Classical detection candidates into a single hybrid DetectionResult."""
        if not neural_result.detected and not classical_result.detected:
            return DetectionResult(
                detected=False,
                centroid=None,
                bbox=None,
                confidence=0.0,
                candidate_count=0,
                method_used="hybrid_fusion",
                processing_time_ms=neural_result.processing_time_ms + classical_result.processing_time_ms,
            )

        # Primary candidate selection
        primary = neural_result if neural_result.detected else classical_result
        secondary = classical_result if neural_result.detected else neural_result

        c_neural = neural_result.confidence if neural_result.detected else 0.0
        c_optical = classical_result.confidence if classical_result.detected else 0.0

        # Temporal consistency score relative to Kalman predicted position
        s_temporal = 1.0
        if predicted_pos is not None and primary.centroid is not None:
            dist = math.hypot(
                primary.centroid[0] - predicted_pos[0],
                primary.centroid[1] - predicted_pos[1],
            )
            s_temporal = float(np.exp(-0.5 * (dist / max(pos_uncertainty, 1.0)) ** 2))

        fused_score = (
            self.w_neural * c_neural
            + self.w_optical * c_optical
            + self.w_temporal * s_temporal
        )
        fused_score = float(np.clip(fused_score, 0.0, 1.0))

        detected = fused_score >= 0.35

        return DetectionResult(
            detected=detected,
            centroid=primary.centroid if detected else None,
            bbox=primary.bbox if detected else None,
            confidence=fused_score if detected else 0.0,
            candidate_count=(1 if neural_result.detected else 0) + (1 if classical_result.detected else 0),
            method_used="hybrid_fusion",
            processing_time_ms=neural_result.processing_time_ms + classical_result.processing_time_ms,
        )
