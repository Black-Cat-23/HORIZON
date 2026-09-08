"""
Unit and Integration tests for Adaptive Belief-Map Search Strategy.
HORIZON — SIH 2026 PS SIH26169 (PDF Section 6.4)
"""

import math
import numpy as np
import pytest

from pat.search.belief_map import BeliefMapSearchStrategy
from pat.search.search_manager import SearchManager
from pat.mode_manager import PATModeManager
from pat.state import PATMode


def test_belief_map_initialization_and_reset():
    strat = BeliefMapSearchStrategy(
        span_pan_deg=10.0,
        span_tilt_deg=8.0,
        grid_resolution_deg=0.5,
        prior_sigma_deg=1.5,
    )
    # Check dimensions
    assert strat.pan_coords.shape[0] > 10
    assert strat.tilt_coords.shape[0] > 10
    assert strat.belief_grid.shape == (strat.tilt_coords.shape[0], strat.pan_coords.shape[0])

    # Reset around specific center
    center_pan, center_tilt = 1.0, -1.0
    strat.reset(center_pan, center_tilt)

    # Probability mass must sum to 1.0
    assert np.isclose(np.sum(strat.belief_grid), 1.0, atol=1e-5)

    # Peak of Gaussian prior should be at center
    peak_pan, peak_tilt, peak_prob = strat.get_peak_location()
    assert abs(peak_pan - center_pan) <= 0.5
    assert abs(peak_tilt - center_tilt) <= 0.5
    assert peak_prob > 0.0


def test_bayesian_evidence_update():
    strat = BeliefMapSearchStrategy(
        span_pan_deg=10.0,
        span_tilt_deg=8.0,
        grid_resolution_deg=0.5,
        prior_sigma_deg=2.0,
    )
    strat.reset(0.0, 0.0)

    # Candidate detection offset at (+3.0, +2.0)
    cand_pan, cand_tilt = 3.0, 2.0
    prior_prob_at_cand = strat.belief_grid[
        np.argmin(abs(strat.tilt_coords - cand_tilt)),
        np.argmin(abs(strat.pan_coords - cand_pan)),
    ]

    # Provide weak/moderate candidate evidence
    strat.update_belief(cand_pan, cand_tilt, confidence=0.8, uncertainty_deg=0.5)

    # Probability at candidate location must increase significantly
    post_prob_at_cand = strat.belief_grid[
        np.argmin(abs(strat.tilt_coords - cand_tilt)),
        np.argmin(abs(strat.pan_coords - cand_pan)),
    ]
    assert post_prob_at_cand > prior_prob_at_cand

    # Overall map still normalized to 1.0
    assert np.isclose(np.sum(strat.belief_grid), 1.0, atol=1e-5)

    # Peak should now be attracted towards candidate position
    peak_pan, peak_tilt, _ = strat.get_peak_location()
    assert abs(peak_pan - cand_pan) < 1.0
    assert abs(peak_tilt - cand_tilt) < 1.0


def test_camera_steering_towards_peak():
    strat = BeliefMapSearchStrategy(
        span_pan_deg=10.0,
        span_tilt_deg=8.0,
        grid_resolution_deg=0.5,
        scan_speed_deg_s=2.0,
    )
    strat.reset(0.0, 0.0)

    # Plant a high-probability region to the right (+3.0 deg pan)
    strat.update_belief(candidate_pan_deg=3.0, candidate_tilt_deg=0.0, confidence=0.9)

    # Camera currently at (0.0, 0.0) should command positive pan rate
    cmd_pan, cmd_tilt = strat.next_command(dt=0.1, current_pan_deg=0.0, current_tilt_deg=0.0)
    assert cmd_pan > 0.0  # Steers right towards the belief peak
    assert abs(cmd_tilt) < abs(cmd_pan)


def test_negative_information_discounting():
    strat = BeliefMapSearchStrategy(
        span_pan_deg=6.0,
        span_tilt_deg=6.0,
        grid_resolution_deg=0.5,
        discount_rate=0.8,
        fov_radius_deg=1.0,
    )
    strat.reset(0.0, 0.0)

    _, _, initial_center_prob = strat.get_peak_location()

    # Repeatedly hover at (0.0, 0.0) with no detection
    for _ in range(10):
        strat.next_command(dt=0.2, current_pan_deg=0.0, current_tilt_deg=0.0)

    center_idx_pan = np.argmin(abs(strat.pan_coords - 0.0))
    center_idx_tilt = np.argmin(abs(strat.tilt_coords - 0.0))
    new_center_prob = strat.belief_grid[center_idx_tilt, center_idx_pan]

    # Center belief must be discounted due to negative evidence
    assert new_center_prob < initial_center_prob


def test_search_manager_integration():
    mgr = SearchManager()
    assert "BELIEF_MAP" in mgr.strategies

    mgr.set_active_strategy("BELIEF_MAP")
    assert mgr.active_strategy_name == "BELIEF_MAP"

    mgr.reset_active_strategy(center_pan_deg=1.0, center_tilt_deg=1.0)
    strat = mgr.get_active_strategy()
    assert isinstance(strat, BeliefMapSearchStrategy)

    # Check update_belief forwarding
    mgr.update_belief(candidate_pan_deg=2.5, candidate_tilt_deg=1.5, confidence=0.7)
    peak_pan, peak_tilt, _ = strat.get_peak_location()
    assert abs(peak_pan - 2.5) < 1.0

    cmd_pan, cmd_tilt = mgr.get_command(dt=0.1, current_pan_deg=1.0, current_tilt_deg=1.0)
    assert abs(cmd_pan) > 0.0 or abs(cmd_tilt) > 0.0


def test_pat_mode_manager_integration_with_belief_map():
    pat = PATModeManager()
    pat.search_manager.set_active_strategy("BELIEF_MAP")
    pat.search_manager.reset_active_strategy(0.0, 0.0)

    assert pat.state.mode == PATMode.SEARCH

    # Process search step
    state = pat.process_step(
        dt=0.05,
        timestamp_s=0.05,
        detection_valid=False,
        detection_confidence=0.0,
        mahalanobis_d2=0.0,
        covariance_trace=1.0,
        estimated_u_px=0.0,
        estimated_v_px=0.0,
        estimated_vx_px_s=0.0,
        estimated_vy_px_s=0.0,
        current_pan_deg=0.0,
        current_tilt_deg=0.0,
    )
    assert state.mode == PATMode.SEARCH
    assert state.active_search_strategy == "BELIEF_MAP"

