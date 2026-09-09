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
        w = max(220, self.width()) if self.width() > 50 else 220
        h = max(100, self.height()) if self.height() > 30 else 100
        canvas = np.zeros((h, w, 3), dtype=np.uint8)

        margin_left = 32
        margin_right = 10
        margin_top = 22
        margin_bottom = 15
        plot_w = max(10, w - margin_left - margin_right)
        plot_h = max(10, h - margin_top - margin_bottom)

        # Draw grid lines
        y_grid1 = int(margin_top + plot_h * 0.25)
        y_grid2 = int(margin_top + plot_h * 0.50)
        y_grid3 = int(margin_top + plot_h * 0.75)
        cv2.line(canvas, (margin_left, y_grid1), (w - margin_right, y_grid1), (35, 35, 40), 1)
        cv2.line(canvas, (margin_left, y_grid2), (w - margin_right, y_grid2), (35, 35, 40), 1)
        cv2.line(canvas, (margin_left, y_grid3), (w - margin_right, y_grid3), (35, 35, 40), 1)

        # Axes
        cv2.line(canvas, (margin_left, 10), (margin_left, h - margin_bottom), (80, 80, 85), 1)
        cv2.line(canvas, (margin_left, h - margin_bottom), (w - margin_right, h - margin_bottom), (80, 80, 85), 1)

        # Title Label
        cv2.putText(canvas, f"{self.plot_title} ({self.unit})", (margin_left + 4, 16), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (220, 220, 220), 1, cv2.LINE_AA)

        if len(val_data) > 0 and len(time_data) == len(val_data):
            curr_max = max(y_max, max(val_data) * 1.1)
            curr_min = min(y_min, min(val_data))
            val_range = max(1e-5, curr_max - curr_min)

            n_pts = len(val_data)
            if n_pts == 1:
                px = margin_left + plot_w // 2
                norm_val = (val_data[0] - curr_min) / val_range
                py = int(round((h - margin_bottom) - norm_val * plot_h))
                cv2.circle(canvas, (px, py), 3, self.line_color, -1)
            else:
                pts: List[Tuple[int, int]] = []
                for i in range(n_pts):
                    px = int(round(margin_left + (i / (n_pts - 1)) * plot_w))
                    norm_val = (val_data[i] - curr_min) / val_range
                    py = int(round((h - margin_bottom) - norm_val * plot_h))
                    py = max(margin_top, min(h - margin_bottom, py))
                    pts.append((px, py))

                pts_arr = np.array(pts, dtype=np.int32).reshape((-1, 1, 2))
                cv2.polylines(canvas, [pts_arr], isClosed=False, color=self.line_color, thickness=1, lineType=cv2.LINE_AA)

            # Latest value readout
            latest_val = val_data[-1]
            readout_str = f"{latest_val:.1f}"
            cv2.putText(canvas, readout_str, (w - margin_right - 45, 16), cv2.FONT_HERSHEY_SIMPLEX, 0.35, self.line_color, 1, cv2.LINE_AA)
        else:
            cv2.putText(canvas, "N/A", (margin_left + plot_w // 2 - 10, margin_top + plot_h // 2), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (120, 120, 120), 1, cv2.LINE_AA)

        # Convert OpenCV BGR to RGB and create QImage with .copy() memory ownership
        canvas_rgb = cv2.cvtColor(canvas, cv2.COLOR_BGR2RGB)
        qimg = QImage(canvas_rgb.data, w, h, w * 3, QImage.Format.Format_RGB888).copy()
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
