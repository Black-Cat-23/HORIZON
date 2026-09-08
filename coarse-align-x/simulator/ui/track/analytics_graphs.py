"""HORIZON Phase 11.4 Time-Series Analytics Component
======================================================
Six real-time telemetry graphs plotting filter and control performance:
  1. Tracking Error vs Time (px)
  2. Track Quality vs Time (%)
  3. Innovation Residual vs Time (px)
  4. Pan Error vs Time (deg)
  5. Tilt Error vs Time (deg)
  6. Detector Confidence vs Time (%)

Each graph renders labeled axes, units, grid lines, and live telemetry lines using semantic color tokens sparingly.
"""

from __future__ import annotations
from typing import List, Tuple
import cv2
import numpy as np

from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import QGridLayout, QGroupBox, QLabel, QVBoxLayout, QWidget

from simulator.ui.foundation.tokens import (
    COLOR_CONFIRM_GREEN,
    COLOR_DISTURBANCE_AMBER,
    COLOR_FIELD,
    COLOR_HAIRLINE_BORDER_HEX,
    COLOR_LOCK_CYAN,
    COLOR_TEXT_PRIMARY,
    COLOR_TEXT_SECONDARY,
    COLOR_VOID,
    FONT_BODY,
    FONT_TELEMETRY,
    SPACING_8,
    SPACING_12,
    SPACING_16,
)
from simulator.ui.foundation.primitives import PanelSurface, PanelVariant, SectionHeaderLabel


class MiniTimeSeriesGraph(QLabel):
    """Clean 2D time-series plot canvas widget with axis labels and units."""

    def __init__(self, title: str, unit: str, color_bgr: Tuple[int, int, int], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.plot_title = title
        self.unit = unit
        self.line_color = color_bgr

        self.setMinimumSize(220, 100)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet(f"background-color: {COLOR_VOID}; border: 1px solid {COLOR_HAIRLINE_BORDER_HEX}; border-radius: 4px;")
        self._current_pixmap: Optional[QPixmap] = None

    def render_plot(self, time_data: List[float], val_data: List[float], y_min: float = 0.0, y_max: float = 100.0) -> None:
        canvas = np.zeros((100, 220, 3), dtype=np.uint8)

        # Draw grid lines
        cv2.line(canvas, (30, 20), (210, 20), (35, 35, 40), 1)
        cv2.line(canvas, (30, 50), (210, 50), (35, 35, 40), 1)
        cv2.line(canvas, (30, 80), (210, 80), (35, 35, 40), 1)

        # Axes
        cv2.line(canvas, (30, 10), (30, 85), (80, 80, 85), 1)
        cv2.line(canvas, (30, 85), (210, 85), (80, 80, 85), 1)

        # Title & Y-Max Label
        cv2.putText(canvas, f"{self.plot_title} ({self.unit})", (35, 16), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (220, 220, 220), 1, cv2.LINE_AA)

        if len(val_data) > 1 and len(time_data) == len(val_data):
            # Scale data to plot area [30..210] x [85..20]
            curr_max = max(y_max, max(val_data) * 1.1)
            curr_min = min(y_min, min(val_data))
            val_range = max(1e-5, curr_max - curr_min)

            pts: List[Tuple[int, int]] = []
            n_pts = len(val_data)
            for i in range(n_pts):
                px = int(round(30 + (i / max(1, n_pts - 1)) * 180))
                norm_val = (val_data[i] - curr_min) / val_range
                py = int(round(85 - norm_val * 65))
                py = max(12, min(85, py))
                pts.append((px, py))

            pts_arr = np.array(pts, dtype=np.int32).reshape((-1, 1, 2))
            cv2.polylines(canvas, [pts_arr], isClosed=False, color=self.line_color, thickness=1, lineType=cv2.LINE_AA)

            # Latest value readout
            latest_val = val_data[-1]
            cv2.putText(canvas, f"{latest_val:.1f}", (170, 16), cv2.FONT_HERSHEY_SIMPLEX, 0.35, self.line_color, 1, cv2.LINE_AA)
        else:
            cv2.putText(canvas, "N/A", (100, 52), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (120, 120, 120), 1, cv2.LINE_AA)

        qimg = QImage(canvas.data, 220, 100, 220 * 3, QImage.Format.Format_RGB888)
        self._current_pixmap = QPixmap.fromImage(qimg)
        self.setPixmap(self._current_pixmap)


class TimeSeriesAnalyticsWidget(PanelSurface):
    """Grid container for the 6 Time-Series Analytics Graphs."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(PanelVariant.FIELD, parent)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(SPACING_12, SPACING_12, SPACING_12, SPACING_12)
        main_layout.setSpacing(SPACING_8)

        # Title: "Time-series analytics" (sentence case)
        header = SectionHeaderLabel("Time-series analytics", self)
        header.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY}; font-family: {FONT_BODY}; font-size: 13px; font-weight: 600;")
        main_layout.addWidget(header)

        grid = QGridLayout()
        grid.setHorizontalSpacing(SPACING_8)
        grid.setVerticalSpacing(SPACING_8)

        # 6 Graphs (Cyan=(232,212,127), Green=(168,232,111), Amber=(92,161,232) in BGR)
        self.graph_error = MiniTimeSeriesGraph("Tracking error", "px", (232, 212, 127), self)
        self.graph_quality = MiniTimeSeriesGraph("Track quality", "%", (168, 232, 111), self)
        self.graph_innov = MiniTimeSeriesGraph("Innovation residual", "px", (92, 161, 232), self)
        self.graph_pan_err = MiniTimeSeriesGraph("Pan error", "°", (232, 212, 127), self)
        self.graph_tilt_err = MiniTimeSeriesGraph("Tilt error", "°", (92, 161, 232), self)
        self.graph_conf = MiniTimeSeriesGraph("Detector confidence", "%", (168, 232, 111), self)

        grid.addWidget(self.graph_error, 0, 0)
        grid.addWidget(self.graph_quality, 0, 1)
        grid.addWidget(self.graph_innov, 0, 2)
        grid.addWidget(self.graph_pan_err, 1, 0)
        grid.addWidget(self.graph_tilt_err, 1, 1)
        grid.addWidget(self.graph_conf, 1, 2)

        main_layout.addLayout(grid)

    def update_analytics(
        self,
        times: List[float],
        errors_px: List[float],
        qualities: List[float],
        innovations: List[float],
        pan_errors: List[float],
        tilt_errors: List[float],
        confidences: List[float],
    ) -> None:
        """Update all 6 time-series plots from real telemetry history."""
        self.graph_error.render_plot(times, errors_px, y_min=0.0, y_max=50.0)
        self.graph_quality.render_plot(times, qualities, y_min=0.0, y_max=100.0)
        self.graph_innov.render_plot(times, innovations, y_min=0.0, y_max=20.0)
        self.graph_pan_err.render_plot(times, pan_errors, y_min=-2.0, y_max=2.0)
        self.graph_tilt_err.render_plot(times, tilt_errors, y_min=-2.0, y_max=2.0)
        self.graph_conf.render_plot(times, confidences, y_min=0.0, y_max=100.0)
