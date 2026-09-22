"""
HORIZON Track Quality & Filter Health Monitoring
========================================================
Quantitative indicators of tracking consistency, covariance convergence,
measurement availability, and statistical health.

NOTE: This is NOT the future PAT state machine (SEARCH/ACQUIRE/TRACK/DEGRADED/REACQUIRE).
It is purely quantitative statistical health data produced by the estimator.

Strict Invariant: Zero access to true target position or ground-truth state.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Optional
import numpy as np


@dataclass(frozen=True)
class TrackQuality:
    """Quantitative tracking health and statistical consistency record."""
    measurement_available: bool
    innovation_norm: float         # ||y||_2 [px]
    mahalanobis_distance: float    # sqrt(y^T * S^-1 * y)
    covariance_trace: float        # tr(P)
    position_uncertainty: float    # sqrt(P[0,0] + P[1,1]) [px]
    velocity_uncertainty: float    # sqrt(P[2,2] + P[3,3]) [px/s]
    consecutive_measurements: int  # Number of uninterrupted valid updates
    consecutive_misses: int        # Number of consecutive unobserved frames
    last_update_time: float        # Timestamp of last observation [s]
    track_age: int                 # Total filter propagation steps
    association_quality: float     # Gating match quality in [0.0, 1.0]
    nis: float = 0.0               # Normalized Innovation Squared (y^T S^-1 y)


def evaluate_track_quality(
    P: np.ndarray,
    innovation_norm: float,
    mahalanobis_dist: float,
    measurement_available: bool,
    consecutive_hits: int,
    consecutive_misses: int,
    last_update_time: float,
    track_age: int,
    detector_confidence: float = 1.0,
    gate_threshold: float = 9.21,
) -> TrackQuality:
    """Compute normalized track quality and filter metrics.

    Args:
        P: 4×4 state covariance matrix.
        innovation_norm: ||y|| in pixels.
        mahalanobis_dist: sqrt(d^2) dimensionless.
        measurement_available: True if observation was fused in this step.
        consecutive_hits: Number of continuous hits.
        consecutive_misses: Number of continuous misses.
        last_update_time: Timestamp of last measurement.
        track_age: Age in steps.
        detector_confidence: Confidence from Phase 4 detector in [0.0, 1.0].
        gate_threshold: Chi-squared threshold for association gate.

    Returns:
        TrackQuality dataclass instance.
    """
    cov_tr = float(np.trace(P))
    pos_unc = float(math.sqrt(max(0.0, P[0, 0] + P[1, 1])))
    vel_unc = float(math.sqrt(max(0.0, P[2, 2] + P[3, 3])))
    d2 = mahalanobis_dist * mahalanobis_dist

    # Association quality metric in [0.0, 1.0]
    # Combines Mahalanobis closeness exp(-0.5 * d^2 / gate) with detector confidence
    if measurement_available:
        gate_scale = max(1.0, gate_threshold)
        dist_factor = math.exp(-0.5 * min(d2, 50.0) / gate_scale)
        assoc_quality = float(np.clip(dist_factor * detector_confidence, 0.0, 1.0))
    else:
        assoc_quality = 0.0

    return TrackQuality(
        measurement_available=measurement_available,
        innovation_norm=float(innovation_norm),
        mahalanobis_distance=float(mahalanobis_dist),
        covariance_trace=cov_tr,
        position_uncertainty=pos_unc,
        velocity_uncertainty=vel_unc,
        consecutive_measurements=consecutive_hits,
        consecutive_misses=consecutive_misses,
        last_update_time=float(last_update_time),
        track_age=track_age,
        association_quality=assoc_quality,
        nis=d2,
    )
