"""
Unit tests for Phase C Data Association & Clutter Rejection SOTA Upgrades.
"""

import numpy as np
import pytest

from tracking.association.gate import AdaptiveMahalanobisGate
from tracking.association.association import (
    MeasurementCandidate,
    HungarianMultiTargetAssociator,
    JPDACandidateAssociator,
)


def test_adaptive_mahalanobis_gate():
    gate = AdaptiveMahalanobisGate(base_threshold=9.210)
    x_pred = np.array([[320.0], [240.0], [50.0], [0.0]], dtype=np.float64)
    P_pred = np.eye(4, dtype=np.float64) * 5.0

    thresh = gate.compute_adaptive_threshold(x_pred, P_pred)
    assert thresh >= 9.210

    z = np.array([[322.0], [241.0]], dtype=np.float64)
    H = np.array([[1, 0, 0, 0], [0, 1, 0, 0]], dtype=np.float64)
    R = np.eye(2, dtype=np.float64) * 0.25

    is_valid, d2, d = gate.test(z, x_pred, P_pred, H, R)
    assert is_valid is True
    assert d2 > 0 and d > 0


def test_hungarian_multi_target_associator():
    associator = HungarianMultiTargetAssociator(gate_threshold=9.210)
    cand1 = MeasurementCandidate(candidate_id=1, centroid_x=100.0, centroid_y=100.0, confidence=0.9, score=0.85)
    cand2 = MeasurementCandidate(candidate_id=2, centroid_x=200.0, centroid_y=200.0, confidence=0.88, score=0.80)
    candidates = [cand1, cand2]

    x1 = np.array([[101.0], [99.0], [0.0], [0.0]], dtype=np.float64)
    x2 = np.array([[199.0], [201.0], [0.0], [0.0]], dtype=np.float64)
    P = np.eye(4, dtype=np.float64) * 2.0

    assignments = associator.associate_matrix(candidates, [x1, x2], [P, P])
    assert len(assignments) == 2
    assert assignments[0].candidate_id == 1
    assert assignments[1].candidate_id == 2


def test_jpda_soft_association():
    associator = JPDACandidateAssociator(gate_threshold=9.210)
    cand1 = MeasurementCandidate(candidate_id=1, centroid_x=100.0, centroid_y=100.0, confidence=0.95, score=0.9)
    cand2 = MeasurementCandidate(candidate_id=2, centroid_x=102.0, centroid_y=101.0, confidence=0.70, score=0.6)
    candidates = [cand1, cand2]

    x_pred = np.array([[100.5], [100.5], [0.0], [0.0]], dtype=np.float64)
    P_pred = np.eye(4, dtype=np.float64) * 2.0

    res = associator.associate_jpda(candidates, x_pred, P_pred)
    assert res.associated is True
    assert res.combined_innovation.shape == (2, 1)
    assert res.combined_covariance_spread.shape == (2, 2)
    assert len(res.marginal_probabilities) == 3
    assert res.best_candidate.candidate_id == 1
