"""HORIZON Phase 11.4 Track Screen View Component
=================================================
Composite main view for Mode 2 ("Track Diagnostics & Precision Analysis Workstation").
Integrates:
  - TOP STRIP: Executive Mission KPI Header Strip (Handoff Gate, Link Coupling η, NIS Consistency, Track Integrity)
  - LEFT/CENTER TOP: Track Geometry View (Dual-Mode: 640x480 Full FOV & 12x Subpixel Laser Microscope)
  - LEFT/CENTER MIDDLE: Polar Coarse-to-Fine Alignment Radar
  - LEFT/CENTER BOTTOM: Time-Series Analytics Panel (6-Channel Graphs & Lyapunov Phase-Plane Portrait)
  - RIGHT TOP: Covariance Diagnostic Panel (Reactive 1σ/2σ/3σ controls, Dynamic Bounds, 2D Vector Compass)
  - RIGHT MIDDLE: State Estimate Vector Panel (Plain-language context labels, State Vector)
  - RIGHT BOTTOM: Hybrid Perception Breakdown Panel (Classical, Neural, Agreement, Final confidence readouts)

Strict Ground-Truth Firewall: Ground-truth marker appears ONLY in Evaluation Mode (OFF by default) and NEVER influences any backend algorithm.
"""

from __future__ import annotations
import logging
import math
import time
from typing import List, Optional, Tuple
import cv2
import numpy as np

logger = logging.getLogger(__name__)

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from simulator.perception.detector import DetectionResult
from tracking.estimation.state import StateEstimate
from pat.state import PATMode, PATState

from simulator.ui.foundation.tokens import (
    COLOR_FIELD,
    COLOR_HAIRLINE_BORDER_HEX,
    COLOR_LOCK_CYAN,
    COLOR_LOST_RED,
    COLOR_TEXT_PRIMARY,
    COLOR_TEXT_SECONDARY,
    COLOR_VOID,
    FONT_BODY,
    FONT_TELEMETRY,
)
from simulator.ui.foundation.primitives import (
    StateIndicatorPill,
    StatePillState,
)

# UI Subcomponents
from simulator.ui.track.analytics_graphs import TimeSeriesAnalyticsWidget
from simulator.ui.track.covariance_panel import CovarianceDiagnosticPanel
from simulator.ui.track.geometry_view import TrackGeometryView
from simulator.ui.track.perception_breakdown import HybridPerceptionBreakdownPanel
from simulator.ui.track.radar_widget import CoarseToFineRadarWidget
from simulator.ui.track.state_estimate_panel import StateEstimatePanel


class ExecutiveKPICard(QWidget):
    """Single glassmorphic Executive KPI status card for high-level mission situational awareness."""

    def __init__(self, title: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setStyleSheet(
            f"background-color: {COLOR_FIELD}; "
            f"border: 1px solid {COLOR_HAIRLINE_BORDER_HEX}; "
            "border-radius: 6px;"
        )
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 7, 10, 7)
        layout.setSpacing(3)

        top_row = QHBoxLayout()
        top_row.setContentsMargins(0, 0, 0, 0)
        top_row.setSpacing(6)

        self.lbl_title = QLabel(title.upper(), self)
        self.lbl_title.setStyleSheet(
            f"color: {COLOR_TEXT_SECONDARY}; font-family: {FONT_BODY}; "
            "font-size: 10px; font-weight: 700; letter-spacing: 0.5px;"
        )
        top_row.addWidget(self.lbl_title)

        top_row.addStretch()

        self.pill = StateIndicatorPill(StatePillState.IDLE, label_text="STANDBY", parent=self)
        top_row.addWidget(self.pill)
        layout.addLayout(top_row)

        self.lbl_value = QLabel("--", self)
        self.lbl_value.setStyleSheet(
            f"color: {COLOR_TEXT_PRIMARY}; font-family: {FONT_TELEMETRY}; "
            "font-size: 14px; font-weight: 700;"
        )
        layout.addWidget(self.lbl_value)

        self.lbl_subtitle = QLabel("Awaiting telemetry stream", self)
        self.lbl_subtitle.setStyleSheet(
            f"color: {COLOR_TEXT_SECONDARY}; font-family: {FONT_BODY}; font-size: 10px;"
        )
        layout.addWidget(self.lbl_subtitle)

    def set_data(
        self,
        value_text: str,
        pill_text: str,
        pill_state: StatePillState,
        subtitle_text: str,
        value_color: str | None = None,
    ) -> None:
        self.lbl_value.setText(value_text)
        col = value_color or COLOR_TEXT_PRIMARY
        self.lbl_value.setStyleSheet(
            f"color: {col}; font-family: {FONT_TELEMETRY}; font-size: 14px; font-weight: 700;"
        )
        self.pill.set_state(pill_state, label_text=pill_text)
        self.lbl_subtitle.setText(subtitle_text)


