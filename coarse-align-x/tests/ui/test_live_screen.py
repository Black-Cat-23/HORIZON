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
    assert screen._combo_perc_mode.currentText() in ("HYBRID", "SOTA_FOURIER_GMM")
    assert screen._combo_preset.currentText() == "NOMINAL"


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
    # Simulate what the UI does: set the combo THEN the handler fires
    screen._combo_perc_mode.setCurrentText("NEURAL")
    # Handler reads from combo, so _perception_mode should now be NEURAL
    assert screen._perception_mode == "NEURAL"
    # Verify detector instance changed to neural
    from simulator.perception.neural_detector import NeuralBeaconDetector
    assert isinstance(screen._detector, NeuralBeaconDetector)


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


def test_live_screen_apply_mission_config(qapp):
    """Verify apply_mission_config applies custom configuration from Mission Setup."""
    from simulator.core.config import AppConfig, TrajectoryConfig, SimulationConfig, CircularTrajectoryConfig
    from simulator.disturbances.presets import get_preset_config

    screen = LiveScreenView()
    custom_cfg = AppConfig(
        simulation=SimulationConfig(seed=987, duration_seconds=15.0),
        trajectory=TrajectoryConfig(type="circular", circular=CircularTrajectoryConfig(radius=150.0)),
        disturbance=get_preset_config("DIFFICULT"),
    )
    screen.apply_mission_config(custom_cfg)

    assert screen._config.simulation.seed == 987
    assert screen._config.simulation.duration_seconds == 15.0
    assert screen._config.trajectory.type == "circular"
    assert screen._combo_traj.currentText() == "circular"
    assert screen._spin_seed.value() == 987
    assert screen._spin_duration.value() == 15.0
    assert screen._combo_preset.currentText() == "DIFFICULT"
    assert screen._engine is not None
    assert screen._engine.is_running is True


def test_live_screen_external_video_ingestion(qapp, tmp_path):
    """Verify loading and processing external MP4 video file (ISRO Performance-2 requirement)."""
    import os
    import time

    video_path = "data/samples/isro_square_beacon_evaluation_30s.mp4"
    if not os.path.exists(video_path):
        video_path = "data/samples/isro_sample_beacon_30s.mp4"

    screen = LiveScreenView()
    success = screen.load_video_source(video_path)
    assert success is True
    assert screen._input_source == "EXTERNAL_VIDEO"
    assert screen._video_source is not None
    assert screen._video_source.is_open() is True
    assert len(screen._video_gt_data) > 0

    # Step through 5 frames
    for _ in range(5):
        screen._execute_video_step(time.perf_counter())

    assert len(screen._video_log_records) == 5
    first_rec = screen._video_log_records[0]
    assert first_rec["frame_idx"] == 0
    assert first_rec["detected"] == 1
    assert isinstance(first_rec["centroid_u"], float)
    assert isinstance(first_rec["centroid_v"], float)
    assert first_rec["centroid_error_px"] != ""
    assert float(first_rec["centroid_error_px"]) < 10.0

    # Test export to CSV
    out_csv = tmp_path / "test_centroid_export.csv"
    import csv
    fieldnames = list(first_rec.keys())
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(screen._video_log_records)

    assert out_csv.exists()
    assert out_csv.stat().st_size > 0


def test_live_to_track_external_video_end_to_end(qapp):
    """Verify end-to-end signal streaming from LiveScreenView to TrackScreenView in EXTERNAL_VIDEO mode."""
    import os
    import time
    from simulator.ui.track import TrackScreenView

    video_path = "data/samples/isro_square_beacon_evaluation_30s.mp4"
    if not os.path.exists(video_path):
        video_path = "data/samples/isro_sample_beacon_test.mp4"

    live_screen = LiveScreenView()
    track_screen = TrackScreenView()

    # Wire signal exactly as in AppShell
    live_screen.track_data_ready.connect(track_screen.update_track_displays)
    live_screen.simulation_reset.connect(track_screen.reset_telemetry)

    success = live_screen.load_video_source(video_path)
    assert success is True
    assert len(track_screen._history_times) == 0

    # Step through 30 frames
    for _ in range(30):
        live_screen._execute_video_step(time.perf_counter())

    # Verify Track Screen received telemetry
    assert len(track_screen._history_times) == 30
    assert len(track_screen._history_errors_px) == 30

    # Verify radar and KPI coupling synchronization
    radar_coupling = track_screen.radar_widget._coupling_pct
    assert radar_coupling > 0.0
    kpi_coupling_text = track_screen.kpi_strip.card_coupling.lbl_value.text()
    assert f"{radar_coupling:.1f}%" in kpi_coupling_text

    # Verify StateEstimatePanel updated without error
    assert track_screen.estimate_panel.telem_x._val_label.text() != "N/A"

    # Test reset signal
    live_screen._reset_sim()
    assert len(track_screen._history_times) == 0
    assert track_screen.kpi_strip.card_handoff.pill.text().strip() == "STANDBY"


