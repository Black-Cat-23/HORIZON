"""
Unit Tests for Uncertainty-Aware Gain Scheduling and Gating.
HORIZON Phase 6
"""

import pytest
from pat.state import PATMode, PATState
from control.gain_scheduler import GainScheduler, ScheduledGains


def test_uncertainty_gain_scaling_continuous_interpolation():
    """Verifies that gain scheduler smoothly transitions from DEGRADED to full TRACK gains."""
    scheduler = GainScheduler(
        kp_track=2.0, kp_degraded=0.5,
        ki_track=0.1, ki_degraded=0.0,
        kd_track=0.1, kd_degraded=0.3,
    )

    # Low quality (<= 0.3) -> DEGRADED gains
    g_low = scheduler.get_gains(PATMode.TRACK, track_quality=0.2, continuous_interpolation=True)
    assert g_low.kp == pytest.approx(0.5)
    assert g_low.ki == pytest.approx(0.0)
    assert g_low.kd == pytest.approx(0.3)

    # High quality (>= 0.8) -> full TRACK gains
    g_high = scheduler.get_gains(PATMode.TRACK, track_quality=0.9, continuous_interpolation=True)
    assert g_high.kp == pytest.approx(2.0)
    assert g_high.ki == pytest.approx(0.1)
    assert g_high.kd == pytest.approx(0.1)

    # Mid quality (0.55) -> intermediate interpolated gains
    g_mid = scheduler.get_gains(PATMode.TRACK, track_quality=0.55, continuous_interpolation=True)
    assert 0.5 < g_mid.kp < 2.0
    assert 0.0 < g_mid.ki < 0.1
    assert 0.1 < g_mid.kd < 0.3


def test_uncertainty_gain_inactive_during_search():
    """Verifies that gains are zeroed during open-loop search and reacquisition."""
    scheduler = GainScheduler()
    g_search = scheduler.get_gains(PATMode.SEARCH, track_quality=1.0)
    g_reacq = scheduler.get_gains(PATMode.REACQUIRE, track_quality=1.0)

    assert g_search.kp == 0.0 and g_search.ki == 0.0 and g_search.kd == 0.0
    assert g_reacq.kp == 0.0 and g_reacq.ki == 0.0 and g_reacq.kd == 0.0
