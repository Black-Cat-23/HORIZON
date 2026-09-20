"""
HORIZON Perception Feature Consistency Metrics
=====================================================
Phase 8 spatial agreement, bounding box/size agreement, optical quality,
and temporal Mahalanobis consistency scoring.

Strict Invariant: Zero ground-truth access or dependencies.
"""

from __future__ import annotations

import math
from typing import Optional, Tuple
import numpy as np

from simulator.perception.hybrid_candidate import UnifiedCandidate


def compute_spatial_agreement(
    dist_px: float, dist_sigma_px: float = 10.0
) -> float:
    """Compute spatial agreement score in range [0.0, 1.0].

    Uses Gaussian decay relative to centroid distance:
        score = exp(-0.5 * (dist / dist_sigma)^2)
    """
    if dist_sigma_px <= 0.0:
        dist_sigma_px = 10.0
    val = math.exp(-0.5 * (dist_px / dist_sigma_px) ** 2)
    return float(np.clip(val, 0.0, 1.0))


def compute_size_agreement(
    area_a: float, area_b: float
) -> float:
    """Compute size/area agreement ratio in range [0.0, 1.0].

    Uses ratio of min(area_a, area_b) / max(area_a, area_b).
    """
    if area_a <= 0.0 or area_b <= 0.0:
        return 0.0
    val = min(area_a, area_b) / max(area_a, area_b)
    return float(np.clip(val, 0.0, 1.0))


def compute_optical_agreement(
    local_contrast: Optional[float],
    background_estimate: Optional[float],
    expected_contrast: float = 30.0,
) -> float:
    """Compute optical signal contrast score in range [0.0, 1.0]."""
    if local_contrast is None or local_contrast <= 0.0:
        return 0.5  # Neutral fallback when optical features missing
    val = min(local_contrast / max(expected_contrast, 1.0), 1.0)
    return float(np.clip(val, 0.0, 1.0))


def compute_temporal_agreement(
    candidate_centroid: Tuple[float, float],
    predicted_pos: Optional[Tuple[float, float]],
    prediction_cov: Optional[np.ndarray] = None,
    max_uncertainty_px: float = 25.0,
) -> float:
    """Compute temporal consistency score relative to estimator prediction.

    If covariance matrix is provided, calculates 2D Mahalanobis distance.
    Otherwise uses normalized Euclidean distance.

    Returns:
        float score in range [0.0, 1.0].
    """
    if predicted_pos is None:
        return 1.0  # Neutral fallback when temporal prediction unavailable

    dx = candidate_centroid[0] - predicted_pos[0]
    dy = candidate_centroid[1] - predicted_pos[1]

    if prediction_cov is not None and prediction_cov.shape == (2, 2):
        try:
            inv_cov = np.linalg.inv(prediction_cov)
            diff = np.array([dx, dy])
            mahalanobis_sq = float(diff.T @ inv_cov @ diff)
            val = math.exp(-0.5 * max(mahalanobis_sq, 0.0))
            return float(np.clip(val, 0.0, 1.0))
        except np.linalg.LinAlgError:
            pass  # Fallback to Euclidean

    dist = math.hypot(dx, dy)
    val = math.exp(-0.5 * (dist / max(max_uncertainty_px, 1.0)) ** 2)
    return float(np.clip(val, 0.0, 1.0))


def compute_appearance_agreement(
    cand: UnifiedCandidate,
) -> float:
    """Compute appearance consistency score in range [0.0, 1.0].

    Evaluates whether candidate geometry matches an expected optical beacon model:
    - Circular compactness (aspect ratio near 1.0)
    - Symmetry and radial Gaussian profile (from classical candidate if available)
    - Absence of extreme elongation (glint/streak rejection)
    """
    if cand.raw_classical_candidate is not None:
        rc = cand.raw_classical_candidate
        # Weighted combination of optical shape metrics
        circ = getattr(rc, "circularity", 0.5)
        comp = getattr(rc, "compactness", 0.5)
        symm = getattr(rc, "symmetry", 0.5)
        rad = getattr(rc, "radial_consistency", 0.5)
        score = 0.30 * circ + 0.25 * comp + 0.25 * symm + 0.20 * rad
        return float(np.clip(score, 0.0, 1.0))

    # For neural bounding boxes, estimate aspect ratio symmetry
    if cand.bbox_width > 0 and cand.bbox_height > 0:
        ar = min(cand.bbox_width, cand.bbox_height) / max(cand.bbox_width, cand.bbox_height)
        return float(np.clip(ar, 0.0, 1.0))

    return 0.5


def compute_estimator_consistency(
    candidate_centroid: Tuple[float, float],
    predicted_pos: Optional[Tuple[float, float]],
    prediction_cov: Optional[np.ndarray] = None,
    gate_threshold: float = 9.210,
) -> Tuple[bool, float, float]:
    """Test candidate against estimator validation gate.

    Returns:
        (is_valid, mahalanobis_sq, consistency_score)
    """
    if predicted_pos is None:
        return True, 0.0, 1.0

    dx = candidate_centroid[0] - predicted_pos[0]
    dy = candidate_centroid[1] - predicted_pos[1]
    diff = np.array([dx, dy], dtype=np.float64)

    if prediction_cov is not None and prediction_cov.shape == (2, 2):
        try:
            inv_cov = np.linalg.inv(prediction_cov)
            d2 = float(diff.T @ inv_cov @ diff)
            is_valid = bool(d2 <= gate_threshold)
            score = float(np.clip(math.exp(-0.5 * max(d2, 0.0)), 0.0, 1.0))
            return is_valid, d2, score
        except np.linalg.LinAlgError:
            pass

    # Euclidean approximation
    dist_sq = float(dx * dx + dy * dy)
    sigma_sq = 25.0 ** 2
    d2 = dist_sq / sigma_sq
    is_valid = bool(d2 <= gate_threshold)
    score = float(np.clip(math.exp(-0.5 * d2), 0.0, 1.0))
    return is_valid, d2, score
