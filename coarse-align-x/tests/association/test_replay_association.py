"""
Tests for deterministic replay and consistency of candidate association.
"""

import numpy as np
import pytest
from tracking.association.association import MeasurementCandidate, TrackAssociator


def test_replay_deterministic_association():
    associator = TrackAssociator(gate_threshold=9.21)

    candidates = [
        MeasurementCandidate(candidate_id=1, centroid_x=321.0, centroid_y=240.5, confidence=0.95, score=0.9),
        MeasurementCandidate(candidate_id=2, centroid_x=335.0, centroid_y=245.0, confidence=0.80, score=0.6),
        MeasurementCandidate(candidate_id=3, centroid_x=450.0, centroid_y=400.0, confidence=0.99, score=0.9),
    ]
    x_pred = np.array([[320.0], [240.0], [0.0], [0.0]], dtype=np.float64)
    P_pred = np.diag([10.0, 10.0, 2.0, 2.0])

    res1 = associator.associate(candidates, x_pred, P_pred)
    res2 = associator.associate(candidates, x_pred, P_pred)

    assert res1.associated == res2.associated
    assert res1.selected_candidate.candidate_id == res2.selected_candidate.candidate_id
    assert res1.cost == res2.cost
    assert res1.mahalanobis_sq == res2.mahalanobis_sq
    assert res1.decision_reason == res2.decision_reason
    assert res1.rejection_reasons == res2.rejection_reasons
