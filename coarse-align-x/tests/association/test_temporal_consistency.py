"""
Tests for temporal consistency gating and zero ground-truth leakage.
"""

import numpy as np
import pytest
from simulator.perception.consistency_features import compute_estimator_consistency, compute_temporal_agreement


def test_temporal_consistency_within_gate():
    cand_pos = (322.0, 241.0)
    pred_pos = (320.0, 240.0)
    pred_cov = np.diag([16.0, 16.0])

    is_valid, d2, score = compute_estimator_consistency(cand_pos, pred_pos, pred_cov, gate_threshold=9.21)

    assert is_valid is True
    assert d2 < 9.21
    assert score > 0.5


def test_temporal_consistency_outside_gate():
    cand_pos = (380.0, 300.0)
    pred_pos = (320.0, 240.0)
    pred_cov = np.diag([9.0, 9.0])

    is_valid, d2, score = compute_estimator_consistency(cand_pos, pred_pos, pred_cov, gate_threshold=9.21)

    assert is_valid is False
    assert d2 > 9.21
    assert score < 0.1
