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


# ---------------------------------------------------------------------------
# Hungarian Multi-Target Assignment Engine
# ---------------------------------------------------------------------------

class HungarianMultiTargetAssociator:
    """Hungarian Kuhn-Munkres global multi-target bipartite assignment engine."""

    def __init__(self, gate_threshold: float = 9.210) -> None:
        self._gate = MahalanobisGate(threshold=gate_threshold)
        self._H = build_measurement_matrix()

    def associate_matrix(
        self,
        candidates: List[MeasurementCandidate],
        tracks_x_pred: List[np.ndarray],
        tracks_P_pred: List[np.ndarray],
    ) -> List[Optional[MeasurementCandidate]]:
        """Perform optimal 2D Hungarian assignment between M tracks and N candidates."""
        from scipy.optimize import linear_sum_assignment
        num_tracks = len(tracks_x_pred)
        num_cands = len(candidates)
        if num_tracks == 0:
            return []
        if num_cands == 0:
            return [None] * num_tracks

        cost_matrix = np.full((num_tracks, num_cands), 1e6, dtype=np.float64)

        for i in range(num_tracks):
            x_pred = tracks_x_pred[i]
            P_pred = tracks_P_pred[i]
            for j in range(num_cands):
                cand = candidates[j]
                z = np.array([[cand.centroid_x], [cand.centroid_y]], dtype=np.float64)
                R = build_measurement_noise_matrix(confidence=cand.confidence)
                is_valid, d2, _ = self._gate.test(z, x_pred, P_pred, self._H, R)
                if is_valid:
                    cost = d2 - 2.0 * cand.confidence - 1.0 * cand.score
                    cost_matrix[i, j] = cost

        row_ind, col_ind = linear_sum_assignment(cost_matrix)

        assignments: List[Optional[MeasurementCandidate]] = [None] * num_tracks
        for r, c in zip(row_ind, col_ind):
            if cost_matrix[r, c] < 1e5:
                assignments[r] = candidates[c]

        return assignments


# ---------------------------------------------------------------------------
# JPDA Soft-Association Engine
# ---------------------------------------------------------------------------

@dataclass
class JPDAAssociationResult:
    """Result of JPDA soft-association integration."""
    associated: bool
    combined_innovation: np.ndarray
    combined_covariance_spread: np.ndarray
    marginal_probabilities: List[float]
    best_candidate: Optional[MeasurementCandidate]


class JPDACandidateAssociator:
    """Joint Probabilistic Data Association (JPDA) Bayesian soft-association integrator."""

    def __init__(self, gate_threshold: float = 9.210, clutter_density: float = 1e-5) -> None:
        self._gate = MahalanobisGate(threshold=gate_threshold)
        self._clutter_density = float(clutter_density)
        self._H = build_measurement_matrix()

    def associate_jpda(
        self,
        candidates: List[MeasurementCandidate],
        x_pred: np.ndarray,
        P_pred: np.ndarray,
    ) -> JPDAAssociationResult:
        """Compute marginal joint association probabilities and soft-associated innovation."""
        if not candidates:
            return JPDAAssociationResult(
                associated=False,
                combined_innovation=np.zeros((2, 1), dtype=np.float64),
                combined_covariance_spread=np.zeros((2, 2), dtype=np.float64),
                marginal_probabilities=[],
                best_candidate=None,
            )

        gated_candidates: List[Tuple[float, float, MeasurementCandidate, np.ndarray]] = []
        for cand in candidates:
            z = np.array([[cand.centroid_x], [cand.centroid_y]], dtype=np.float64)
            R = build_measurement_noise_matrix(confidence=cand.confidence)
            is_valid, d2, _ = self._gate.test(z, x_pred, P_pred, self._H, R)
            if is_valid:
                inno = compute_innovation(z, x_pred, P_pred, self._H, R)
                gated_candidates.append((d2, inno.mahalanobis_distance, cand, inno.residual))

        if not gated_candidates:
            return JPDAAssociationResult(
                associated=False,
                combined_innovation=np.zeros((2, 1), dtype=np.float64),
                combined_covariance_spread=np.zeros((2, 2), dtype=np.float64),
                marginal_probabilities=[],
                best_candidate=None,
            )

        likelihoods = [np.exp(-0.5 * d2) for d2, _, _, _ in gated_candidates]
        v0 = max(1e-4, self._clutter_density * (2.0 * np.pi))
        total_lik = v0 + sum(likelihoods)

        beta_0 = v0 / total_lik
        betas = [lik / total_lik for lik in likelihoods]

        y_tilde_jpda = np.zeros((2, 1), dtype=np.float64)
        for beta_j, (_, _, _, res) in zip(betas, gated_candidates):
            y_tilde_jpda += beta_j * res

        P_spread = np.zeros((2, 2), dtype=np.float64)
        for beta_j, (_, _, _, res) in zip(betas, gated_candidates):
            diff = res - y_tilde_jpda
            P_spread += beta_j * (diff @ diff.T)

        best_cand = max(gated_candidates, key=lambda item: item[2].confidence)[2]

        return JPDAAssociationResult(
            associated=True,
            combined_innovation=y_tilde_jpda,
            combined_covariance_spread=P_spread,
            marginal_probabilities=[beta_0] + betas,
            best_candidate=best_cand,
        )
