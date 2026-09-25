"""Unit tests for Phase 11.0 Patch: Neutral Dark Palette & Typography Correction.
"""

import pytest
from PySide6.QtWidgets import QApplication
from simulator.ui.foundation.tokens import (
    COLOR_VOID,
    COLOR_FIELD,
    COLOR_FIELD_RAISED,
    COLOR_TEXT_PRIMARY,
    COLOR_TEXT_SECONDARY,
    FONT_BODY,
    FONT_TELEMETRY,
)
from simulator.ui.foundation.primitives import SectionHeaderLabel, StateIndicatorPill, StatePillState


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


def test_neutral_dark_palette():
    """Verify true neutral dark theme palette values (Patch 11.0)."""
    assert COLOR_VOID == "#0A0A0B"
    assert COLOR_FIELD == "#16161A"
    assert COLOR_FIELD_RAISED == "#202024"
    assert COLOR_TEXT_PRIMARY == "#F2F2F4"
    assert COLOR_TEXT_SECONDARY == "#8E8E96"


def test_typography_tokens():
    """Verify primary vs monospace font tokens."""
    assert "General Sans" in FONT_BODY
    assert "JetBrains Mono" in FONT_TELEMETRY


def test_section_header_title_case(qapp):
    """Verify section headers use Title Case instead of ALL CAPS."""
    lbl = SectionHeaderLabel("mission control parameters")
    assert lbl.text() == "Mission Control Parameters"


def test_state_pill_short_caps_tag(qapp):
    """Verify state pills enforce short all-caps state tags."""
    pill = StateIndicatorPill(StatePillState.ACTIVE, label_text="TRACK")
    assert pill.text().strip() == "TRACK"

    pill.set_state(StatePillState.SEARCHING if hasattr(StatePillState, "SEARCHING") else StatePillState.IDLE, label_text="SEARCH")
    assert pill.text().strip() == "SEARCH"

    pill.set_state(StatePillState.DEGRADED, label_text="DEGRADED")
    assert pill.text().strip() == "DEGRADED"

    pill.set_state(StatePillState.CONFIRMED, label_text="READY")
    assert pill.text().strip() == "READY"
