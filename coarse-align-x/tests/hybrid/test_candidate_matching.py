"""
Unit tests for Phase 8 perception candidate matching and IoU computation.
"""

import pytest
from simulator.perception.candidate_matcher import (
    CandidateMatcher,
    compute_centroid_distance,
    compute_iou,
)
from simulator.perception.hybrid_candidate import CandidateSource, UnifiedCandidate


def test_iou_identical_boxes():
    bbox = (10, 10, 20, 20)
    assert compute_iou(bbox, bbox) == pytest.approx(1.0)


def test_iou_disjoint_boxes():
    bbox1 = (10, 10, 20, 20)
    bbox2 = (100, 100, 20, 20)
    assert compute_iou(bbox1, bbox2) == pytest.approx(0.0)


def test_iou_partial_overlap():
    bbox1 = (0, 0, 10, 10)  # Area 100
    bbox2 = (5, 0, 10, 10)  # Inter (5,0,5,10)=50, Union=150
    assert compute_iou(bbox1, bbox2) == pytest.approx(50.0 / 150.0)


def test_centroid_distance():
    c1 = (10.0, 10.0)
    c2 = (13.0, 14.0)
    assert compute_centroid_distance(c1, c2) == pytest.approx(5.0)


def test_candidate_matcher_matching():
    matcher = CandidateMatcher(max_centroid_distance_px=20.0, min_iou_threshold=0.1)

    cand_c = UnifiedCandidate(
        candidate_id="C0",
        centroid_x=100.0,
        centroid_y=100.0,
        bbox_x=90,
        bbox_y=90,
        bbox_width=20,
        bbox_height=20,
        area=400.0,
        classical_confidence=0.9,
        source=CandidateSource.CLASSICAL,
    )

    cand_n = UnifiedCandidate(
        candidate_id="N0",
        centroid_x=102.0,
        centroid_y=101.0,
        bbox_x=92,
        bbox_y=91,
        bbox_width=20,
        bbox_height=20,
        area=400.0,
        neural_confidence=0.85,
        source=CandidateSource.NEURAL,
    )

    matched, un_c, un_n = matcher.match_candidates([cand_c], [cand_n])

    assert len(matched) == 1
    assert len(un_c) == 0
    assert len(un_n) == 0
    assert matched[0].fused_candidate.source == CandidateSource.BOTH
