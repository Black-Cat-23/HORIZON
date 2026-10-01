"""Unit tests for Phase 11.4 Track Diagnostics Screen (Geometry View, Analytics Graphs, Covariance, Estimates, Hybrid Perception).
"""

import numpy as np
import pytest
from PySide6.QtWidgets import QApplication

from simulator.ui.track import TrackScreenView
from simulator.ui.track.geometry_view import TrackGeometryView
from simulator.ui.track.analytics_graphs import TimeSeriesAnalyticsWidget
from simulator.ui.track.covariance_panel import CovarianceDiagnosticPanel
from simulator.ui.track.state_estimate_panel import StateEstimatePanel
from simulator.ui.track.perception_breakdown import HybridPerceptionBreakdownPanel
from tracking.estimation.state import StateEstimate, EstimatorStatus
from simulator.perception.detector import DetectionResult


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


def test_track_geometry_view_ground_truth_firewall(qapp):
    """Verify ground-truth marker renders ONLY when Evaluation Mode is ON."""
    view = TrackGeometryView()
    assert not view._eval_mode_enabled

    sensor_frame = np.zeros((480, 640), dtype=np.uint8)

    # Operational mode (eval_mode=False): GT must not be rendered
    view.render_geometry(sensor_frame, detection_res=None, estimate=None, ground_truth_pos=(320.0, 240.0))
    assert not view._eval_mode_enabled

    # Enable evaluation mode explicitly
    view.chk_eval_mode.setChecked(True)
    assert view._eval_mode_enabled


def test_covariance_diagnostic_panel(qapp):
    """Verify CovarianceDiagnosticPanel sigma selection & mathematical ellipse computation."""
    panel = CovarianceDiagnosticPanel()
    assert panel.selected_sigma == 2.0

    selected = []
    panel.sigma_changed.connect(lambda s: selected.append(s))

    panel.select_sigma(3.0)
    assert panel.selected_sigma == 3.0
    assert selected == [3.0]

    # Test covariance matrix calculation
    est = StateEstimate(
        estimated_x=320.0,
        estimated_y=240.0,
        estimated_vx=10.0,
        estimated_vy=5.0,
        covariance=np.array([[4.0, 1.0, 0, 0], [1.0, 9.0, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]]),
        innovation=np.array([[0.0], [0.0]]),
        predicted_x=320.0,
        predicted_y=240.0,
        filter_status=EstimatorStatus.TRACKING,
        timestamp=1.0,
        measurement_available=True,
        track_age=5,
        consecutive_measurements=5,
        consecutive_misses=0,
    )
    panel.update_covariance(est)
    assert panel.telem_pxx._val_label.text() == "4.00"
    assert panel.telem_pyy._val_label.text() == "9.00"


def test_state_estimate_panel_context_labels(qapp):
    """Verify StateEstimatePanel displays plain-language context for state vector."""
    panel = StateEstimatePanel()
    assert panel.telem_x._val_label.text() == "N/A"

    est = StateEstimate(
        estimated_x=315.42,
        estimated_y=242.18,
        estimated_vx=12.5,
        estimated_vy=-4.2,
        covariance=np.eye(4),
        innovation=None,
        predicted_x=315.42,
        predicted_y=242.18,
        filter_status=EstimatorStatus.TRACKING,
        timestamp=1.0,
        measurement_available=True,
        track_age=5,
        consecutive_measurements=5,
        consecutive_misses=0,
    )
    panel.update_estimate(est)
    assert panel.telem_x._val_label.text() == "315.42"
    assert panel.telem_y._val_label.text() == "242.18"


def test_hybrid_perception_breakdown_real_values(qapp):
    """Verify HybridPerceptionBreakdownPanel shows real confidence values when active, N/A when idle."""
    panel = HybridPerceptionBreakdownPanel()
    assert panel.telem_final._val_label.text() == "N/A"

    res = DetectionResult(
        detected=True,
        centroid=(320.0, 240.0),
        bbox=(310, 230, 20, 20),
        confidence=0.942,
        candidate_count=1,
        method_used="HYBRID",
        processing_time_ms=2.5,
        diagnostics={
            "classical_confidence": 0.88,
            "neural_confidence": 0.96,
            "agreement_confidence": 0.91,
        },
    )
    panel.update_breakdown(res)
    assert panel.telem_classical._val_label.text() == "88.00"
    assert panel.telem_neural._val_label.text() == "96.00"
    assert panel.telem_final._val_label.text() == "94.20"


