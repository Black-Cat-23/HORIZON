"""HORIZON Phase 11.4 Time-Series Analytics & Phase-Plane Stability Component
=============================================================================
Six real-time telemetry graphs plotting filter and control performance:
  1. Tracking Error vs Time (px) [FPS Gate 2.5px threshold]
  2. Coupling Efficiency / Quality vs Time (%) [95% optical handoff threshold]
  3. Innovation Residual / NIS consistency vs Time (χ²) [Chi-square bound 7.38]
  4. Pan Error vs Time (°) [Boresight zero line]
  5. Tilt Error vs Time (°) [Boresight zero line]
  6. Detector Confidence vs Time (%) [80% high-confidence line]

Plus Dual-View Mode:
  - 📈 6-Channel Telemetry (detailed individual time-series charts with pill readouts and elided titles)
  - 🎯 State Phase-Plane Portrait (e vs ė) proving Lyapunov asymptotic stability to origin limit cycle
"""

from __future__ import annotations
import math
from typing import List, Tuple, Optional

from PySide6.QtCore import Qt, QPointF, QRectF
from PySide6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QFontMetrics,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
)
from PySide6.QtWidgets import (
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from simulator.ui.foundation.tokens import (
    COLOR_HAIRLINE_BORDER_HEX,
    COLOR_LOCK_CYAN,
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
    """Clean 2D time-series plot widget with aerospace threshold annotations and non-overlapping pill readouts."""

    def __init__(
        self,
        title: str,
        unit: str,
        color_rgb: Tuple[int, int, int],
        parent: QWidget | None = None,
        threshold_val: Optional[float] = None,
        threshold_label: str = "",
        threshold_color: Optional[Tuple[int, int, int]] = None,
    ) -> None:
        super().__init__(parent)
        self.plot_title = title
        self.unit = unit
        self.line_color = QColor(*color_rgb)
        self.threshold_val = threshold_val
        self.threshold_label = threshold_label
        self.threshold_color = QColor(*(threshold_color or (111, 232, 168)))

        self.setMinimumSize(220, 145)

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

        margin_left = 34
        margin_right = 10
        margin_top = 28
        margin_bottom = 18

        plot_w = max(10, w - margin_left - margin_right)
        plot_h = max(10, h - margin_top - margin_bottom)

        # 2. Latest Value Readout Pill Badge (Top-Right)
        pill_w = 46
        pill_h = 16
        pill_x = w - margin_right - pill_w
        pill_y = 6

        if len(self._val_data) > 0:
            latest_val = self._val_data[-1]
            readout_str = f"{latest_val:.1f}"
        else:
            readout_str = "--"

        painter.setBrush(QBrush(QColor(18, 24, 34)))
        pill_border = QColor(self.line_color.red(), self.line_color.green(), self.line_color.blue(), 140)
        painter.setPen(QPen(pill_border, 1))
        painter.drawRoundedRect(QRectF(pill_x, pill_y, pill_w, pill_h), 3, 3)

        painter.setFont(QFont("Consolas", 8, QFont.Weight.Bold))
        painter.setPen(QPen(self.line_color))
        painter.drawText(QRectF(pill_x, pill_y, pill_w, pill_h), Qt.AlignmentFlag.AlignCenter, readout_str)

        # 3. Title Header Label (Elided cleanly to prevent any overlap with pill)
        avail_title_w = max(20, pill_x - margin_left - 6)
        title_str = f"{self.plot_title} ({self.unit})"
        painter.setFont(QFont("Inter", 8, QFont.Weight.Bold))
        painter.setPen(QPen(QColor(215, 220, 230)))
        fm = QFontMetrics(painter.font())
        elided_title = fm.elidedText(title_str, Qt.TextElideMode.ElideRight, int(avail_title_w))
        painter.drawText(QRectF(margin_left, pill_y, avail_title_w, pill_h), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, elided_title)

        # 4. Grid lines
        grid_pen = QPen(QColor(32, 38, 48), 1, Qt.PenStyle.DashLine)
        painter.setPen(grid_pen)
        for ratio in (0.25, 0.50, 0.75):
            gy = margin_top + plot_h * ratio
            painter.drawLine(QPointF(margin_left, gy), QPointF(w - margin_right, gy))

        # 5. Axes
        axis_pen = QPen(QColor(60, 68, 80), 1)
        painter.setPen(axis_pen)
        painter.drawLine(QPointF(margin_left, margin_top - 4), QPointF(margin_left, h - margin_bottom))
        painter.drawLine(QPointF(margin_left, h - margin_bottom), QPointF(w - margin_right, h - margin_bottom))

        # 6. Data Plotting & Dynamic Y-Scale Ticks
        if len(self._val_data) > 0 and len(self._time_data) == len(self._val_data):
            curr_max = max(self._y_max, max(self._val_data) * 1.05)
            curr_min = min(self._y_min, min(self._val_data))
            val_range = max(1e-5, curr_max - curr_min)

            # Draw Threshold Reference Line (e.g. FPS Gate 2.5px or Chi-square bound)
            if self.threshold_val is not None:
                norm_th = (self.threshold_val - curr_min) / val_range
                thy = (h - margin_bottom) - norm_th * plot_h
                if margin_top <= thy <= (h - margin_bottom):
                    th_pen = QPen(self.threshold_color, 1.2, Qt.PenStyle.DashLine)
                    painter.setPen(th_pen)
                    painter.drawLine(QPointF(margin_left, thy), QPointF(w - margin_right, thy))
                    if self.threshold_label:
                        painter.setFont(QFont("Inter", 6, QFont.Weight.Bold))
                        painter.setPen(QPen(self.threshold_color))
                        th_x = max(margin_left + 10, w - margin_right - 95)
                        painter.drawText(int(th_x), int(thy - 2), self.threshold_label)

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
        else:
            # Y-Scale Empty Ticks
            painter.setFont(QFont("Consolas", 7))
            painter.setPen(QPen(QColor(110, 115, 125)))
            painter.drawText(2, int(margin_top + 4), f"{self._y_max:.0f}")
            painter.drawText(2, int(h - margin_bottom), f"{self._y_min:.0f}")

            painter.setFont(QFont("Inter", 8))
            painter.setPen(QPen(QColor(110, 115, 125)))
            painter.drawText(int(margin_left + plot_w / 2.0 - 10), int(margin_top + plot_h / 2.0 + 4), "N/A")


class PhasePortraitWidget(QWidget):
    """Aerospace PAT Phase Portrait Widget (Error e vs Error Velocity ė).
    Demonstrates Lyapunov asymptotic stability and limit-cycle convergence.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumSize(320, 240)
        self._error_history: List[float] = []
        self._edot_history: List[float] = []
        self._fps_locked: bool = False

    def update_phase_data(self, errors_px: List[float], times: List[float]) -> None:
        """Calculate phase velocities e_dot and update portrait trajectory."""
        if not errors_px or len(errors_px) < 2:
            self._error_history = list(errors_px)
            self._edot_history = [0.0] * len(errors_px)
            self.update()
            return

        self._error_history = list(errors_px)
        edots = [0.0]
        for i in range(1, len(errors_px)):
            dt = max(1e-3, times[i] - times[i - 1]) if i < len(times) else 0.05
            de = errors_px[i] - errors_px[i - 1]
            edots.append(de / dt)
        self._edot_history = edots
        self._fps_locked = (len(errors_px) > 0 and errors_px[-1] <= 2.5)
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        w = self.width()
        h = self.height()

        # 1. Background Card
        painter.setBrush(QBrush(QColor(13, 17, 23)))
        painter.setPen(QPen(QColor(40, 45, 55), 1))
        painter.drawRoundedRect(0, 0, w - 1, h - 1, 4, 4)

        margin = 32
        plot_w = w - 2 * margin
        plot_h = h - 2 * margin - 20
        cx = margin + plot_w / 2.0
        cy = margin + 15 + plot_h / 2.0

        # Dynamic Adaptive Scaling based on recent trajectory history (last 60 frames)
        if len(self._error_history) > 0:
            hist_subset_e = self._error_history[-60:]
            hist_subset_edot = self._edot_history[-60:] if len(self._edot_history) >= len(hist_subset_e) else [0.0]
            max_seen_e = max(abs(e) for e in hist_subset_e)
            max_seen_edot = max(abs(ed) for ed in hist_subset_edot)
        else:
            max_seen_e = 2.5
            max_seen_edot = 6.0

        # Enforce minimum viewing box (+/-5 px, +/-12 px/s) so FPS gate is always clearly visible
        max_e = max(5.0, max_seen_e * 1.25)
        max_edot = max(12.0, max_seen_edot * 1.25)

        scale_x = (plot_w / 2.0) / max_e
        scale_y = (plot_h / 2.0) / max_edot

        # 2. Grid & Boresight Crosshairs (e=0, edot=0)
        painter.setPen(QPen(QColor(30, 36, 46), 1, Qt.PenStyle.DashLine))
        for r_step in (0.25, 0.5, 0.75):
            painter.drawLine(QPointF(cx - plot_w / 2.0 * r_step, cy - plot_h / 2.0), QPointF(cx - plot_w / 2.0 * r_step, cy + plot_h / 2.0))
            painter.drawLine(QPointF(cx + plot_w / 2.0 * r_step, cy - plot_h / 2.0), QPointF(cx + plot_w / 2.0 * r_step, cy + plot_h / 2.0))
            painter.drawLine(QPointF(cx - plot_w / 2.0, cy - plot_h / 2.0 * r_step), QPointF(cx + plot_w / 2.0, cy - plot_h / 2.0 * r_step))
            painter.drawLine(QPointF(cx - plot_w / 2.0, cy + plot_h / 2.0 * r_step), QPointF(cx + plot_w / 2.0, cy + plot_h / 2.0 * r_step))

        # Main Axes
        painter.setPen(QPen(QColor(70, 80, 95), 1.2))
        painter.drawLine(QPointF(cx - plot_w / 2.0, cy), QPointF(cx + plot_w / 2.0, cy))
        painter.drawLine(QPointF(cx, cy - plot_h / 2.0), QPointF(cx, cy + plot_h / 2.0))

        # 3. Stability Basin Ellipses (Lyapunov Capture Gate)
        # Inner FPS Capture Basin: e <= 2.5 px, edot <= 6 px/s
        rx_fps = 2.5 * scale_x
        ry_fps = 6.0 * scale_y
        painter.setPen(QPen(QColor(111, 232, 168, 160), 1.2, Qt.PenStyle.DashLine))
        painter.setBrush(QBrush(QColor(111, 232, 168, 15)))
        painter.drawEllipse(QPointF(cx, cy), rx_fps, ry_fps)

        # Outer Coarse Convergence Basin: e <= 10.0 px, edot <= 18 px/s
        rx_coarse = 10.0 * scale_x
        ry_coarse = 18.0 * scale_y
        painter.setPen(QPen(QColor(127, 212, 232, 80), 1, Qt.PenStyle.DotLine))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(QPointF(cx, cy), rx_coarse, ry_coarse)

        # 4. Trajectory Plotting with Temporal Alpha Gradient
        n_pts = min(len(self._error_history), len(self._edot_history))
        if n_pts > 1:
            for i in range(1, n_pts):
                alpha = int(40 + 215 * (i / float(n_pts)))
                e0, ed0 = self._error_history[i - 1], self._edot_history[i - 1]
                e1, ed1 = self._error_history[i], self._edot_history[i]

                x0 = cx + max(-plot_w / 2.0, min(plot_w / 2.0, e0 * scale_x))
                y0 = cy - max(-plot_h / 2.0, min(plot_h / 2.0, ed0 * scale_y))
                x1 = cx + max(-plot_w / 2.0, min(plot_w / 2.0, e1 * scale_x))
                y1 = cy - max(-plot_h / 2.0, min(plot_h / 2.0, ed1 * scale_y))

                traj_pen = QPen(QColor(127, 212, 232, alpha), 1.8)
                painter.setPen(traj_pen)
                painter.drawLine(QPointF(x0, y0), QPointF(x1, y1))

            # Current Operating Point
            cur_x = cx + max(-plot_w / 2.0, min(plot_w / 2.0, self._error_history[-1] * scale_x))
            cur_y = cy - max(-plot_h / 2.0, min(plot_h / 2.0, self._edot_history[-1] * scale_y))

            # Glowing Halo
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(QColor(255, 230, 80, 80)))
            painter.drawEllipse(QPointF(cur_x, cur_y), 8, 8)
            painter.setBrush(QBrush(QColor(255, 230, 80)))
            painter.drawEllipse(QPointF(cur_x, cur_y), 3.5, 3.5)

            # Callout Text for Current Point
            painter.setFont(QFont("Consolas", 7, QFont.Weight.Bold))
            painter.setPen(QPen(QColor(255, 230, 80)))
            painter.drawText(int(cur_x + 8), int(cur_y - 4), f"e={self._error_history[-1]:.2f} px")

        # 5. Header Bar & Status Pill
        painter.setFont(QFont("Inter", 8, QFont.Weight.Bold))
        painter.setPen(QPen(QColor(215, 220, 230)))
        painter.drawText(margin, margin, "Phase-Plane Stability Portrait [e vs ė] — Lyapunov Basin")

        latest_e = self._error_history[-1] if len(self._error_history) > 0 else 0.0
        if self._fps_locked:
            status_str = f"LIMIT CYCLE LOCKED (|e| ≤ 2.5 px)"
            status_col = QColor(111, 232, 168)
        elif latest_e <= 10.0:
            status_str = f"COARSE PULL-IN (e={latest_e:.1f} px)"
            status_col = QColor(232, 212, 127)
        else:
            status_str = f"SLEW CONVERGING (e={latest_e:.1f} px)"
            status_col = QColor(127, 212, 232)

        painter.setBrush(QBrush(QColor(18, 24, 34)))
        painter.setPen(QPen(status_col, 1))
        pill_rect = QRectF(w - margin - 185, margin - 12, 185, 18)
        painter.drawRoundedRect(pill_rect, 3, 3)
        painter.setFont(QFont("Consolas", 7, QFont.Weight.Bold))
        painter.setPen(QPen(status_col))
        painter.drawText(pill_rect, Qt.AlignmentFlag.AlignCenter, status_str)

        # 6. Axis Labels & Dynamic Scale Readouts
        painter.setFont(QFont("Consolas", 7))
        painter.setPen(QPen(QColor(120, 130, 145)))
        painter.drawText(int(cx + plot_w / 2.0 - 75), int(cy - 4), f"+e (±{max_e:.0f}px) →")
        painter.drawText(int(cx + 6), int(cy - plot_h / 2.0 + 10), f"+ė (±{max_edot:.0f}px/s)")
        painter.drawText(margin, h - 8, f"INNER BASIN: FPS Gate (|e| ≤ 2.5px)  |  ORIGIN: Optical Boresight (0, 0)  |  ZOOM: ±{max_e:.0f} px")


class TimeSeriesAnalyticsWidget(PanelSurface):
    """Container for the 6 Aerospace Time-Series Analytics Graphs and Phase-Plane Stability Portrait."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(PanelVariant.FIELD, parent)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(SPACING_12, SPACING_12, SPACING_12, SPACING_12)
        main_layout.setSpacing(SPACING_8)

        # Header Bar: Title + View Mode Switcher [📈 6-Channel Telemetry] vs [🎯 Phase-Plane (e vs ė)]
        header_row = QHBoxLayout()
        header_row.setContentsMargins(0, 0, 0, 0)
        header_row.setSpacing(8)

        lbl_header = SectionHeaderLabel("Aerospace tracking & control diagnostics", self)
        lbl_header.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY}; font-family: {FONT_BODY}; font-size: 13px; font-weight: 600;")
        header_row.addWidget(lbl_header)

        header_row.addStretch()

        self.btn_view_timeseries = QPushButton("📈 Telemetry (6ch)", self)
        self.btn_view_phase = QPushButton("🎯 Phase-Plane (e vs ė)", self)
        self.btn_view_timeseries.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_view_phase.setCursor(Qt.CursorShape.PointingHandCursor)

        self.btn_view_timeseries.clicked.connect(lambda: self.set_view_mode(0))
        self.btn_view_phase.clicked.connect(lambda: self.set_view_mode(1))

        mode_row = QHBoxLayout()
        mode_row.setSpacing(4)
        mode_row.addWidget(self.btn_view_timeseries)
        mode_row.addWidget(self.btn_view_phase)
        header_row.addLayout(mode_row)

        main_layout.addLayout(header_row)

        # 1. 6-Graph Grid Container
        self.grid_container = QWidget(self)
        grid = QGridLayout(self.grid_container)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(SPACING_8)
        grid.setVerticalSpacing(SPACING_8)

        # 6 Domain Graphs with official aerospace threshold references:
        # 1. Tracking error with FPS capture gate line at 2.5 px
        self.graph_error = MiniTimeSeriesGraph("Tracking Error", "px", (127, 212, 232), self.grid_container, threshold_val=2.5, threshold_label="FPS GATE (2.5px)", threshold_color=(111, 232, 168))
        # 2. Optical coupling efficiency & track quality with 95% target threshold
        self.graph_quality = MiniTimeSeriesGraph("Coupling Efficiency η", "%", (111, 232, 168), self.grid_container, threshold_val=95.0, threshold_label="TARGET (95%)", threshold_color=(111, 232, 168))
        # 3. Innovation residual with chi-square consistency boundary (score / px)
        self.graph_innov = MiniTimeSeriesGraph("NIS Consistency", "χ²", (232, 161, 92), self.grid_container, threshold_val=7.38, threshold_label="χ² BOUND (7.38)", threshold_color=(232, 111, 127))
        # 4. Pan angular tracking error with boresight zero reference
        self.graph_pan_err = MiniTimeSeriesGraph("Pan Error", "°", (127, 212, 232), self.grid_container, threshold_val=0.0, threshold_label="BORESIGHT", threshold_color=(75, 85, 100))
        # 5. Tilt angular tracking error with boresight zero reference
        self.graph_tilt_err = MiniTimeSeriesGraph("Tilt Error", "°", (232, 161, 92), self.grid_container, threshold_val=0.0, threshold_label="BORESIGHT", threshold_color=(75, 85, 100))
        # 6. Detector confidence with high-confidence reference line at 80%
        self.graph_conf = MiniTimeSeriesGraph("Detector Confidence", "%", (111, 232, 168), self.grid_container, threshold_val=80.0, threshold_label="HIGH CONF (80%)", threshold_color=(111, 232, 168))

        grid.addWidget(self.graph_error, 0, 0)
        grid.addWidget(self.graph_quality, 0, 1)
        grid.addWidget(self.graph_innov, 0, 2)
        grid.addWidget(self.graph_pan_err, 1, 0)
        grid.addWidget(self.graph_tilt_err, 1, 1)
        grid.addWidget(self.graph_conf, 1, 2)

        main_layout.addWidget(self.grid_container)

        # 2. Phase Portrait Widget
        self.phase_portrait = PhasePortraitWidget(self)
        self.phase_portrait.setVisible(False)
        main_layout.addWidget(self.phase_portrait)

        self._view_mode = 0
        self._update_button_styles()

    def set_view_mode(self, mode: int) -> None:
        """Toggle between 6-Channel Telemetry (0) and Phase-Plane Portrait (1)."""
        self._view_mode = mode
        if mode == 0:
            self.grid_container.setVisible(True)
            self.phase_portrait.setVisible(False)
        else:
            self.grid_container.setVisible(False)
            self.phase_portrait.setVisible(True)
        self._update_button_styles()

    def _update_button_styles(self) -> None:
        active_style = (
            "QPushButton {"
            f"  background-color: #162B38; color: {COLOR_LOCK_CYAN}; "
            f"  border: 1px solid {COLOR_LOCK_CYAN}; border-radius: 4px; "
            "  font-weight: 700; font-size: 11px; padding: 3px 8px;"
            "}"
        )
        inactive_style = (
            "QPushButton {"
            f"  background-color: {COLOR_VOID}; color: {COLOR_TEXT_SECONDARY}; "
            "  border: 1px solid #30363D; border-radius: 4px; "
            "  font-weight: 500; font-size: 11px; padding: 3px 8px;"
            "}"
            "QPushButton:hover { background-color: #21262D; color: #C9D1D9; border-color: #58A6FF; }"
        )
        if self._view_mode == 0:
            self.btn_view_timeseries.setStyleSheet(active_style)
            self.btn_view_phase.setStyleSheet(inactive_style)
        else:
            self.btn_view_timeseries.setStyleSheet(inactive_style)
            self.btn_view_phase.setStyleSheet(active_style)

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
        """Update all 6 time-series plots and phase-portrait trajectory from real telemetry history."""

        def _range(data: List[float], y_min_floor: float, y_max_ceil: float, min_span: float) -> tuple:
            """Dynamic axis range: data-driven with a minimum visible span and sensible clamps."""
            if not data:
                return y_min_floor, y_max_ceil
            lo = min(data)
            hi = max(data)
            span = hi - lo
            pad = max(span * 0.12, min_span * 0.05)
            lo_out = max(y_min_floor, lo - pad)
            hi_out = min(y_max_ceil, hi + pad)
            # Guarantee minimum visible span so a flat line still shows a graph region
            if hi_out - lo_out < min_span:
                mid = (lo_out + hi_out) / 2.0
                lo_out = max(y_min_floor, mid - min_span / 2.0)
                hi_out = min(y_max_ceil, mid + min_span / 2.0)
            return lo_out, hi_out

        err_lo, err_hi   = _range(errors_px,   0.0,   200.0, 5.0)
        qual_lo, qual_hi = _range(qualities,    0.0,   100.0, 10.0)
        inn_lo,  inn_hi  = _range(innovations,  0.0,   50.0,  2.0)
        pan_lo,  pan_hi  = _range(pan_errors,  -10.0,  10.0,  0.5)
        tilt_lo, tilt_hi = _range(tilt_errors, -10.0,  10.0,  0.5)
        conf_lo, conf_hi = _range(confidences,  0.0,   100.0, 10.0)

        self.graph_error.render_plot(times, errors_px,   y_min=err_lo,  y_max=err_hi)
        self.graph_quality.render_plot(times, qualities, y_min=qual_lo, y_max=qual_hi)
        self.graph_innov.render_plot(times, innovations, y_min=inn_lo,  y_max=inn_hi)
        self.graph_pan_err.render_plot(times, pan_errors,  y_min=pan_lo,  y_max=pan_hi)
        self.graph_tilt_err.render_plot(times, tilt_errors, y_min=tilt_lo, y_max=tilt_hi)
        self.graph_conf.render_plot(times, confidences,   y_min=conf_lo, y_max=conf_hi)

        # Update Phase Portrait
        self.phase_portrait.update_phase_data(errors_px, times)

