"""
Unit tests for Phase 8 perception consistency feature scoring.
"""

import pytest
import numpy as np
from simulator.perception.consistency_features import (
    compute_optical_agreement,
    compute_size_agreement,
    compute_spatial_agreement,
    compute_temporal_agreement,
)


def test_spatial_agreement_bounds():
    assert compute_spatial_agreement(0.0) == pytest.approx(1.0)
    assert 0.0 <= compute_spatial_agreement(50.0) <= 1.0


def test_size_agreement_bounds():
    assert compute_size_agreement(100.0, 100.0) == pytest.approx(1.0)
    assert compute_size_agreement(50.0, 100.0) == pytest.approx(0.5)
    assert compute_size_agreement(0.0, 100.0) == pytest.approx(0.0)


def test_optical_agreement_bounds():
    assert compute_optical_agreement(60.0, 10.0) == pytest.approx(1.0)
    assert compute_optical_agreement(None, None) == pytest.approx(0.5)


def test_temporal_agreement_mahalanobis():
    cand_pos = (100.0, 100.0)
    pred_pos = (100.0, 100.0)
    cov = np.eye(2) * 10.0

    score = compute_temporal_agreement(cand_pos, pred_pos, cov)
    assert score == pytest.approx(1.0)

    score_far = compute_temporal_agreement((150.0, 150.0), pred_pos, cov)
    assert score_far < score
