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
    dist_px: float,
    dist_sigma_px: float = 10.0,
    velocity_hint_px_s: float = 0.0,
    camera_rate_hz: float = 30.0,
) -> float:
    """Compute spatial agreement score in range [0.0, 1.0].

    Uses Gaussian decay relative to centroid distance:
        score = exp(-0.5 * (dist / adaptive_sigma)^2)

    The sigma is widened proportionally to the beacon velocity so that fast-moving
    beacons (e.g. random trajectory, spiral) are not penalised for inter-frame drift
    between Classical optical and Neural bbox centroids:
        adaptive_sigma = max(dist_sigma_px,
                            dist_sigma_px + 0.5 * (velocity_hint_px_s / camera_rate_hz))

    Args:
        dist_px:           Centroid distance between Classical and Neural proposals (px).
        dist_sigma_px:     Base sigma of the agreement Gaussian (px). From config.
        velocity_hint_px_s: Optional estimated beacon velocity magnitude (px/s) from the
                            state estimator. 0.0 disables velocity adaptation.
        camera_rate_hz:    Camera frame rate used to convert velocity to per-frame distance.
    """
    if dist_sigma_px <= 0.0:
        dist_sigma_px = 10.0
    if velocity_hint_px_s > 0.0 and camera_rate_hz > 0.0:
        per_frame_drift = velocity_hint_px_s / camera_rate_hz
        adaptive_sigma = max(dist_sigma_px, dist_sigma_px + 0.5 * per_frame_drift)
    else:
        adaptive_sigma = dist_sigma_px
    val = math.exp(-0.5 * (dist_px / adaptive_sigma) ** 2)
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
        # Weighted combination of optical shape, profile, and energy metrics
        circ = getattr(rc, "circularity", 0.5)
        comp = getattr(rc, "compactness", 0.5)
        symm = getattr(rc, "symmetry", 0.5)
        rad = getattr(rc, "radial_consistency", 0.5)
        size_plaus = getattr(rc, "size_plausibility", 0.5)
        flux = getattr(rc, "integrated_flux", 0.0)
        flux_score = float(np.clip(flux / 2000.0, 0.20, 1.0))
        area = getattr(rc, "area_px", 10.0)
        area_reg = float(np.clip(area / 8.0, 0.40, 1.0))

        score = (
            0.20 * (circ * area_reg)
            + 0.15 * (comp * area_reg)
            + 0.15 * symm
            + 0.20 * rad
            + 0.15 * size_plaus
            + 0.15 * flux_score
        )
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
    grace_factor: float = 1.0,
    velocity_hint_px_s: float = 0.0,
) -> Tuple[bool, float, float]:
    """Test candidate against estimator validation gate.

    Args:
        candidate_centroid: (u, v) of the candidate in pixels.
        predicted_pos:      Estimator predicted position, or None (disables gating).
        prediction_cov:     2×2 position covariance matrix, or None (uses Euclidean fallback).
        gate_threshold:     Mahalanobis² chi-squared gate (default 9.21 = 99th percentile 2-DOF).
        grace_factor:       Multiplier on gate_threshold, e.g. 2.0 during trajectory inflection
                            points where estimator may be momentarily uncertain. >1 widens the gate.
        velocity_hint_px_s: Estimated target speed (px/s) to dynamically adapt gate to fast maneuvers.

    Returns:
        (is_valid, mahalanobis_sq, consistency_score)
    """
    if predicted_pos is None or prediction_cov is None:
        return True, 0.0, 1.0

    # Expand grace factor dynamically for high-velocity maneuvers
    dyn_grace = max(grace_factor, 1.0)
    if velocity_hint_px_s > 0.0:
        dyn_grace = max(dyn_grace, 1.0 + float(velocity_hint_px_s) / 80.0)

    effective_gate = gate_threshold * dyn_grace
    dx = candidate_centroid[0] - predicted_pos[0]
    dy = candidate_centroid[1] - predicted_pos[1]
    diff = np.array([dx, dy], dtype=np.float64)

    if prediction_cov is not None and prediction_cov.shape == (2, 2):
        try:
            inv_cov = np.linalg.inv(prediction_cov)
            d2 = float(diff.T @ inv_cov @ diff)
            is_valid = bool(d2 <= effective_gate)
            score = float(np.clip(math.exp(-0.5 * max(d2, 0.0)), 0.0, 1.0))
            return is_valid, d2, score
        except np.linalg.LinAlgError:
            pass

    # Euclidean approximation using gate-scaled sigma
    dist_sq = float(dx * dx + dy * dy)
    # sigma derived from gate to keep Euclidean fallback consistent:
    # chi2_2dof_99 = 9.21 → sigma = sqrt(dist_sq / 9.21) when at the boundary
    sigma_sq = max(prediction_cov[0, 0] + prediction_cov[1, 1], 1.0) if (
        prediction_cov is not None and prediction_cov.shape == (2, 2)
    ) else (25.0 ** 2)
    d2 = dist_sq / max(sigma_sq, 1e-6)
    is_valid = bool(d2 <= effective_gate)
    score = float(np.clip(math.exp(-0.5 * d2), 0.0, 1.0))
    return is_valid, d2, score
