"""Unit tests for Phase 11.2 Live Screen Replica (Dual Sensors, World Overview, Telemetry, Controls, Timeline).
"""

import numpy as np
import pytest
from PySide6.QtWidgets import QApplication

from simulator.ui.live import LiveScreenView
from simulator.ui.live.world_overview_panel import WorldOverviewPanel
from simulator.ui.live.event_timeline import EventTimelineWidget
from pat.state import PATMode, PATState


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


def test_live_screen_view_initialization(qapp):
    """Verify LiveScreenView composite widget initialization."""
    screen = LiveScreenView()
    assert screen._engine is not None
    assert screen._pat_mgr is not None
    assert screen._clean_cam_label is not None
    assert screen._dist_cam_label is not None
    assert screen._combo_perc_mode.currentText() == "SOTA_FOURIER_GMM"
    assert screen._combo_preset.currentText() == "DIFFICULT"


def test_live_screen_view_stepping(qapp):
    """Verify LiveScreenView simulation step execution & frame updates."""
    screen = LiveScreenView()
    screen._execute_sim_step()
    assert screen._engine.clock.current_frame == 1
    assert screen._lbl_time.text() != "0.000 s"


def test_live_screen_preset_change(qapp):
    """Verify live disturbance preset change updates configuration."""
    screen = LiveScreenView()
    screen._on_preset_changed("SEVERE")
    assert screen._combo_preset.currentText() == "SEVERE"
    assert screen._config.disturbance.enabled is True


def test_live_screen_perception_mode_change(qapp):
    """Verify changing perception mode updates internal detector."""
    screen = LiveScreenView()
    screen._on_perc_mode_changed("NEURAL")
    assert screen._perception_mode == "NEURAL"
    assert screen._lbl_status.text() == "Perception Mode: NEURAL"


def test_live_screen_blackout_test_toggle(qapp):
    """Verify blackout detection test toggle."""
    screen = LiveScreenView()
    screen._toggle_blackout_test(True)
    assert screen._suppress_detection_test is True
    screen._toggle_blackout_test(False)
    assert screen._suppress_detection_test is False


def test_world_overview_panel_update(qapp):
    """Verify WorldOverviewPanel updates 2000x2000 macro view."""
    panel = WorldOverviewPanel()
    world_frame = np.zeros((2000, 2000), dtype=np.uint8)
    pat_state = PATState(mode=PATMode.TRACK)

    panel.update_world_display(
        world_frame=world_frame,
        target_pos=(1000.0, 1000.0),
        boresight_pos=(1000.0, 1000.0),
        path_history=[(1000.0, 1000.0), (1005.0, 1005.0)],
        pat_state=pat_state,
    )
    assert panel.canvas_label.pixmap() is not None


def test_event_timeline_widget(qapp):
    """Verify EventTimelineWidget records timestamped events."""
    timeline = EventTimelineWidget()
    assert len(timeline._records) == 0

    timeline.add_event(1.23, "SEARCH", "Initial search sequence started")
    assert len(timeline._records) == 1

    timeline.clear_events()
    assert len(timeline._records) == 0
