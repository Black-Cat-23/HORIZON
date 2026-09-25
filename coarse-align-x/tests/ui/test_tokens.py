"""
Unit tests for Phase 11.0 Design Tokens
"""

from simulator.ui.foundation.tokens import (
    COLOR_VOID,
    COLOR_FIELD,
    COLOR_FIELD_RAISED,
    COLOR_LOCK_CYAN,
    COLOR_CONFIRM_GREEN,
    COLOR_DISTURBANCE_AMBER,
    COLOR_LOST_RED,
    VALID_SPACING_VALUES,
    DURATION_MICRO_MS,
    DURATION_COMPONENT_MS,
    DURATION_SCREEN_MS,
)


def test_token_colors():
    assert COLOR_VOID == "#0A0A0B"
    assert COLOR_FIELD == "#16161A"
    assert COLOR_FIELD_RAISED == "#202024"
    assert COLOR_LOCK_CYAN == "#7FD4E8"
    assert COLOR_CONFIRM_GREEN == "#6FE8A8"
    assert COLOR_DISTURBANCE_AMBER == "#E8A15C"
    assert COLOR_LOST_RED == "#E86F7F"


def test_spacing_scale():
    expected_spacing = {4, 8, 12, 16, 24, 32, 48, 64}
    assert VALID_SPACING_VALUES == expected_spacing


def test_motion_durations():
    assert DURATION_MICRO_MS == 120
    assert DURATION_COMPONENT_MS == 200
    assert DURATION_SCREEN_MS == 320
