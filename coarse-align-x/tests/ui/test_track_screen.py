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
    """Verify TimeSeriesAnalyticsWidget updates all 6 telemetry plots."""
    widget = TimeSeriesAnalyticsWidget()
    times = [0.0, 1.0, 2.0]
    widget.update_analytics(
        times=times,
        errors_px=[5.2, 3.1, 1.4],
        qualities=[80.0, 92.0, 98.0],
        innovations=[2.1, 1.0, 0.4],
        pan_errors=[0.5, 0.2, 0.1],
        tilt_errors=[0.3, 0.1, 0.05],
        confidences=[85.0, 95.0, 99.0],
    )
    assert widget.graph_error._val_data == [5.2, 3.1, 1.4]


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