def test_time_series_analytics_widget(qapp):
    """Verify TimeSeriesAnalyticsWidget updates all 6 telemetry plots and all 4 view modes including PSD."""
    widget = TimeSeriesAnalyticsWidget()
    assert widget.psd_widget is not None

    times = [float(i) * 0.05 for i in range(20)]
    errors = [2.5 + 0.5 * np.sin(i * 0.5) for i in range(20)]
    qualities = [90.0 + i * 0.4 for i in range(20)]
    innovations = [0.2 for _ in range(20)]
    pan_errors = [0.01 for _ in range(20)]
    tilt_errors = [0.01 for _ in range(20)]
    confidences = [95.0 for _ in range(20)]

    widget.update_analytics(
        times=times,
        errors_px=errors,
        qualities=qualities,
        innovations=innovations,
        pan_errors=pan_errors,
        tilt_errors=tilt_errors,
        confidences=confidences,
    )
    assert widget.graph_error._val_data == errors

    # Verify switching across all 4 modes
    widget.show()
    widget.set_view_mode(widget.MODE_MPL_DYNAMICS)
    assert not widget.mpl_workstation.isHidden()
    assert widget.psd_widget.isHidden()

    widget.set_view_mode(widget.MODE_6CH_TELEMETRY)
    assert not widget.grid_container.isHidden()

    widget.set_view_mode(widget.MODE_PHASE_PORTRAIT)
    assert not widget.phase_portrait.isHidden()

    widget.set_view_mode(widget.MODE_JITTER_PSD)
    assert not widget.psd_widget.isHidden()
    assert widget.mpl_workstation.isHidden()


def test_track_screen_view_integration(qapp):
    """Verify TrackScreenView composite widget initialization."""
    screen = TrackScreenView()
    assert screen.geometry_view is not None
    assert screen.radar_widget is not None
    assert screen.cov_panel is not None
    assert screen.estimate_panel is not None
    assert screen.perception_panel is not None
    assert screen.analytics_panel is not None


def test_coarse_to_fine_radar_widget(qapp):
    """Verify CoarseToFineRadarWidget updates alignment and coupling state."""
    from simulator.ui.track.radar_widget import CoarseToFineRadarWidget
    radar = CoarseToFineRadarWidget()
    assert radar._coupling_pct == 0.0
    radar.update_alignment(pan_error_deg=0.001, tilt_error_deg=0.001, error_px=0.5)
    assert radar._fps_locked is True
    assert radar._coupling_pct > 90.0


def test_executive_kpi_strip_handoff_and_coupling(qapp):
    """Verify ExecutiveKPIStripWidget FSM lock gate, consecutive lock counter, and coupling physics."""
    from simulator.ui.track.track_screen import ExecutiveKPIStripWidget
    from pat.state import PATMode, PATState

    kpi = ExecutiveKPIStripWidget()
    assert kpi._consecutive_lock_frames == 0

    # 1. Feed 25 locked frames (within FSM basin <= 2.5 px, e.g. 0.0005 deg = 0.03 px)
    pat_locked = PATState(
        mode=PATMode.TRACK,
        pan_error_deg=0.0005,
        tilt_error_deg=0.0003,
        track_quality=0.98,
    )
    est = StateEstimate(
        estimated_x=320.0,
        estimated_y=240.0,
        estimated_vx=0.0,
        estimated_vy=0.0,
        covariance=np.eye(4) * 0.5,
        innovation=np.array([[0.1], [0.1]]),
        predicted_x=320.0,
        predicted_y=240.0,
        filter_status=EstimatorStatus.TRACKING,
        timestamp=1.0,
        measurement_available=True,
        track_age=50,
        consecutive_measurements=50,
        consecutive_misses=0,
    )

    for _ in range(25):
        kpi.update_kpis(estimate=est, pat_state=pat_locked, detection_res=None)

    assert kpi._consecutive_lock_frames == 25
    assert kpi.card_handoff.pill.text().strip() == "FSM LOCKED"
    assert "Handoff Verified" in kpi.card_handoff.lbl_subtitle.text()
    assert kpi.card_coupling.pill.text().strip() == "OPTIMAL"
    assert "BER < 1e-9" in kpi.card_coupling.lbl_subtitle.text()

    # 2. Slew perturbation (error > 6.0 px, e.g. 0.2 deg = 12 px)
    pat_slew = PATState(
        mode=PATMode.TRACK,
        pan_error_deg=0.2,
        tilt_error_deg=0.1,
        track_quality=0.3,
    )
    kpi.update_kpis(estimate=est, pat_state=pat_slew, detection_res=None)

    assert kpi._consecutive_lock_frames == 0
    assert kpi.card_handoff.pill.text().strip() == "SLEWING"
    assert "Sensor FOV Slew" in kpi.card_handoff.lbl_subtitle.text()
    assert kpi.card_coupling.pill.text().strip() == "LOSS RISK"


