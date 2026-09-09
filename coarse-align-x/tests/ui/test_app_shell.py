"""Unit tests for Phase 11.1 Application Shell & Navigation Bank.
"""

import pytest
from PySide6.QtWidgets import QApplication
from simulator.ui.shell import GlobalHeader, ModeSelectorBank, ModePlaceholderView, ApplicationShell
from simulator.ui.foundation.primitives import StatePillState


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


def test_global_header_initialization(qapp):
    """Verify GlobalHeader renders title, truthful idle pills, and FPS readout."""
    header = GlobalHeader()
    assert header.height() == 64
    assert header.wordmark.text() == "HORIZON"
    assert header.pill_runtime.text().strip() == "READY"
    assert header.pill_pat.text().strip() == "READY"
    assert header.telem_fps._val_label.text() == "N/A"


def test_global_header_status_updates(qapp):
    """Verify GlobalHeader updates runtime status, PAT status, and FPS values."""
    header = GlobalHeader()
    header.set_runtime_status(StatePillState.ACTIVE, "TRACK")
    assert header.pill_runtime.text().strip() == "TRACK"

    header.set_fps(59.8)
    assert header.telem_fps._val_label.text() == "59.80"


def test_mode_selector_bank_modes(qapp):
    """Verify ModeSelectorBank handles all 5 modes and emits mode_changed signals."""
    bank = ModeSelectorBank()
    recorded_modes = []
    bank.mode_changed.connect(lambda idx: recorded_modes.append(idx))

    assert bank.current_index == 0  # Mission Control default

    bank.select_mode(1)  # Live Tracking
    assert bank.current_index == 1
    assert recorded_modes == [1]

    bank.select_mode(4)  # Benchmark
    assert bank.current_index == 4
    assert recorded_modes == [1, 4]


def test_mode_placeholder_view(qapp):
    """Verify ModePlaceholderView initializes with mode_index."""
    view = ModePlaceholderView(mode_index=3)
    assert view.mode_index == 3


def test_application_shell_mode_switching(qapp):
    """Verify ApplicationShell switches screens correctly."""
    shell = ApplicationShell()
    assert shell.bank_switcher.current_index == 1
    assert shell.stack.currentIndex() == 1

    shell.bank_switcher.select_mode(2)
    assert shell.bank_switcher.current_index == 2
    assert shell.stack.currentIndex() == 2
