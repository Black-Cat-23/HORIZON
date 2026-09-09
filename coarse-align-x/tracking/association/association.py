"""
HORIZON Multi-Candidate Association Engine
=================================================
Associates extracted optical candidates against predicted filter state
using statistical gating and multi-criteria cost ranking.

Candidate Ranking Formulation:
    For all candidates passing the validation gate (d_i^2 <= gamma):
        J_i = d_i^2 - alpha * confidence_i - beta * score_i
    Where:
        d_i^2: Normalized statistical Mahalanobis distance from predicted position
        confidence_i: Detector confidence score in [0.0, 1.0]
        score_i: Multi-criteria composite optical quality score

Strict Invariant: Zero access to true target position or ground-truth state.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Dict, List, Optional, Tuple
import numpy as np

from tracking.association.gate import MahalanobisGate
from tracking.estimation.innovation import compute_innovation
from tracking.estimation.model import build_measurement_matrix, build_measurement_noise_matrix


@dataclass(frozen=True)
class MeasurementCandidate:
    """Standardized representation of a candidate optical detection."""
    candidate_id: int
    centroid_x: float
    centroid_y: float
    confidence: float
    bbox: Optional[Tuple[int, int, int, int]] = None
    score: float = 0.0
    reason: str = ""

    @property
    def centroid(self) -> Tuple[float, float]:
        return (self.centroid_x, self.centroid_y)


@dataclass(frozen=True)
class AssociationResult:
    """Result of candidate-to-track association."""
    associated: bool
    selected_candidate: Optional[MeasurementCandidate]
    rejected_candidates: List[MeasurementCandidate]
    all_candidates_count: int
    cost: float = 0.0
    mahalanobis_sq: float = 0.0
    mahalanobis_distance: float = 0.0
    decision_reason: str = ""
    rejection_reasons: Optional[Dict[int, str]] = None


class TrackAssociator:
    """Multi-candidate gating and association engine."""

    def __init__(
        self,
        gate_threshold: float = 9.210,
        alpha_confidence: float = 2.0,
        beta_score: float = 1.0,
        base_sigma_px: float = 0.5,
    ) -> None:
        """Initialize associator.

        PROJECT ENGINEERING PARAMETERS:
            gate_threshold: Chi-squared threshold (default 9.210 -> 99% for 2 DOF).
            alpha_confidence: Weight for detector confidence reward.
            beta_score: Weight for optical feature score reward.
            base_sigma_px: Base measurement noise standard deviation.
        """
        self._gate = MahalanobisGate(threshold=gate_threshold)
        self._alpha = float(alpha_confidence)
        self._beta = float(beta_score)
        self._base_sigma_px = float(base_sigma_px)
        self._H = build_measurement_matrix()

    @property
    def gate(self) -> MahalanobisGate:
        return self._gate

    def associate(
        self,
        candidates: List[MeasurementCandidate],
        x_pred: np.ndarray,
        P_pred: np.ndarray,
    ) -> AssociationResult:
        """Associate candidates with predicted track state.

        Steps:
          1. Predict target position: z_hat = H * x_pred.
          2. For each candidate, evaluate residual, covariance S, and Mahalanobis distance d^2.
          3. Filter candidates through Mahalanobis gate d^2 <= gamma.
          4. Reject candidates outside the gate.
          5. For remaining candidates, compute ranking cost J_i.
          6. Select candidate with lowest cost.

        Args:
            candidates: List of MeasurementCandidate detections.
            x_pred: 4×1 predicted state vector [px, py, vx, vy]^T.
            P_pred: 4×4 predicted covariance matrix.

        Returns:
            AssociationResult dataclass.
        """
        if not candidates:
            return AssociationResult(
                associated=False,
                selected_candidate=None,
                rejected_candidates=[],
                all_candidates_count=0,
                decision_reason="No candidate measurements available for association",
                rejection_reasons={},
            )

        valid_gated: List[Tuple[float, float, float, MeasurementCandidate]] = []
        rejected: List[MeasurementCandidate] = []
        rejection_reasons: Dict[int, str] = {}

        for cand in candidates:
            z = np.array([[cand.centroid_x], [cand.centroid_y]], dtype=np.float64)
            R = build_measurement_noise_matrix(
                confidence=cand.confidence,
                base_sigma_px=self._base_sigma_px,
            )

            is_valid, d2, d = self._gate.test(z, x_pred, P_pred, self._H, R)

            if not is_valid:
                rejected.append(cand)
                rejection_reasons[cand.candidate_id] = (
                    f"Candidate rejected because Mahalanobis distance d²={d2:.2f} exceeded validation gate {self._gate.threshold:.2f}"
                )
            else:
                # Cost function: Lower is better.
                # Penalize large statistical distance d^2; reward high detector confidence and score
                cost = float(d2 - (self._alpha * cand.confidence) - (self._beta * cand.score))
                valid_gated.append((cost, d2, d, cand))

        if not valid_gated:
            return AssociationResult(
                associated=False,
                selected_candidate=None,
                rejected_candidates=rejected,
                all_candidates_count=len(candidates),
                decision_reason=f"All {len(candidates)} candidate(s) rejected by Mahalanobis validation gate (threshold={self._gate.threshold:.2f})",
                rejection_reasons=rejection_reasons,
            )

        # Sort valid candidates by minimum cost
        valid_gated.sort(key=lambda item: item[0])
        best_cost, best_d2, best_d, best_cand = valid_gated[0]

        # Remaining non-selected gated candidates also tracked
        for item in valid_gated[1:]:
            rejection_reasons[item[3].candidate_id] = (
                f"Candidate rejected because cost J={item[0]:.2f} (d²={item[1]:.2f}) was higher than optimal candidate J={best_cost:.2f}"
            )
        other_candidates = [item[3] for item in valid_gated[1:]]
        all_rejected = rejected + other_candidates

        decision_reason = (
            f"Candidate #{best_cand.candidate_id} selected because minimal ranking cost J={best_cost:.2f} "
            f"(d²={best_d2:.2f} <= {self._gate.threshold:.2f}, conf={best_cand.confidence:.2f}, score={best_cand.score:.2f})"
        )

        return AssociationResult(
            associated=True,
            selected_candidate=best_cand,
            rejected_candidates=all_rejected,
            all_candidates_count=len(candidates),
            cost=best_cost,
            mahalanobis_sq=best_d2,
            mahalanobis_distance=best_d,
            decision_reason=decision_reason,
            rejection_reasons=rejection_reasons,
        )
