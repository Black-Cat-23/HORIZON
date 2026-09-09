"""HORIZON Phase 11.4 Track Screen View Component
=================================================
Composite main view for Mode 2 ("Track Diagnostics").
Integrates:
  - LEFT/CENTER TOP: Track Geometry View (640x480 crop feed, measured/estimated/predicted centroids, covariance ellipse, GT when eval mode ON)
  - LEFT/CENTER BOTTOM: Time-Series Analytics Panel (6 domain telemetry graphs vs time)
  - RIGHT TOP: Covariance Diagnostic Panel (Selectable 1-sigma / 2-sigma / 3-sigma controls)
  - RIGHT MIDDLE: State Estimate Vector Panel (X, Y, VX, VY, Innovation, Uncertainty with single-line context)
  - RIGHT BOTTOM: Hybrid Perception Breakdown Panel (Classical, Neural, Agreement, Final confidence readouts)

Strict Ground-Truth Firewall: Ground-truth marker appears ONLY in Evaluation Mode (OFF by default) and NEVER influences any backend algorithm.
"""

from __future__ import annotations
import math
import time
from typing import List, Optional, Tuple
import cv2
import numpy as np

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QHBoxLayout,
    QVBoxLayout,
    QWidget,
)

from simulator.perception.detector import DetectionResult
from tracking.estimation.state import StateEstimate
from pat.state import PATMode, PATState

# UI Subcomponents
from simulator.ui.track.analytics_graphs import TimeSeriesAnalyticsWidget
from simulator.ui.track.covariance_panel import CovarianceDiagnosticPanel
from simulator.ui.track.geometry_view import TrackGeometryView
from simulator.ui.track.perception_breakdown import HybridPerceptionBreakdownPanel
from simulator.ui.track.state_estimate_panel import StateEstimatePanel


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

        # Build Layout Architecture
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(12)

        # LEFT / CENTER COLUMN (~60% width)
        left_column = QVBoxLayout()
        left_column.setSpacing(12)

        # Primary Geometry View
        self.geometry_view = TrackGeometryView(self)
        left_column.addWidget(self.geometry_view, stretch=3)

        # Time-Series Analytics Panel (6 graphs)
        self.analytics_panel = TimeSeriesAnalyticsWidget(self)
        left_column.addWidget(self.analytics_panel, stretch=2)

        main_layout.addLayout(left_column, stretch=3)

        # RIGHT COLUMN (~40% width)
        right_column = QVBoxLayout()
        right_column.setSpacing(12)

        # 1. Covariance Diagnostic Panel
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
        main_layout.addLayout(right_column, stretch=2)

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

        # 1. Update Geometry View
        if dist_frame is not None:
            self.geometry_view.render_geometry(
                sensor_frame=dist_frame,
                detection_res=detection_res,
                estimate=estimate,
                ground_truth_pos=ground_truth_pos,
            )

        # 2. Update Covariance Panel
        self.cov_panel.update_covariance(estimate)

        # 3. Update State Estimate Panel
        self.estimate_panel.update_estimate(estimate)

        # 4. Update Hybrid Perception Breakdown Panel
        self.perception_panel.update_breakdown(detection_res)

        # 5. Append to Time-Series History Buffers & Update Analytics Graphs
        if pat_state is not None and estimate is not None:
            err_px = float(np.hypot(pat_state.pan_error_deg, pat_state.tilt_error_deg) * 60.0)
            quality = float(pat_state.track_quality * 100.0)
            innov = float(np.hypot(estimate.innovation_x, estimate.innovation_y))
            conf = float(detection_res.confidence * 100.0) if (detection_res and detection_res.detected) else 0.0

            self._history_times.append(sim_time)
            self._history_errors_px.append(err_px)
            self._history_qualities.append(quality)
            self._history_innovations.append(innov)
            self._history_pan_errors.append(pat_state.pan_error_deg)
            self._history_tilt_errors.append(pat_state.tilt_error_deg)
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
