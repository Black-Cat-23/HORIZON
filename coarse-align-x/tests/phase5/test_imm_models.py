"""
Phase 5 IMM Model Structure & Probability Invariants Tests
"""

import numpy as np
import pytest
from tracking.estimation.imm_kalman import InteractingMultipleModelFilter
from tracking.estimation.state import EstimatorStatus


def test_imm_3_models_initialization():
    imm = InteractingMultipleModelFilter()
    assert not imm.is_initialized
    assert imm.status == EstimatorStatus.UNINITIALIZED

    est = imm.initialize((320.0, 240.0), timestamp=0.0)
    assert imm.is_initialized
    assert imm.status == EstimatorStatus.TRACKING
    assert est.estimated_x == 320.0
    assert est.estimated_y == 240.0


def test_imm_model_probabilities_sum_to_one():
    imm = InteractingMultipleModelFilter()
    imm.initialize((320.0, 240.0), timestamp=0.0)

    for i in range(10):
        t = 0.05 * (i + 1)
        meas = (320.0 + i * 2.0, 240.0 + i * 1.5)
        est = imm.step(meas, confidence=0.9, timestamp=t)
        probs = imm.mode_probabilities
        assert len(probs) == 3
        assert pytest.approx(sum(probs), abs=1e-5) == 1.0
        assert all(p >= 0.0 for p in probs)
