"""
Unit tests for Phase 11.0 Base Component Primitives
"""

import pytest
from PySide6.QtWidgets import QApplication
from simulator.ui.foundation.primitives import (
    PanelSurface,
    PanelVariant,
    PrimaryButton,
    SecondaryButton,
    StateIndicatorPill,
    StatePillState,
    MonospaceTelemetryLabel,
    SectionHeaderLabel,
    ExpandableDiagnosticContainer,
)


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


def test_panel_surface(qapp):
    panel = PanelSurface(PanelVariant.FIELD)
    assert panel.variant == PanelVariant.FIELD
    panel.set_variant(PanelVariant.FIELD_RAISED)
    assert panel.variant == PanelVariant.FIELD_RAISED


def test_state_pill(qapp):
    pill = StateIndicatorPill(StatePillState.ACTIVE)
    assert pill.state == StatePillState.ACTIVE
    pill.set_state(StatePillState.CONFIRMED)
    assert pill.state == StatePillState.CONFIRMED


def test_telemetry_label_na_state(qapp):
    lbl = MonospaceTelemetryLabel(value=None, unit="px")
    assert lbl._val_label.text() == "N/A"

    lbl.set_value(12.345, "px")
    assert lbl._val_label.text() == "12.35"


def test_section_header_label(qapp):
    lbl = SectionHeaderLabel("test section")
    assert lbl.text() == "Test Section"


def test_collapsible_container(qapp):
    container = ExpandableDiagnosticContainer("Diagnostics")
    assert not container.is_expanded
    assert container.content_widget.isHidden()

    container.toggle()
    assert container.is_expanded
    assert not container.content_widget.isHidden()