class ExecutiveKPIStripWidget(QWidget):
    """Four-pillar Executive Mission KPI Header Strip for PAT Track Workstation."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        self.card_handoff = ExecutiveKPICard("🎯 Optical Handoff Gate", self)
        self.card_coupling = ExecutiveKPICard("⚡ Link Coupling η", self)
        self.card_nis = ExecutiveKPICard("🛡️ NIS Consistency (χ²)", self)
        self.card_integrity = ExecutiveKPICard("⏱️ Track Integrity & Age", self)

        layout.addWidget(self.card_handoff, stretch=1)
        layout.addWidget(self.card_coupling, stretch=1)
        layout.addWidget(self.card_nis, stretch=1)
        layout.addWidget(self.card_integrity, stretch=1)

        # Handoff Gate & Coupling Physics Tracking Buffers
        self._consecutive_lock_frames: int = 0
        self._recent_errors_px: List[float] = []
        self._max_recent_errors: int = 30

    def update_kpis(
        self,
        estimate: Optional[StateEstimate],
        pat_state: Optional[PATState],
        detection_res: Optional[DetectionResult],
    ) -> None:
        # 1. Optical Handoff Gate & Consecutive Lock Tracking
        if pat_state is not None:
            err_deg = math.hypot(pat_state.pan_error_deg, pat_state.tilt_error_deg)
            err_px = err_deg * 60.0
            err_urad = err_deg * 17453.3

            self._recent_errors_px.append(err_px)
            if len(self._recent_errors_px) > self._max_recent_errors:
                self._recent_errors_px.pop(0)

            # FSM capture basin threshold is <= 2.5 px (~50-60 urad)
            is_in_basin = (err_px <= 2.5) or (err_urad <= 60.0)
            if is_in_basin:
                self._consecutive_lock_frames += 1
            else:
                self._consecutive_lock_frames = 0

            if is_in_basin and self._consecutive_lock_frames >= 20:
                self.card_handoff.set_data(
                    value_text=f"±{err_urad:.1f} µrad ({err_px:.2f} px)",
                    pill_text="FSM LOCKED",
                    pill_state=StatePillState.CONFIRMED,
                    subtitle_text=f"Handoff Verified ({self._consecutive_lock_frames} frames) | Basin ≤ 2.5 px",
                    value_color="#38EF7D",
                )
            elif is_in_basin:
                self.card_handoff.set_data(
                    value_text=f"±{err_urad:.1f} µrad ({err_px:.2f} px)",
                    pill_text="LOCKED",
                    pill_state=StatePillState.CONFIRMED,
                    subtitle_text=f"Within Basin ({self._consecutive_lock_frames}/20 frames to FSM Handoff)",
                    value_color=COLOR_LOCK_CYAN,
                )
            elif err_px <= 6.0:
                self.card_handoff.set_data(
                    value_text=f"±{err_urad:.1f} µrad ({err_px:.2f} px)",
                    pill_text="ACQUIRING",
                    pill_state=StatePillState.ACTIVE,
                    subtitle_text=f"Coarse Gimbal Converging | Basin Δ: {err_px - 2.5:.1f} px",
                    value_color="#E8D47F",
                )
            else:
                self.card_handoff.set_data(
                    value_text=f"±{err_urad:.1f} µrad ({err_px:.2f} px)",
                    pill_text="SLEWING",
                    pill_state=StatePillState.LOST,
                    subtitle_text=f"Sensor FOV Slew Active | Basin Δ: {err_px - 2.5:.1f} px",
                    value_color=COLOR_LOST_RED,
                )
        else:
            self._consecutive_lock_frames = 0
            self.card_handoff.set_data(
                value_text="--",
                pill_text="STANDBY",
                pill_state=StatePillState.IDLE,
                subtitle_text="Awaiting coarse alignment",
            )

        # 2. Link Coupling η & Physical Optical Loss / Strehl / BER
        if pat_state is not None:
            total_urad = math.hypot(pat_state.pan_error_deg, pat_state.tilt_error_deg) * 17453.3
            spatial_coupling = math.exp(-2.0 * (min(total_urad, 600.0) / 140.0) ** 2)

            if len(self._recent_errors_px) >= 5:
                jitter_px = float(np.std(self._recent_errors_px))
            else:
                jitter_px = err_px * 0.1

            strehl = math.exp(-((jitter_px / 2.5) ** 2)) if jitter_px < 10.0 else 0.05
            eta = float(np.clip(spatial_coupling * pat_state.track_quality, 1e-4, 1.0))
            coupling_pct = eta * 100.0
            db_loss = 10.0 * math.log10(eta)
            margin_db = 18.0 + db_loss

            if coupling_pct >= 85.0:
                self.card_coupling.set_data(
                    value_text=f"{coupling_pct:.1f}% ({db_loss:+.2f} dB)",
                    pill_text="OPTIMAL",
                    pill_state=StatePillState.CONFIRMED,
                    subtitle_text=f"Margin: {margin_db:+.1f} dB | BER < 1e-9 | Strehl: {strehl:.2f}",
                    value_color="#6FE8A8",
                )
            elif coupling_pct >= 50.0:
                self.card_coupling.set_data(
                    value_text=f"{coupling_pct:.1f}% ({db_loss:+.2f} dB)",
                    pill_text="DEGRADED",
                    pill_state=StatePillState.DEGRADED,
                    subtitle_text=f"Margin: {margin_db:+.1f} dB | BER ~ 1e-6 (FEC Active)",
                    value_color="#E8D47F",
                )
            else:
                self.card_coupling.set_data(
                    value_text=f"{coupling_pct:.1f}% ({db_loss:+.2f} dB)",
                    pill_text="LOSS RISK",
                    pill_state=StatePillState.LOST,
                    subtitle_text=f"Margin: {margin_db:+.1f} dB | Decoupled (BER > 1e-2)",
                    value_color=COLOR_LOST_RED,
                )
        else:
            self.card_coupling.set_data(
                value_text="0.0% (-40.00 dB)",
                pill_text="STANDBY",
                pill_state=StatePillState.IDLE,
                subtitle_text="Zero optical flux coupled",
            )

        # 3. NIS Consistency (χ²)
        if estimate is not None and estimate.innovation is not None:
            innov = np.asarray(estimate.innovation).flatten()
            if estimate.covariance is not None and estimate.covariance.shape[0] >= 2:
                var_x = max(1e-4, float(estimate.covariance[0, 0]) + 0.25)
                var_y = max(1e-4, float(estimate.covariance[1, 1]) + 0.25)
                nis_val = float((innov[0] ** 2) / var_x + (innov[1] ** 2) / var_y)
            else:
                nis_val = float(np.sum(innov ** 2))

            if nis_val <= 5.99:
                self.card_nis.set_data(
                    value_text=f"χ² = {nis_val:.2f} (≤ 5.99)",
                    pill_text="CONSISTENT",
                    pill_state=StatePillState.CONFIRMED,
                    subtitle_text="Innovation inside 95% Confidence Ellipsoid",
                    value_color="#6FE8A8",
                )
            elif nis_val <= 9.21:
                self.card_nis.set_data(
                    value_text=f"χ² = {nis_val:.2f} (≤ 9.21)",
                    pill_text="MARGINAL",
                    pill_state=StatePillState.ACTIVE,
                    subtitle_text="Within 99% Bound | Filter Adapting",
                    value_color="#E8D47F",
                )
            else:
                self.card_nis.set_data(
                    value_text=f"χ² = {nis_val:.2f} (> 9.21)",
                    pill_text="MANEUVER",
                    pill_state=StatePillState.DEGRADED,
                    subtitle_text="Dynamic Acceleration / Process Covariance Adapted",
                    value_color="#E8D47F",
                )
        else:
            self.card_nis.set_data(
                value_text="χ² = 0.00",
                pill_text="IDLE",
                pill_state=StatePillState.IDLE,
                subtitle_text="Zero innovation residual",
            )

        # 4. Track Integrity & Age
        if estimate is not None:
            age = estimate.track_age
            misses = estimate.consecutive_misses
            conf = (detection_res.confidence * 100.0) if (detection_res and detection_res.detected) else 0.0
            if misses == 0 and age > 10:
                duty_text = "100% Lock" if self._consecutive_lock_frames >= 20 else "Continuous"
                self.card_integrity.set_data(
                    value_text=f"Age: {age} frames ({misses} drops)",
                    pill_text="CONTINUOUS",
                    pill_state=StatePillState.CONFIRMED,
                    subtitle_text=f"Conf: {conf:.1f}% | {duty_text} | Hybrid Lock",
                    value_color=COLOR_LOCK_CYAN,
                )
            elif misses > 0:
                self.card_integrity.set_data(
                    value_text=f"Age: {age} frames ({misses} misses)",
                    pill_text="COASTING",
                    pill_state=StatePillState.DEGRADED,
                    subtitle_text="Kalman Dead-Reckoning Extrapolation Active",
                    value_color="#E8D47F",
                )
            else:
                self.card_integrity.set_data(
                    value_text=f"Age: {age} frames",
                    pill_text="ACQUIRING",
                    pill_state=StatePillState.ACTIVE,
                    subtitle_text="Establishing temporal filter convergence",
                    value_color=COLOR_TEXT_PRIMARY,
                )
        else:
            self.card_integrity.set_data(
                value_text="--",
                pill_text="STANDBY",
                pill_state=StatePillState.IDLE,
                subtitle_text="Awaiting track initiation",
            )


class TrackScreenView(QWidget):
    """Phase 11.4 Track Diagnostics & Precision Analysis Workstation Screen.

    This screen is a passive consumer: it receives live simulation data pushed
    from LiveScreenView.track_data_ready signal and renders it. It does NOT
    run its own simulation engine.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        # Telemetry Time-Series Buffers (up to 200 data points)
        self._history_times: List[float] = []
        self._history_errors_px: List[float] = []
        self._history_qualities: List[float] = []
        self._history_innovations: List[float] = []
        self._history_pan_errors: List[float] = []
        self._history_tilt_errors: List[float] = []
        self._history_confidences: List[float] = []
        self._max_history = 200

        # Build Root Layout Architecture
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(12, 10, 12, 10)
        root_layout.setSpacing(10)

        # Top Bar: Executive Mission KPI Header Strip
        self.kpi_strip = ExecutiveKPIStripWidget(self)
        root_layout.addWidget(self.kpi_strip)

        # Main 2-Column Split (Left 62%, Right 38%)
        columns_layout = QHBoxLayout()
        columns_layout.setContentsMargins(0, 0, 0, 0)
        columns_layout.setSpacing(12)

        # LEFT / CENTER COLUMN (~62% width)
        left_column = QVBoxLayout()
        left_column.setSpacing(10)

        # Top Diagnostic Bank: Geometry View (Dual-Mode: Full FOV & 12x Microscope) + Polar Handoff Radar
        top_diag_row = QHBoxLayout()
        top_diag_row.setSpacing(10)

        self.geometry_view = TrackGeometryView(self)
        top_diag_row.addWidget(self.geometry_view, stretch=3)

        self.radar_widget = CoarseToFineRadarWidget(self)
        top_diag_row.addWidget(self.radar_widget, stretch=2)

        left_column.addLayout(top_diag_row, stretch=2)

        # Time-Series Analytics Panel (6-Channel Graphs & Lyapunov Phase Portrait)
        self.analytics_scroll = QScrollArea(self)
        self.analytics_scroll.setWidgetResizable(True)
        self.analytics_scroll.setStyleSheet(
            f"QScrollArea {{ background-color: transparent; border: none; }} "
            f"QScrollBar:vertical {{ background-color: {COLOR_VOID}; width: 8px; margin: 0px; border-radius: 4px; }} "
            f"QScrollBar::handle:vertical {{ background-color: #2D3342; min-height: 20px; border-radius: 4px; }} "
            f"QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0px; }}"
        )
        self.analytics_panel = TimeSeriesAnalyticsWidget(self.analytics_scroll)
        self.analytics_scroll.setWidget(self.analytics_panel)
        left_column.addWidget(self.analytics_scroll, stretch=3)

        columns_layout.addLayout(left_column, stretch=3)

        # RIGHT COLUMN (~38% width)
        right_column = QVBoxLayout()
        right_column.setSpacing(10)

        # 1. Covariance Diagnostic Panel (With Vector Compass & Dynamic Bounds)
        self.cov_panel = CovarianceDiagnosticPanel(self)
        self.cov_panel.sigma_changed.connect(self.geometry_view.set_sigma_level)
        right_column.addWidget(self.cov_panel)

        # 2. State Estimate Vector Panel
        self.estimate_panel = StateEstimatePanel(self)
        right_column.addWidget(self.estimate_panel)

        # 3. Hybrid Perception Breakdown Panel
        self.perception_panel = HybridPerceptionBreakdownPanel(self)
        right_column.addWidget(self.perception_panel)

        right_column.addStretch()
        columns_layout.addLayout(right_column, stretch=2)

        root_layout.addLayout(columns_layout, stretch=1)

        # Initial UI update in idle state
        self.update_track_displays()

    def update_track_displays(
        self,
        dist_frame: Optional[np.ndarray] = None,
        detection_res: Optional[DetectionResult] = None,
        estimate: Optional[StateEstimate] = None,
        pat_state: Optional[PATState] = None,
        ground_truth_pos: Optional[Tuple[float, float]] = None,
        sim_time: float = 0.0,
    ) -> None:
        """Update all Track screen components from real backend data pushed via signal."""

        # 0. Update Executive Mission KPI Header Strip
        try:
            self.kpi_strip.update_kpis(
                estimate=estimate,
                pat_state=pat_state,
                detection_res=detection_res,
            )
        except Exception:
            pass

        # 1. Update Geometry View
        try:
            if dist_frame is not None:
                self.geometry_view.render_geometry(
                    sensor_frame=dist_frame,
                    detection_res=detection_res,
                    estimate=estimate,
                    ground_truth_pos=ground_truth_pos,
                )
        except Exception:
            pass

        # 2. Update Covariance Panel
        try:
            self.cov_panel.update_covariance(estimate)
        except Exception:
            pass

        # 3. Update State Estimate Panel
        try:
            self.estimate_panel.update_estimate(estimate)
        except Exception:
            pass

        # 4. Update Hybrid Perception Breakdown Panel
        try:
            self.perception_panel.update_breakdown(detection_res)
        except Exception:
            pass

        # 5. Update Coarse-to-Fine Alignment Radar Widget
        try:
            if pat_state is not None:
                err_px = float(np.hypot(pat_state.pan_error_deg, pat_state.tilt_error_deg) * 60.0)
                self.radar_widget.update_alignment(
                    pan_error_deg=pat_state.pan_error_deg,
                    tilt_error_deg=pat_state.tilt_error_deg,
                    error_px=err_px,
                )
        except Exception:
            pass

        # 6. Append to Time-Series History Buffers & Update Analytics Graphs
        try:
            t_curr = float(sim_time)

            if pat_state is not None:
                err_px = float(np.hypot(pat_state.pan_error_deg, pat_state.tilt_error_deg) * 60.0)
                quality = float(pat_state.track_quality * 100.0)
                pan_err = float(pat_state.pan_error_deg)
                tilt_err = float(pat_state.tilt_error_deg)
            elif ground_truth_pos and detection_res and detection_res.detected and detection_res.centroid:
                err_px = float(np.hypot(detection_res.centroid[0] - ground_truth_pos[0], detection_res.centroid[1] - ground_truth_pos[1]))
                quality = float(detection_res.confidence * 100.0)
                pan_err = float(detection_res.centroid[0] - 320.0) / 60.0
                tilt_err = float(detection_res.centroid[1] - 240.0) / 60.0
            elif detection_res and detection_res.detected and detection_res.centroid:
                err_px = float(np.hypot(detection_res.centroid[0] - 320.0, detection_res.centroid[1] - 240.0))
                quality = float(detection_res.confidence * 100.0)
                pan_err = float(detection_res.centroid[0] - 320.0) / 60.0
                tilt_err = float(detection_res.centroid[1] - 240.0) / 60.0
            else:
                err_px = 0.0
                quality = 0.0
                pan_err = 0.0
                tilt_err = 0.0

            innov = float(np.linalg.norm(estimate.innovation)) if (estimate and estimate.innovation is not None) else 0.0
            conf = float(detection_res.confidence * 100.0) if (detection_res and detection_res.detected) else 0.0

            self._history_times.append(t_curr)
            self._history_errors_px.append(err_px)
            self._history_qualities.append(quality)
            self._history_innovations.append(innov)
            self._history_pan_errors.append(pan_err)
            self._history_tilt_errors.append(tilt_err)
            self._history_confidences.append(conf)

            if len(self._history_times) > self._max_history:
                self._history_times.pop(0)
                self._history_errors_px.pop(0)
                self._history_qualities.pop(0)
                self._history_innovations.pop(0)
                self._history_pan_errors.pop(0)
                self._history_tilt_errors.pop(0)
                self._history_confidences.pop(0)

            self.analytics_panel.update_analytics(
                times=self._history_times,
                errors_px=self._history_errors_px,
                qualities=self._history_qualities,
                innovations=self._history_innovations,
                pan_errors=self._history_pan_errors,
                tilt_errors=self._history_tilt_errors,
                confidences=self._history_confidences,
            )
        except Exception as ex:
            logger.debug("Analytics update error: %s", ex)