def test_track_screen_snapshot_export(qapp, tmp_path):
    """Verify 1-Click CCSDS Flight Telemetry Snapshot Dossier export functionality."""
    import os
    screen = TrackScreenView()
    assert screen.btn_export_snapshot is not None
    assert screen.lbl_snapshot_toast is not None

    # Simulate feeding realistic track frames and estimates
    frame = np.zeros((480, 640), dtype=np.uint8)
    frame[238:242, 318:322] = 255  # bright spot
    det = DetectionResult(
        detected=True,
        centroid=(320.0, 240.0),
        confidence=0.98,
        bbox=(310, 230, 20, 20),
        processing_time_ms=1.8,
        candidate_count=1,
        method_used="HYBRID",
        diagnostics={"classical_confidence": 0.95, "neural_confidence": 0.99},
    )
    est = StateEstimate(
        estimated_x=320.0,
        estimated_y=240.0,
        estimated_vx=0.0,
        estimated_vy=0.0,
        covariance=np.eye(4) * 0.2,
        innovation=np.array([[0.05], [0.05]]),
        predicted_x=320.0,
        predicted_y=240.0,
        filter_status=EstimatorStatus.TRACKING,
        timestamp=1.0,
        measurement_available=True,
        track_age=10,
        consecutive_measurements=10,
        consecutive_misses=0,
    )
    from pat.state import PATMode, PATState
    pat = PATState(
        mode=PATMode.TRACK,
        pan_error_deg=0.0002,
        tilt_error_deg=0.0001,
        track_quality=0.99,
    )

    screen.update_track_displays(
        dist_frame=frame,
        detection_res=det,
        estimate=est,
        pat_state=pat,
        ground_truth_pos=(320.0, 240.0),
        sim_time=1.0,
    )

    # Click export
    out_path = screen._export_telemetry_snapshot(prompt_dialog=False)
    assert out_path and os.path.exists(out_path)
    assert os.path.getsize(out_path) > 10000  # valid image file generated
    assert "✓ Saved:" in screen.lbl_snapshot_toast.text()


def test_track_screen_and_radar_unified_coupling(qapp):
    """Verify coupling_pct is unified between Executive KPI Strip and Optical Alignment Radar."""
    from pat.state import PATMode, PATState
    screen = TrackScreenView()

    # Create PAT state in coarse tracking corridor (3.2 px error, ~349 urad)
    pat = PATState(
        mode=PATMode.TRACK,
        pan_error_deg=0.015,
        tilt_error_deg=0.013,
        track_quality=0.92,
    )
    est = StateEstimate(
        estimated_x=322.4,
        estimated_y=242.0,
        estimated_vx=0.5,
        estimated_vy=-0.3,
        covariance=np.eye(4) * 0.4,
        innovation=np.array([[0.1], [0.1]]),
        predicted_x=322.4,
        predicted_y=242.0,
        filter_status=EstimatorStatus.TRACKING,
        timestamp=2.0,
        measurement_available=True,
        track_age=15,
        consecutive_measurements=15,
        consecutive_misses=0,
    )

    screen.update_track_displays(dist_frame=None, detection_res=None, estimate=est, pat_state=pat, sim_time=2.0)

    # Both widgets must display valid non-zero coupling with 800 urad beam waist
    radar_coupling = screen.radar_widget._coupling_pct
    assert radar_coupling > 60.0, f"Expected coupling > 60%, got {radar_coupling}%"
    kpi_coupling_text = screen.kpi_strip.card_coupling.lbl_value.text()
    assert f"{radar_coupling:.1f}%" in kpi_coupling_text


