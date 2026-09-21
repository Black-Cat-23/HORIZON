"""HORIZON Phase 11.4 Time-Series Analytics Component
======================================================
Six real-time telemetry graphs plotting filter and control performance:
  1. Tracking Error vs Time (px)
  2. Track Quality vs Time (%)
  3. Innovation Residual vs Time (px)
  4. Pan Error vs Time (deg)
  5. Tilt Error vs Time (deg)
  6. Detector Confidence vs Time (%)

Each graph renders labeled axes, units, grid lines, and live telemetry lines using PySide QPainter vector rendering.
"""

from __future__ import annotations
from typing import List, Tuple, Optional

from PySide6.QtCore import Qt, QPointF
from PySide6.QtGui import QBrush, QColor, QFont, QLinearGradient, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QGridLayout, QVBoxLayout, QWidget

from simulator.ui.foundation.tokens import (
    COLOR_HAIRLINE_BORDER_HEX,
    COLOR_TEXT_PRIMARY,
    COLOR_TEXT_SECONDARY,
    COLOR_VOID,
    FONT_BODY,
    FONT_TELEMETRY,
    SPACING_8,
    SPACING_12,
)
from simulator.ui.foundation.primitives import PanelSurface, PanelVariant, SectionHeaderLabel


class MiniTimeSeriesGraph(QWidget):
    """Clean 2D time-series plot widget using native PySide QPainter vector rendering."""

    def __init__(
        self,
        title: str,
        unit: str,
        color_rgb: Tuple[int, int, int],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.plot_title = title
        self.unit = unit
        self.line_color = QColor(*color_rgb)

        self.setMinimumSize(240, 155)

        self._time_data: List[float] = []
        self._val_data: List[float] = []
        self._y_min: float = 0.0
        self._y_max: float = 100.0

    def render_plot(
        self,
        time_data: List[float],
        val_data: List[float],
        y_min: float = 0.0,
        y_max: float = 100.0,
    ) -> None:
        """Update telemetry data and trigger QPainter repaint."""
        self._time_data = list(time_data)
        self._val_data = list(val_data)
        self._y_min = y_min
        self._y_max = y_max
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        w = self.width()
        h = self.height()

        # 1. Background Surface Card
        bg_color = QColor(13, 17, 23)
        border_color = QColor(40, 45, 55)
        painter.setBrush(QBrush(bg_color))
        painter.setPen(QPen(border_color, 1))
        painter.drawRoundedRect(0, 0, w - 1, h - 1, 4, 4)

        margin_left = 38
        margin_right = 14
        margin_top = 26
        margin_bottom = 20

        plot_w = max(10, w - margin_left - margin_right)
        plot_h = max(10, h - margin_top - margin_bottom)

        # 2. Grid lines
        grid_pen = QPen(QColor(32, 38, 48), 1, Qt.PenStyle.DashLine)
        painter.setPen(grid_pen)
        for ratio in (0.25, 0.50, 0.75):
            gy = margin_top + plot_h * ratio
            painter.drawLine(QPointF(margin_left, gy), QPointF(w - margin_right, gy))

        # 3. Axes
        axis_pen = QPen(QColor(65, 72, 85), 1)
        painter.setPen(axis_pen)
        painter.drawLine(QPointF(margin_left, margin_top - 4), QPointF(margin_left, h - margin_bottom))
        painter.drawLine(QPointF(margin_left, h - margin_bottom), QPointF(w - margin_right, h - margin_bottom))

        # 4. Title Header Label
        painter.setFont(QFont("Inter", 8, QFont.Weight.Bold))
        painter.setPen(QPen(QColor(210, 215, 225)))
        title_str = f"{self.plot_title} ({self.unit})"
        painter.drawText(margin_left, margin_top - 8, title_str)

        # 5. Data Plotting & Dynamic Y-Scale Ticks
        if len(self._val_data) > 0 and len(self._time_data) == len(self._val_data):
            curr_max = max(self._y_max, max(self._val_data) * 1.05)
            curr_min = min(self._y_min, min(self._val_data))
            val_range = max(1e-5, curr_max - curr_min)

            # Draw Y-Scale Tick Readouts on Left Margin
            painter.setFont(QFont("Consolas", 7))
            painter.setPen(QPen(QColor(110, 115, 125)))
            painter.drawText(2, int(margin_top + 4), f"{curr_max:.0f}")
            painter.drawText(2, int(margin_top + plot_h * 0.5 + 3), f"{(curr_max + curr_min) * 0.5:.0f}")
            painter.drawText(2, int(h - margin_bottom), f"{curr_min:.0f}")

            n_pts = len(self._val_data)
            if n_pts == 1:
                px = margin_left + plot_w / 2.0
                norm_val = (self._val_data[0] - curr_min) / val_range
                py = (h - margin_bottom) - norm_val * plot_h
                painter.setBrush(QBrush(self.line_color))
                painter.setPen(Qt.PenStyle.NoPen)
                painter.drawEllipse(QPointF(px, py), 3.5, 3.5)
            else:
                path = QPainterPath()
                pts_list = []
                for i in range(n_pts):
                    px = margin_left + (i / (n_pts - 1)) * plot_w
                    norm_val = (self._val_data[i] - curr_min) / val_range
                    py = (h - margin_bottom) - norm_val * plot_h
                    py = max(float(margin_top), min(float(h - margin_bottom), py))
                    pts_list.append((px, py))

                    if i == 0:
                        path.moveTo(px, py)
                    else:
                        path.lineTo(px, py)

                # Gradient Fill Area Under Curve
                fill_path = QPainterPath(path)
                fill_path.lineTo(pts_list[-1][0], h - margin_bottom)
                fill_path.lineTo(pts_list[0][0], h - margin_bottom)
                fill_path.closeSubpath()

                grad = QLinearGradient(0, margin_top, 0, h - margin_bottom)
                grad.setColorAt(0.0, QColor(self.line_color.red(), self.line_color.green(), self.line_color.blue(), 45))
                grad.setColorAt(1.0, QColor(self.line_color.red(), self.line_color.green(), self.line_color.blue(), 5))
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(QBrush(grad))
                painter.drawPath(fill_path)

                # Solid Curve Line
                line_pen = QPen(self.line_color, 1.6)
                painter.setPen(line_pen)
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawPath(path)

            # Latest Value Readout in top right
            latest_val = self._val_data[-1]
            readout_str = f"{latest_val:.1f}"
            painter.setFont(QFont("Consolas", 10, QFont.Weight.Bold))
            painter.setPen(QPen(self.line_color))
            painter.drawText(int(w - margin_right - 50), int(margin_top - 8), readout_str)
        else:
            # Y-Scale Empty Ticks
            painter.setFont(QFont("Consolas", 7))
            painter.setPen(QPen(QColor(110, 115, 125)))
            painter.drawText(2, int(margin_top + 4), f"{self._y_max:.0f}")
            painter.drawText(2, int(h - margin_bottom), f"{self._y_min:.0f}")

            painter.setFont(QFont("Inter", 8))
            painter.setPen(QPen(QColor(110, 115, 125)))
            painter.drawText(int(margin_left + plot_w / 2.0 - 10), int(margin_top + plot_h / 2.0 + 4), "N/A")


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

        # 6 Graphs (RGB tuples: Cyan=(127,212,232), Green=(111,232,168), Amber=(232,161,92))
        self.graph_error = MiniTimeSeriesGraph("Tracking error", "px", (127, 212, 232), self)
        self.graph_quality = MiniTimeSeriesGraph("Track quality", "%", (111, 232, 168), self)
        self.graph_innov = MiniTimeSeriesGraph("Innovation residual", "px", (232, 161, 92), self)
        self.graph_pan_err = MiniTimeSeriesGraph("Pan error", "°", (127, 212, 232), self)
        self.graph_tilt_err = MiniTimeSeriesGraph("Tilt error", "°", (232, 161, 92), self)
        self.graph_conf = MiniTimeSeriesGraph("Detector confidence", "%", (111, 232, 168), self)

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
