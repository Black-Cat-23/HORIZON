"""
Unit and integration tests for candidate association and multi-criteria ranking.
"""

import numpy as np
import pytest
from tracking.association.association import MeasurementCandidate, TrackAssociator


def test_candidate_association_ranking_clean():
    associator = TrackAssociator(gate_threshold=9.21)

    # 3 candidates: candidate 1 is closest to predicted position (320, 240)
    c1 = MeasurementCandidate(candidate_id=1, centroid_x=321.0, centroid_y=240.5, confidence=0.95, score=0.9)
    c2 = MeasurementCandidate(candidate_id=2, centroid_x=335.0, centroid_y=245.0, confidence=0.80, score=0.6)
    c3 = MeasurementCandidate(candidate_id=3, centroid_x=450.0, centroid_y=400.0, confidence=0.99, score=0.9)

    x_pred = np.array([[320.0], [240.0], [0.0], [0.0]], dtype=np.float64)
    P_pred = np.diag([10.0, 10.0, 2.0, 2.0])

    res = associator.associate([c1, c2, c3], x_pred, P_pred)

    assert res.associated is True
    assert res.selected_candidate is not None
    assert res.selected_candidate.candidate_id == 1
    assert len(res.rejected_candidates) == 2
    assert "selected because" in res.decision_reason
    assert 3 in res.rejection_reasons
    assert "exceeded validation gate" in res.rejection_reasons[3]


def test_candidate_association_all_rejected_gate():
    associator = TrackAssociator(gate_threshold=4.0)

    # All candidates outside small gate
    c1 = MeasurementCandidate(candidate_id=1, centroid_x=400.0, centroid_y=300.0, confidence=0.9)
    c2 = MeasurementCandidate(candidate_id=2, centroid_x=100.0, centroid_y=100.0, confidence=0.9)

    x_pred = np.array([[320.0], [240.0], [0.0], [0.0]], dtype=np.float64)
    P_pred = np.diag([5.0, 5.0, 1.0, 1.0])

    res = associator.associate([c1, c2], x_pred, P_pred)

    assert res.associated is False
    assert res.selected_candidate is None
    assert len(res.rejected_candidates) == 2
    assert "rejected by Mahalanobis validation gate" in res.decision_reason