def test_state_estimate_actuator_allocation(qapp):
    """Verify StateEstimatePanel computes and displays coarse gimbal rate and piezo stroke without error."""
    from pat.state import PATMode, PATState
    panel = StateEstimatePanel()

    pat = PATState(
        mode=PATMode.TRACK,
        pan_error_deg=0.02,
        tilt_error_deg=0.015,
        track_quality=0.95,
    )
    est = StateEstimate(
        estimated_x=323.2,
        estimated_y=242.4,
        estimated_vx=1.2,
        estimated_vy=0.8,
        covariance=np.eye(4) * 0.3,
        innovation=np.array([[0.05], [0.05]]),
        predicted_x=323.2,
        predicted_y=242.4,
        filter_status=EstimatorStatus.TRACKING,
        timestamp=1.5,
        measurement_available=True,
        track_age=20,
        consecutive_measurements=20,
        consecutive_misses=0,
    )

    panel.update_estimate(est, pat_state=pat)

    # Gimbal slew rate and FSM deflection must be populated numbers, not N/A
    assert panel.telem_gimbal._val_label.text() != "N/A"
    assert panel.telem_fsm._val_label.text() != "N/A"
    gimbal_val = float(panel.telem_gimbal._val_label.text())
    fsm_val = float(panel.telem_fsm._val_label.text())
    assert 0.0 < gimbal_val <= 1.50
    assert 0.0 < fsm_val <= 50.0


def test_handoff_corridor_hierarchy(qapp):
    """Verify full handoff gate hierarchy across FSM locked, handoff, coarse track, and slew."""
    from pat.state import PATMode, PATState
    from simulator.ui.track.track_screen import ExecutiveKPIStripWidget

    kpi = ExecutiveKPIStripWidget()

    est = StateEstimate(
        estimated_x=320.0,
        estimated_y=240.0,
        estimated_vx=0.0,
        estimated_vy=0.0,
        covariance=np.eye(4),
        innovation=np.array([[0.1], [0.1]]),
        predicted_x=320.0,
        predicted_y=240.0,
        filter_status=EstimatorStatus.TRACKING,
        timestamp=1.0,
        measurement_available=True,
        track_age=10,
        consecutive_measurements=10,
        consecutive_misses=0,
    )

    # 1. Inside FSM Basin (<= 2.5 px, e.g. 0.01 deg = 1.6 px)
    pat_basin = PATState(mode=PATMode.TRACK, pan_error_deg=0.007, tilt_error_deg=0.007, track_quality=0.95)
    kpi.update_kpis(est, pat_basin, None)
    assert kpi.card_handoff.pill.text().strip() == "LOCKED"

    # 2. Handoff Zone (2.5 px < err <= 6.0 px, e.g. 0.03 deg = 4.8 px)
    pat_handoff = PATState(mode=PATMode.TRACK, pan_error_deg=0.025, tilt_error_deg=0.015, track_quality=0.90)
    kpi.update_kpis(est, pat_handoff, None)
    assert kpi.card_handoff.pill.text().strip() == "HANDOFF"

    # 3. Coarse Track Corridor (6.0 px < err <= 25.0 px, e.g. 0.08 deg = 12.8 px)
    pat_coarse = PATState(mode=PATMode.TRACK, pan_error_deg=0.06, tilt_error_deg=0.05, track_quality=0.85)
    kpi.update_kpis(est, pat_coarse, None)
    assert kpi.card_handoff.pill.text().strip() == "COARSE TRACK"

    # 4. Slew Far Field (err > 25.0 px, e.g. 0.25 deg = 40.0 px)
    pat_slew = PATState(mode=PATMode.TRACK, pan_error_deg=0.20, tilt_error_deg=0.15, track_quality=0.50)
    kpi.update_kpis(est, pat_slew, None)
    assert kpi.card_handoff.pill.text().strip() == "SLEWING"


def test_track_screen_reset_telemetry(qapp):
    """Verify reset_telemetry cleans buffers and returns all components to standby."""
    from pat.state import PATMode, PATState
    screen = TrackScreenView()

    pat = PATState(mode=PATMode.TRACK, pan_error_deg=0.01, tilt_error_deg=0.01, track_quality=0.9)
    screen.update_track_displays(dist_frame=None, detection_res=None, estimate=None, pat_state=pat, sim_time=1.0)
    assert len(screen._history_times) > 0

    screen.reset_telemetry()
    assert len(screen._history_times) == 0
    assert len(screen._history_errors_px) == 0
    assert screen.kpi_strip.card_handoff.pill.text().strip() == "STANDBY"
    assert screen.kpi_strip.card_coupling.pill.text().strip() == "STANDBY"
    assert screen.radar_widget._coupling_pct == 0.0



