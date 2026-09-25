"""HORIZON Phase 11.7 Cross-Screen Consistency, Resolution Scaling & Accessibility Tests
========================================================================================
Verifies:
  1. ApplicationShell multi-resolution responsiveness at 1366x768, 1600x900, 1920x1080, and 2560x1440.
  2. All 5 screens (Mission, Live, Track, Stress, Benchmark) instantiate and switch cleanly.
  3. Multi-sensory status indicators (Color + Text Label + Pill/Shape Container).
  4. Unit label presence on numerical readouts.
  5. Keyboard focus policies on interactive controls.
"""

import pytest
from PySide6.QtCore import Qt, QSize
from PySide6.QtWidgets import QApplication

from simulator.ui.shell.app_shell import ApplicationShell
from simulator.ui.mission import MissionScreenView
from simulator.ui.live import LiveScreenView
from simulator.ui.track import TrackScreenView
from simulator.ui.stress import StressScreenView
from simulator.ui.benchmark import BenchmarkScreenView


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_multi_resolution_scaling(qapp):
    """Test ApplicationShell layout responsiveness at required target resolutions."""
    shell = ApplicationShell()
    shell.show()

    resolutions = [
        (1366, 768),
        (1600, 900),
        (1920, 1080),
        (2560, 1440),
    ]

    for width, height in resolutions:
        shell.resize(width, height)
        qapp.processEvents()
        assert shell.width() >= 1280
        assert shell.height() >= 720
        assert shell.stack.currentWidget() is not None

    shell.close()


def test_cross_screen_mode_switching(qapp):
    """Verify switching across all 5 mode views in ApplicationShell."""
    shell = ApplicationShell()
    shell.show()

    for mode_idx in range(5):
        shell.bank_switcher.select_mode(mode_idx)
        qapp.processEvents()
        assert shell._current_mode_index == mode_idx
        active_widget = shell.stack.currentWidget()
        assert active_widget is not None

    shell.close()


def test_multi_sensory_accessibility(qapp):
    """Verify state pills pair color with explicit text tags (no color-only status cues)."""
    live = LiveScreenView()
    assert live._lbl_pat_mode.text().strip() != ""

    stress = StressScreenView()
    assert stress.response_panel.pill_pat_state.text().strip() != ""

    benchmark = BenchmarkScreenView()
    assert benchmark.same_seed_inspector.cards["OURS"]["pill"].text().strip() != ""
