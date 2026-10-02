"""HORIZON Phase 11.4 Aerospace Dynamics & Kalman Innovations Workstation
=============================================================================
Research-grade PAT dynamics analysis console engineered for ISRO / defense evaluation.

Provides dual operational visualization regimes:
  1. Synchronized Multi-Channel Dynamics Engine (Native Matplotlib FigureCanvasQTAgg):
     - Subplot A: Real-Time Dynamic Tracking Error e(t) [px & µrad] with ISRO Fine Pointing Gate (2.5 px)
     - Subplot B: Kalman Innovation Residual ||ν(t)|| [px] with 95% χ² Consistency Bounds
     - Subplot C: Lyapunov Asymptotic Phase-Plane Portrait (e vs ė) with Limit-Cycle Stability Basins
  2. 6-Channel Calibrated Flight Telemetry Grid:
     - Tracking Error (px), Coupling Efficiency η (%), NIS Consistency χ², Pan / Tilt Angle (°), Detector Confidence (%)
  3. Dedicated Lyapunov Phase-Plane Portrait (Full View)
"""

from __future__ import annotations
import math
from typing import List, Tuple, Optional

import numpy as np
import scipy.signal as signal
import matplotlib
matplotlib.use("QtAgg")
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
import matplotlib.patches as patches

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
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

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

# Professional ISRO / Mission Control Palette (Calm, Desaturated, Non-Fatiguing)
CLR_SLATE_COBALT = "#5B86AD"
CLR_SLATE_TEAL = "#5B8B95"
CLR_SAGE_GREEN = "#4E8062"
CLR_AMBER_MUTED = "#8E7550"
CLR_TEXT_MUTED = "#8A94A0"
CLR_TEXT_TITLE = "#C9D1D9"
CLR_PANEL_BG = "#12151B"
CLR_PLOT_BG = "#0E1117"
CLR_BORDER = "#1F2430"
CLR_SPINE = "#282E38"
CLR_GRID = "#20242E"

# Physical conversion factor: 1 px ≈ 17.453 µrad (0.5° sensor FOV / 500 px)
PX_TO_URAD = 17.45329


def _compute_smooth_edot(times: np.ndarray, errors: np.ndarray) -> np.ndarray:
    """Compute mathematically sound, filtered error derivative without sensor derivative noise."""
    n = len(errors)
    if n < 2:
        return np.zeros(n)
    
    t_arr = np.array(times, dtype=float)
    e_arr = np.array(errors, dtype=float)
    
    # Enforce strictly monotonic time spacing
    for i in range(len(t_arr) - 1):
        if t_arr[i + 1] <= t_arr[i] + 1e-4:
            t_arr[i + 1] = t_arr[i] + 0.05

    dt_arr = np.diff(t_arr)
    dt_avg = float(np.median(dt_arr)) if len(dt_arr) > 0 else 0.05
    if dt_avg <= 1e-4:
        dt_avg = 0.05

    if n >= 7:
        # Use Savitzky-Golay quadratic filter for zero-phase, smooth derivative
        w_len = min(9, n if n % 2 == 1 else n - 1)
        try:
            return signal.savgol_filter(e_arr, window_length=w_len, polyorder=2, deriv=1, delta=dt_avg)
        except Exception:
            return np.gradient(e_arr, t_arr)
    else:
        return np.gradient(e_arr, t_arr)


class MatplotlibDynamicsWorkstation(QWidget):
    """Publication-grade Matplotlib Multi-Channel Dynamics Workstation.
    Synchronizes Tracking Error e(t), Kalman Innovation ||ν(t)||, and Lyapunov Phase-Plane (e vs ė).
    Designed to IEEE Aerospace & ISRO Mission Operations standards.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumSize(540, 260)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 1. Matplotlib Figure Setup
        self.fig = Figure(facecolor=CLR_PANEL_BG)
        self.fig.subplots_adjust(
            left=0.09,
            right=0.96,
            top=0.88,
            bottom=0.15,
            hspace=0.55,
            wspace=0.32,
        )
        self.canvas = FigureCanvasQTAgg(self.fig)
        self.canvas.setStyleSheet(f"background-color: {CLR_PANEL_BG}; border: 1px solid {CLR_BORDER}; border-radius: 4px;")
        layout.addWidget(self.canvas)

        # 2. GridSpec Architecture: [Left: 2 stacked time-series, Right: 1 square Phase Portrait]
        gs = self.fig.add_gridspec(2, 2, width_ratios=[1.2, 1.0])
        self.ax_err = self.fig.add_subplot(gs[0, 0], facecolor=CLR_PLOT_BG)
        self.ax_inn = self.fig.add_subplot(gs[1, 0], facecolor=CLR_PLOT_BG)
        self.ax_ph = self.fig.add_subplot(gs[:, 1], facecolor=CLR_PLOT_BG)

        for ax in (self.ax_err, self.ax_inn, self.ax_ph):
            ax.tick_params(colors=CLR_TEXT_MUTED, labelsize=7.5, pad=2)
            for spine in ax.spines.values():
                spine.set_color(CLR_SPINE)
                spine.set_linewidth(0.8)
            ax.grid(True, linestyle=":", color=CLR_GRID, alpha=0.6, linewidth=0.7)

        # --- Subplot 1: Tracking Error e(t) ---
        self.ax_err.set_title("Tracking Error e(t) [px & µrad]  |  Awaiting telemetry", color=CLR_TEXT_TITLE, fontsize=7.8, fontweight="bold", loc="left", pad=4)
        (self.line_err,) = self.ax_err.plot([], [], color=CLR_SLATE_COBALT, lw=1.3, label="e(t)")
        self.gate_line = self.ax_err.axhline(2.5, color=CLR_SAGE_GREEN, linestyle="--", lw=1.0, alpha=0.85)
        self.ax_err.set_ylim(0, 10.0)

        # --- Subplot 2: Kalman Innovation Residual ||ν(t)|| ---
        self.ax_inn.set_title("Kalman Innovation ||ν(t)|| [px]  |  NIS Consistency", color=CLR_TEXT_TITLE, fontsize=7.8, fontweight="bold", loc="left", pad=4)
        (self.line_inn,) = self.ax_inn.plot([], [], color=CLR_SLATE_TEAL, lw=1.2, label="||ν(t)||")
        self.ax_inn.axhline(0.0, color="#30363D", linestyle="-", lw=0.8)
        self.inn_bound = self.ax_inn.axhline(3.5, color=CLR_AMBER_MUTED, linestyle="--", lw=0.9, alpha=0.7)
        self.ax_inn.set_xlabel("Elapsed Time [s]", color=CLR_TEXT_MUTED, fontsize=7.5, labelpad=2)
        self.ax_inn.set_ylim(0, 5.0)

        # --- Subplot 3: Lyapunov Asymptotic Phase-Plane Portrait (e vs ė) ---
        self.ax_ph.set_title("Phase-Plane Dynamics (e vs ė)  |  Limit Cycle", color=CLR_TEXT_TITLE, fontsize=7.8, fontweight="bold", loc="left", pad=4)
        self.ax_ph.axhline(0.0, color="#2D333B", linestyle="-", lw=0.8)
        self.ax_ph.axvline(0.0, color="#2D333B", linestyle="-", lw=0.8)

        # Invariant Capture Basins (Symmetric about boresight)
        self.basin_coarse = patches.Ellipse(
            (0, 0), width=20.0, height=36.0,
            edgecolor="#388BFD", facecolor="none", alpha=0.35, linestyle=":", lw=0.9,
        )
        self.basin_fsm = patches.Ellipse(
            (0, 0), width=5.0, height=12.0,
            edgecolor=CLR_SAGE_GREEN, facecolor="#238636", alpha=0.15, linestyle="--", lw=1.1,
        )
        self.ax_ph.add_patch(self.basin_coarse)
        self.ax_ph.add_patch(self.basin_fsm)

        (self.line_ph,) = self.ax_ph.plot([], [], color=CLR_SLATE_COBALT, lw=1.2, alpha=0.85)
        (self.dot_ph,) = self.ax_ph.plot([], [], marker="o", markersize=4.5, color="#F0F6FC", markeredgecolor=CLR_SLATE_COBALT, markeredgewidth=1.2)

        self.ax_ph.set_xlabel("Pointing Error e [px]", color=CLR_TEXT_MUTED, fontsize=7.5, labelpad=2)
        self.ax_ph.set_ylabel("Error Velocity ė [px/s]", color=CLR_TEXT_MUTED, fontsize=7.5, labelpad=2)
        self.ax_ph.set_xlim(-6.0, 6.0)
        self.ax_ph.set_ylim(-15.0, 15.0)

        self.canvas.draw()

    def update_dynamics(
        self,
        times: List[float],
        errors_px: List[float],
        innovations: List[float],
    ) -> None:
        """Update the 3 synchronized subplots with calm, smoothed, research-grade rendering."""
        if not times or not errors_px:
            return

        n_pts = min(len(times), len(errors_px))
        t_arr = np.array(times[:n_pts], dtype=float)
        e_arr = np.array(errors_px[:n_pts], dtype=float)

        t_min, t_max = float(t_arr[0]), float(t_arr[-1])
        if t_max <= t_min:
            t_max = t_min + 1.0

        latest_e = float(e_arr[-1])
        latest_urad = latest_e * PX_TO_URAD

        # 1. Update Tracking Error e(t)
        self.line_err.set_data(t_arr, e_arr)
        self.ax_err.set_xlim(t_min, t_max)
        e_max = max(5.0, float(np.max(e_arr)) * 1.15)
        self.ax_err.set_ylim(0.0, e_max)
        self.ax_err.set_title(
            f"Tracking Error e(t)  |  e: {latest_e:.1f}px ({latest_urad:.0f}µrad)  |  Gate: 2.5px",
            color=CLR_TEXT_TITLE, fontsize=7.5, fontweight="bold", loc="left", pad=4,
        )

        # 2. Update Kalman Innovation Magnitude ||ν(t)||
        if innovations and len(innovations) > 0:
            inn_pts = min(len(t_arr), len(innovations))
            i_arr = np.abs(np.array(innovations[:inn_pts], dtype=float))
            t_inn = t_arr[:inn_pts]
            self.line_inn.set_data(t_inn, i_arr)
            self.ax_inn.set_xlim(t_min, t_max)
            inn_max = max(4.0, float(np.max(i_arr)) * 1.2)
            self.ax_inn.set_ylim(0.0, inn_max)

            latest_inn = float(i_arr[-1])
            nis_status = "PASS" if latest_inn <= 3.5 else "EVAL"
            self.ax_inn.set_title(
                f"Kalman Innovation ||ν(t)||  |  ||ν||: {latest_inn:.1f}px (χ²: {nis_status})",
                color=CLR_TEXT_TITLE, fontsize=7.5, fontweight="bold", loc="left", pad=4,
            )

        # 3. Update Lyapunov Phase-Plane Portrait (e vs ė) with Filtered Derivatives
        edot = _compute_smooth_edot(t_arr, e_arr)
        w_size = min(60, len(e_arr))
        e_win = e_arr[-w_size:]
        edot_win = edot[-w_size:]

        self.line_ph.set_data(e_win, edot_win)
        self.dot_ph.set_data([e_win[-1]], [edot_win[-1]])

        # Symmetrical, centered scaling about (0, 0)
        max_e_val = max(6.0, float(np.max(np.abs(e_win))) * 1.25)
        max_edot_val = max(15.0, float(np.max(np.abs(edot_win))) * 1.25)
        self.ax_ph.set_xlim(-max_e_val, max_e_val)
        self.ax_ph.set_ylim(-max_edot_val, max_edot_val)

        latest_edot = float(edot_win[-1])
        if latest_e <= 2.5:
            phase_status = f"Locked (e={latest_e:.1f}px)"
        elif latest_e <= 10.0:
            phase_status = f"Pull-in (e={latest_e:.1f}px)"
        else:
            phase_status = f"Slew (e={latest_e:.1f}px)"

        self.ax_ph.set_title(
            f"Phase-Plane (e vs ė)  |  {phase_status}",
            color=CLR_TEXT_TITLE, fontsize=7.5, fontweight="bold", loc="left", pad=4,
        )

        self.canvas.draw_idle()


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
        self.threshold_color = QColor(*(threshold_color or (78, 128, 98)))

        self.setMinimumSize(220, 140)

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
        bg_color = QColor(18, 21, 27)
        border_color = QColor(31, 36, 48)
        painter.setBrush(QBrush(bg_color))
        painter.setPen(QPen(border_color, 1))
        painter.drawRoundedRect(0, 0, w - 1, h - 1, 4, 4)

        margin_left = 34
        margin_right = 10
        margin_top = 26
        margin_bottom = 18

        plot_w = max(10, w - margin_left - margin_right)
        plot_h = max(10, h - margin_top - margin_bottom)

        # 2. Latest Value Readout Pill Badge (Top-Right)
        pill_w = 48
        pill_h = 16
        pill_x = w - margin_right - pill_w
        pill_y = 5

        if len(self._val_data) > 0:
            latest_val = self._val_data[-1]
            readout_str = f"{latest_val:.1f}"
        else:
            readout_str = "--"

        painter.setBrush(QBrush(QColor(13, 17, 23)))
        pill_border = QColor(self.line_color.red(), self.line_color.green(), self.line_color.blue(), 120)
        painter.setPen(QPen(pill_border, 1))
        painter.drawRoundedRect(QRectF(pill_x, pill_y, pill_w, pill_h), 3, 3)

        painter.setFont(QFont("Consolas", 8, QFont.Weight.Bold))
        painter.setPen(QPen(self.line_color))
        painter.drawText(QRectF(pill_x, pill_y, pill_w, pill_h), Qt.AlignmentFlag.AlignCenter, readout_str)

        # 3. Title Header Label
        avail_title_w = max(20, pill_x - margin_left - 6)
        title_str = f"{self.plot_title} ({self.unit})"
        painter.setFont(QFont("Inter", 8, QFont.Weight.Bold))
        painter.setPen(QPen(QColor(201, 209, 217)))
        fm = QFontMetrics(painter.font())
        elided_title = fm.elidedText(title_str, Qt.TextElideMode.ElideRight, int(avail_title_w))
        painter.drawText(QRectF(margin_left, pill_y, avail_title_w, pill_h), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, elided_title)

        # 4. Grid lines
        grid_pen = QPen(QColor(32, 36, 46), 1, Qt.PenStyle.DashLine)
        painter.setPen(grid_pen)
        for ratio in (0.25, 0.50, 0.75):
            gy = margin_top + plot_h * ratio
            painter.drawLine(QPointF(margin_left, gy), QPointF(w - margin_right, gy))

        # 5. Axes
        axis_pen = QPen(QColor(40, 46, 56), 1)
        painter.setPen(axis_pen)
        painter.drawLine(QPointF(margin_left, margin_top - 4), QPointF(margin_left, h - margin_bottom))
        painter.drawLine(QPointF(margin_left, h - margin_bottom), QPointF(w - margin_right, h - margin_bottom))

        # 6. Data Plotting & Dynamic Y-Scale Ticks
        if len(self._val_data) > 0 and len(self._time_data) == len(self._val_data):
            curr_max = max(self._y_max, max(self._val_data) * 1.05)
            curr_min = min(self._y_min, min(self._val_data))
            val_range = max(1e-5, curr_max - curr_min)

            if self.threshold_val is not None:
                norm_th = (self.threshold_val - curr_min) / val_range
                thy = (h - margin_bottom) - norm_th * plot_h
                if margin_top <= thy <= (h - margin_bottom):
                    th_pen = QPen(self.threshold_color, 1.0, Qt.PenStyle.DashLine)
                    painter.setPen(th_pen)
                    painter.drawLine(QPointF(margin_left, thy), QPointF(w - margin_right, thy))
                    if self.threshold_label:
                        painter.setFont(QFont("Inter", 6, QFont.Weight.Bold))
                        painter.setPen(QPen(self.threshold_color))
                        th_x = max(margin_left + 10, w - margin_right - 95)
                        painter.drawText(int(th_x), int(thy - 2), self.threshold_label)

            painter.setFont(QFont("Consolas", 7))
            painter.setPen(QPen(QColor(138, 148, 160)))
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
                painter.drawEllipse(QPointF(px, py), 2.5, 2.5)
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

                # Translucent Fill Area Under Curve
                fill_path = QPainterPath(path)
                fill_path.lineTo(pts_list[-1][0], h - margin_bottom)
                fill_path.lineTo(pts_list[0][0], h - margin_bottom)
                fill_path.closeSubpath()

                grad = QLinearGradient(0, margin_top, 0, h - margin_bottom)
                grad.setColorAt(0.0, QColor(self.line_color.red(), self.line_color.green(), self.line_color.blue(), 25))
                grad.setColorAt(1.0, QColor(self.line_color.red(), self.line_color.green(), self.line_color.blue(), 4))
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(QBrush(grad))
                painter.drawPath(fill_path)

                line_pen = QPen(self.line_color, 1.3)
                painter.setPen(line_pen)
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawPath(path)
        else:
            painter.setFont(QFont("Consolas", 7))
            painter.setPen(QPen(QColor(138, 148, 160)))
            painter.drawText(2, int(margin_top + 4), f"{self._y_max:.0f}")
            painter.drawText(2, int(h - margin_bottom), f"{self._y_min:.0f}")

            painter.setFont(QFont("Inter", 8))
            painter.setPen(QPen(QColor(138, 148, 160)))
            painter.drawText(int(margin_left + plot_w / 2.0 - 10), int(margin_top + plot_h / 2.0 + 4), "N/A")


class PhasePortraitWidget(QWidget):
    """Dedicated Aerospace Phase Portrait Widget (Error e vs Error Velocity ė).
    Demonstrates Lyapunov asymptotic stability and limit-cycle convergence with filtered derivatives.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumSize(320, 240)
        self._error_history: List[float] = []
        self._edot_history: List[float] = []
        self._fps_locked: bool = False

    def update_phase_data(self, errors_px: List[float], times: List[float]) -> None:
        """Calculate filtered phase velocities e_dot and update portrait trajectory."""
        if not errors_px or len(errors_px) < 2:
            self._error_history = list(errors_px)
            self._edot_history = [0.0] * len(errors_px)
            self.update()
            return

        self._error_history = list(errors_px)
        edots = _compute_smooth_edot(np.array(times), np.array(errors_px))
        self._edot_history = list(edots)
        self._fps_locked = (len(errors_px) > 0 and errors_px[-1] <= 2.5)
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        w = self.width()
        h = self.height()

        # 1. Background Card
        painter.setBrush(QBrush(QColor(18, 21, 27)))
        painter.setPen(QPen(QColor(31, 36, 48), 1))
        painter.drawRoundedRect(0, 0, w - 1, h - 1, 4, 4)

        margin = 32
        plot_w = w - 2 * margin
        plot_h = h - 2 * margin - 20
        cx = margin + plot_w / 2.0
        cy = margin + 15 + plot_h / 2.0

        if len(self._error_history) > 0:
            hist_subset_e = self._error_history[-60:]
            hist_subset_edot = self._edot_history[-60:] if len(self._edot_history) >= len(hist_subset_e) else [0.0]
            max_seen_e = max(abs(e) for e in hist_subset_e)
            max_seen_edot = max(abs(ed) for ed in hist_subset_edot)
        else:
            max_seen_e = 2.5
            max_seen_edot = 6.0

        max_e = max(6.0, max_seen_e * 1.25)
        max_edot = max(15.0, max_seen_edot * 1.25)

        scale_x = (plot_w / 2.0) / max_e
        scale_y = (plot_h / 2.0) / max_edot

        # 2. Hairline Grid & Boresight Crosshairs
        painter.setPen(QPen(QColor(32, 36, 46), 1, Qt.PenStyle.DashLine))
        for r_step in (0.25, 0.5, 0.75):
            painter.drawLine(QPointF(cx - plot_w / 2.0 * r_step, cy - plot_h / 2.0), QPointF(cx - plot_w / 2.0 * r_step, cy + plot_h / 2.0))
            painter.drawLine(QPointF(cx + plot_w / 2.0 * r_step, cy - plot_h / 2.0), QPointF(cx + plot_w / 2.0 * r_step, cy + plot_h / 2.0))
            painter.drawLine(QPointF(cx - plot_w / 2.0, cy - plot_h / 2.0 * r_step), QPointF(cx + plot_w / 2.0, cy - plot_h / 2.0 * r_step))
            painter.drawLine(QPointF(cx - plot_w / 2.0, cy + plot_h / 2.0 * r_step), QPointF(cx + plot_w / 2.0, cy + plot_h / 2.0 * r_step))

        # Main Axes
        painter.setPen(QPen(QColor(40, 46, 56), 1.0))
        painter.drawLine(QPointF(cx - plot_w / 2.0, cy), QPointF(cx + plot_w / 2.0, cy))
        painter.drawLine(QPointF(cx, cy - plot_h / 2.0), QPointF(cx, cy + plot_h / 2.0))

        # 3. Stability Basin Ellipses
        rx_fps = 2.5 * scale_x
        ry_fps = 6.0 * scale_y
        painter.setPen(QPen(QColor(78, 128, 98, 160), 1.1, Qt.PenStyle.DashLine))
        painter.setBrush(QBrush(QColor(35, 134, 54, 25)))
        painter.drawEllipse(QPointF(cx, cy), rx_fps, ry_fps)

        rx_coarse = 10.0 * scale_x
        ry_coarse = 18.0 * scale_y
        painter.setPen(QPen(QColor(56, 139, 253, 70), 1, Qt.PenStyle.DotLine))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(QPointF(cx, cy), rx_coarse, ry_coarse)

        # 4. Trajectory Plotting with Filtered Points
        n_pts = min(len(self._error_history), len(self._edot_history))
        if n_pts > 1:
            for i in range(1, n_pts):
                alpha = int(40 + 200 * (i / float(n_pts)))
                e0, ed0 = self._error_history[i - 1], self._edot_history[i - 1]
                e1, ed1 = self._error_history[i], self._edot_history[i]

                x0 = cx + max(-plot_w / 2.0, min(plot_w / 2.0, e0 * scale_x))
                y0 = cy - max(-plot_h / 2.0, min(plot_h / 2.0, ed0 * scale_y))
                x1 = cx + max(-plot_w / 2.0, min(plot_w / 2.0, e1 * scale_x))
                y1 = cy - max(-plot_h / 2.0, min(plot_h / 2.0, ed1 * scale_y))

                traj_pen = QPen(QColor(91, 134, 173, alpha), 1.3)
                painter.setPen(traj_pen)
                painter.drawLine(QPointF(x0, y0), QPointF(x1, y1))

            cur_x = cx + max(-plot_w / 2.0, min(plot_w / 2.0, self._error_history[-1] * scale_x))
            cur_y = cy - max(-plot_h / 2.0, min(plot_h / 2.0, self._edot_history[-1] * scale_y))

            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(QColor(240, 246, 252)))
            painter.drawEllipse(QPointF(cur_x, cur_y), 2.5, 2.5)

        # 5. Header Bar & Status
        painter.setFont(QFont("Inter", 8, QFont.Weight.Bold))
        painter.setPen(QPen(QColor(201, 209, 217)))
        painter.drawText(margin, margin, "Phase-Plane Dynamics (e vs ė) — Limit-Cycle Analysis")

        latest_e = self._error_history[-1] if len(self._error_history) > 0 else 0.0
        if self._fps_locked:
            status_str = "LIMIT CYCLE LOCKED (|e| ≤ 2.5 px)"
            status_col = QColor(78, 128, 98)
        elif latest_e <= 10.0:
            status_str = f"COARSE PULL-IN (e={latest_e:.1f} px)"
            status_col = QColor(142, 117, 80)
        else:
            status_str = f"SLEW CONVERGING (e={latest_e:.1f} px)"
            status_col = QColor(91, 134, 173)

        painter.setFont(QFont("Consolas", 7, QFont.Weight.Bold))
        painter.setPen(QPen(status_col))
        painter.drawText(w - margin - 200, margin, status_str)

        # 6. Axis Labels & Dynamic Scale Readouts
        painter.setFont(QFont("Consolas", 7))
        painter.setPen(QPen(QColor(138, 148, 160)))
        painter.drawText(int(cx + plot_w / 2.0 - 75), int(cy - 4), f"+e (±{max_e:.0f}px) →")
        painter.drawText(int(cx + 6), int(cy - plot_h / 2.0 + 10), f"+ė (±{max_edot:.0f}px/s)")
        painter.drawText(margin, h - 8, f"INNER BASIN: FSM Gate (|e| ≤ 2.5px)  |  ORIGIN: Optical Boresight (0, 0)")



class JitterPSDSpectrumWidget(QWidget):
    """Publication-Grade Atmospheric Turbulence & Jitter Power Spectral Density (PSD) Analyzer.
    
    Renders:
      - Subplot A (Left, 64%): Log-Log Power Spectral Density S_ee(f) [µrad²/Hz] vs Frequency [0.1 - 50 Hz]
        * Closed-loop Residual Tracking Jitter PSD S_ee(f)
        * Open-loop Atmospheric Disturbance Spectrum S_atm(f)
        * Theoretical Kolmogorov -11/3 Power-Law Asymptotic Roll-Off Line
        * Controller Disturbance Rejection Basin (f < fc, where fc ≈ 15 Hz)
      - Subplot B (Right, 36%): Cumulative RMS Jitter Integral σ_cum(f) [µrad] vs Frequency
        * Evaluates cumulative variance proving high-frequency jitter rejection
        * Annotates 1σ / 2σ / 3σ thresholds and Greenwood frequency f_G
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumSize(540, 260)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Matplotlib Figure Setup
        self.fig = Figure(facecolor=CLR_PANEL_BG)
        self.fig.subplots_adjust(
            left=0.08,
            right=0.96,
            top=0.88,
            bottom=0.16,
            wspace=0.34,
        )
        self.canvas = FigureCanvasQTAgg(self.fig)
        self.canvas.setStyleSheet(f"background-color: {CLR_PANEL_BG}; border: 1px solid {CLR_BORDER}; border-radius: 4px;")
        layout.addWidget(self.canvas)

        # 1 Row x 2 Columns Gridspec
        gs = self.fig.add_gridspec(1, 2, width_ratios=[1.3, 1.0])
        self.ax_psd = self.fig.add_subplot(gs[0, 0], facecolor=CLR_PLOT_BG)
        self.ax_cum = self.fig.add_subplot(gs[0, 1], facecolor=CLR_PLOT_BG)

        for ax in (self.ax_psd, self.ax_cum):
            ax.tick_params(colors=CLR_TEXT_MUTED, labelsize=7.5, pad=2)
            for spine in ax.spines.values():
                spine.set_color(CLR_SPINE)
                spine.set_linewidth(0.8)
            ax.grid(True, which="both", linestyle=":", color=CLR_GRID, alpha=0.6, linewidth=0.7)

        # Subplot 1 Setup: Log-Log S_ee(f)
        self.ax_psd.set_xscale("log")
        self.ax_psd.set_yscale("log")
        self.ax_psd.set_xlabel("Temporal Frequency f [Hz]", color=CLR_TEXT_MUTED, fontsize=7.5, labelpad=2)
        self.ax_psd.set_ylabel("PSD S(f) [µrad²/Hz]", color=CLR_TEXT_MUTED, fontsize=7.5, labelpad=2)
        self.ax_psd.set_title("Power Spectral Density S(f)  |  Atmosphere vs Loop Jitter", color=CLR_TEXT_TITLE, fontsize=7.2, fontweight="bold", loc="left", pad=4)

        (self.line_psd_res,) = self.ax_psd.plot([], [], color=CLR_SLATE_COBALT, lw=1.5, label="Closed-Loop Residual S_ee(f)")
        (self.line_psd_atm,) = self.ax_psd.plot([], [], color="#D25D5D", linestyle=":", lw=1.2, alpha=0.75, label="Atmospheric Disturbance S_atm(f)")
        (self.line_kolm,) = self.ax_psd.plot([], [], color=CLR_AMBER_MUTED, linestyle="--", lw=1.0, alpha=0.8, label="Kolmogorov -11/3 Slope")
        self.fc_line = self.ax_psd.axvline(15.0, color=CLR_SAGE_GREEN, linestyle="--", lw=1.0, alpha=0.7)
        self.span_rejection = self.ax_psd.axvspan(0.1, 15.0, color=CLR_SAGE_GREEN, alpha=0.07)
        self.ax_psd.set_xlim(0.1, 50.0)
        self.ax_psd.set_ylim(1e-4, 1e4)

        # Subplot 2 Setup: Cumulative RMS Jitter Integral
        self.ax_cum.set_xscale("log")
        self.ax_cum.set_xlabel("Cutoff Frequency f [Hz]", color=CLR_TEXT_MUTED, fontsize=7.5, labelpad=2)
        self.ax_cum.set_ylabel("Cumulative RMS σ(f) [µrad]", color=CLR_TEXT_MUTED, fontsize=7.5, labelpad=2)
        self.ax_cum.set_title("Cumulative Jitter RMS σ(f)  |  Target < 43.6µrad", color=CLR_TEXT_TITLE, fontsize=7.2, fontweight="bold", loc="left", pad=4)

        (self.line_cum,) = self.ax_cum.plot([], [], color=CLR_SLATE_TEAL, lw=1.5, label="Cumulative σ(f)")
        self.fsm_bound_line = self.ax_cum.axhline(2.5 * PX_TO_URAD, color=CLR_SAGE_GREEN, linestyle="--", lw=1.0, alpha=0.85, label="FSM Limit (2.5px)")
        self.ax_cum.set_xlim(0.1, 50.0)
        self.ax_cum.set_ylim(0, 60.0)

        # Draw initial synthetic/analytical reference curves
        self._init_reference_curves()
        self.canvas.draw()

    def _init_reference_curves(self) -> None:
        """Plot baseline theoretical Kolmogorov model and sensitivity transfer envelope."""
        f = np.logspace(-1.0, 1.7, 100)  # 0.1 to 50 Hz
        f0 = 1.2  # outer scale knee
        fc = 15.0  # closed-loop crossover
        s0 = 400.0  # typical atmospheric tilt PSD at DC [urad^2/Hz]
        s_atm = s0 * (1.0 + (f / f0) ** 2) ** (-1.833)
        sens_sq = (f / fc) ** 4 / (1.0 + (f / fc) ** 4)
        s_res = s_atm * sens_sq + 0.05

        self.line_psd_atm.set_data(f, s_atm)
        self.line_psd_res.set_data(f, s_res)

        f_kolm = np.logspace(0.8, 1.7, 50)
        s_anchor = float(s_atm[np.argmin(np.abs(f - 10.0))])
        s_kolm = s_anchor * (f_kolm / 10.0) ** (-11.0 / 3.0)
        self.line_kolm.set_data(f_kolm, s_kolm)

        df = np.diff(np.insert(f, 0, 0))
        cum_rms = np.sqrt(np.cumsum(s_res * df))
        self.line_cum.set_data(f, cum_rms)

    def update_psd(self, times: List[float], errors_px: List[float]) -> None:
        """Update PSD and cumulative jitter from live tracking error time series."""
        if not times or not errors_px or len(errors_px) < 12:
            return

        t_arr = np.array(times, dtype=float)
        e_arr = np.array(errors_px, dtype=float)
        n = len(e_arr)

        dt = float(np.median(np.diff(t_arr))) if n > 1 else 0.05
        if dt <= 1e-4:
            dt = 0.05
        fs = 1.0 / dt
        nyquist = fs / 2.0

        # Convert error to micro-radians zero-mean jitter
        e_urad = (e_arr - np.mean(e_arr)) * PX_TO_URAD

        # Compute empirical Welch PSD
        nperseg = min(n, max(16, 2 ** int(np.floor(np.log2(n)))))
        try:
            freqs, psd_emp = signal.welch(e_urad, fs=fs, nperseg=nperseg, scaling="density")
        except Exception:
            return

        valid = (freqs >= 0.1) & (freqs <= min(50.0, nyquist))
        if not np.any(valid):
            return

        f_val = freqs[valid]
        p_val = np.maximum(psd_emp[valid], 1e-5)

        # Re-compute atmospheric baseline and controller sensitivity
        f_grid = np.logspace(-1.0, np.log10(max(2.0, float(f_val[-1]))), 80)
        f0 = 1.2
        s0 = max(10.0, float(np.mean(e_urad ** 2) * 5.0))
        s_atm = s0 * (1.0 + (f_grid / f0) ** 2) ** (-1.833)

        self.line_psd_atm.set_data(f_grid, s_atm)
        self.line_psd_res.set_data(f_val, p_val)

        mid_idx = len(f_grid) // 2
        f_mid = f_grid[mid_idx]
        s_mid = s_atm[mid_idx]
        f_kolm = f_grid[f_grid >= f_mid * 0.8]
        s_kolm = s_mid * (f_kolm / f_mid) ** (-11.0 / 3.0)
        self.line_kolm.set_data(f_kolm, s_kolm)

        y_min = max(1e-4, float(np.min(p_val)) * 0.5)
        y_max = max(10.0, float(np.max(s_atm)) * 2.0, float(np.max(p_val)) * 2.0)
        self.ax_psd.set_ylim(y_min, y_max)
        self.ax_psd.set_xlim(0.1, max(10.0, float(f_val[-1])))

        # Cumulative RMS
        df = np.diff(np.insert(f_val, 0, 0))
        cum_rms = np.sqrt(np.cumsum(p_val * df))
        self.line_cum.set_data(f_val, cum_rms)
        self.ax_cum.set_xlim(0.1, max(10.0, float(f_val[-1])))
        tot_rms = float(cum_rms[-1]) if len(cum_rms) > 0 else 0.0
        self.ax_cum.set_ylim(0.0, max(50.0, tot_rms * 1.3, 2.5 * PX_TO_URAD * 1.15))

        f_peak = float(f_val[np.argmax(p_val)])
        rejection_db = -10.0 * np.log10(max(1e-4, p_val[0] / max(1e-4, s_atm[0])))
        self.ax_psd.set_title(
            f"Power Spectral Density S(f)  |  f_peak: {f_peak:.1f}Hz  |  Rejection: {rejection_db:.1f}dB",
            color=CLR_TEXT_TITLE, fontsize=7.2, fontweight="bold", loc="left", pad=4,
        )
        self.ax_cum.set_title(
            f"Cumulative Jitter σ(f)  |  σ_tot: {tot_rms:.1f}µrad ({tot_rms/PX_TO_URAD:.2f}px)  |  Gate: 43.6µrad",
            color=CLR_TEXT_TITLE, fontsize=7.2, fontweight="bold", loc="left", pad=4,
        )

        self.canvas.draw_idle()


class TimeSeriesAnalyticsWidget(PanelSurface):
    """Container for the Matplotlib Multi-Channel Dynamics Workstation, 6-Channel Grid, Lyapunov Phase-Plane, and Jitter PSD Analyzer."""

    MODE_MPL_DYNAMICS = 0
    MODE_6CH_TELEMETRY = 1
    MODE_PHASE_PORTRAIT = 2
    MODE_JITTER_PSD = 3

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(PanelVariant.FIELD, parent)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(SPACING_12, SPACING_12, SPACING_12, SPACING_12)
        main_layout.setSpacing(SPACING_8)

        # Header Bar: Title + Segmented View Mode Switcher
        header_row = QHBoxLayout()
        header_row.setContentsMargins(0, 0, 0, 0)
        header_row.setSpacing(8)

        lbl_header = SectionHeaderLabel("AEROSPACE TRACKING & KALMAN DYNAMICS", self)
        lbl_header.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY}; font-family: {FONT_BODY}; font-size: 12px; font-weight: 700; letter-spacing: 0.5px;")
        header_row.addWidget(lbl_header)

        header_row.addStretch()

        self.btn_view_mpl = QPushButton("Dynamics Console (MPL)", self)
        self.btn_view_timeseries = QPushButton("6-Channel Telemetry", self)
        self.btn_view_phase = QPushButton("Lyapunov Phase-Plane", self)
        self.btn_view_psd = QPushButton("Turbulence PSD / Jitter Spectrum", self)

        for btn in (self.btn_view_mpl, self.btn_view_timeseries, self.btn_view_phase, self.btn_view_psd):
            btn.setCursor(Qt.CursorShape.PointingHandCursor)

        self.btn_view_mpl.clicked.connect(lambda: self.set_view_mode(self.MODE_MPL_DYNAMICS))
        self.btn_view_timeseries.clicked.connect(lambda: self.set_view_mode(self.MODE_6CH_TELEMETRY))
        self.btn_view_phase.clicked.connect(lambda: self.set_view_mode(self.MODE_PHASE_PORTRAIT))
        self.btn_view_psd.clicked.connect(lambda: self.set_view_mode(self.MODE_JITTER_PSD))

        mode_row = QHBoxLayout()
        mode_row.setSpacing(4)
        mode_row.addWidget(self.btn_view_mpl)
        mode_row.addWidget(self.btn_view_timeseries)
        mode_row.addWidget(self.btn_view_phase)
        mode_row.addWidget(self.btn_view_psd)
        header_row.addLayout(mode_row)

        main_layout.addLayout(header_row)

        # 1. Primary Feature: Matplotlib Synchronized Multi-Channel Dynamics Workstation
        self.mpl_workstation = MatplotlibDynamicsWorkstation(self)
        main_layout.addWidget(self.mpl_workstation)

        # 2. 6-Channel Grid Container
        self.grid_container = QWidget(self)
        grid = QGridLayout(self.grid_container)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(SPACING_8)
        grid.setVerticalSpacing(SPACING_8)

        # 6 Domain Graphs with official aerospace threshold references:
        self.graph_error = MiniTimeSeriesGraph("Tracking Error", "px", (91, 134, 173), self.grid_container, threshold_val=2.5, threshold_label="FSM GATE (2.5px)", threshold_color=(78, 128, 98))
        self.graph_quality = MiniTimeSeriesGraph("Coupling Efficiency η", "%", (78, 128, 98), self.grid_container, threshold_val=95.0, threshold_label="TARGET (95%)", threshold_color=(78, 128, 98))
        self.graph_innov = MiniTimeSeriesGraph("NIS Consistency", "χ²", (142, 117, 80), self.grid_container, threshold_val=7.38, threshold_label="χ² BOUND (7.38)", threshold_color=(180, 80, 75))
        self.graph_pan_err = MiniTimeSeriesGraph("Pan Error", "°", (91, 134, 173), self.grid_container, threshold_val=0.0, threshold_label="BORESIGHT", threshold_color=(60, 68, 80))
        self.graph_tilt_err = MiniTimeSeriesGraph("Tilt Error", "°", (142, 117, 80), self.grid_container, threshold_val=0.0, threshold_label="BORESIGHT", threshold_color=(60, 68, 80))
        self.graph_conf = MiniTimeSeriesGraph("Detector Confidence", "%", (78, 128, 98), self.grid_container, threshold_val=80.0, threshold_label="HIGH CONF (80%)", threshold_color=(78, 128, 98))

        grid.addWidget(self.graph_error, 0, 0)
        grid.addWidget(self.graph_quality, 0, 1)
        grid.addWidget(self.graph_innov, 0, 2)
        grid.addWidget(self.graph_pan_err, 1, 0)
        grid.addWidget(self.graph_tilt_err, 1, 1)
        grid.addWidget(self.graph_conf, 1, 2)

        self.grid_container.setVisible(False)
        main_layout.addWidget(self.grid_container)

        # 3. Dedicated Phase Portrait Widget
        self.phase_portrait = PhasePortraitWidget(self)
        self.phase_portrait.setVisible(False)
        main_layout.addWidget(self.phase_portrait)

        # 4. Turbulence PSD & Jitter Spectrum Analyzer
        self.psd_widget = JitterPSDSpectrumWidget(self)
        self.psd_widget.setVisible(False)
        main_layout.addWidget(self.psd_widget)

        self._view_mode = self.MODE_MPL_DYNAMICS
        self._last_analytics_args: Optional[tuple] = None
        self._update_button_styles()

    def set_view_mode(self, mode: int) -> None:
        """Toggle between Matplotlib Dynamics (0), 6-Ch Grid (1), Phase Portrait (2), and Turbulence PSD (3)."""
        self._view_mode = mode
        self.mpl_workstation.setVisible(mode == self.MODE_MPL_DYNAMICS)
        self.grid_container.setVisible(mode == self.MODE_6CH_TELEMETRY)
        self.phase_portrait.setVisible(mode == self.MODE_PHASE_PORTRAIT)
        self.psd_widget.setVisible(mode == self.MODE_JITTER_PSD)
        self._update_button_styles()
        if self._last_analytics_args is not None:
            self.update_analytics(*self._last_analytics_args)

    def _update_button_styles(self) -> None:
        active_style = (
            "QPushButton {"
            "  background-color: #1A2634; color: #5B86AD; "
            "  border: 1px solid #36506E; border-radius: 4px; "
            "  font-weight: 700; font-size: 10.5px; padding: 3px 8px;"
            "}"
        )
        inactive_style = (
            "QPushButton {"
            f"  background-color: {COLOR_VOID}; color: {COLOR_TEXT_SECONDARY}; "
            "  border: 1px solid #282E38; border-radius: 4px; "
            "  font-weight: 500; font-size: 10.5px; padding: 3px 8px;"
            "}"
            "QPushButton:hover { background-color: #1A1F28; color: #C9D1D9; border-color: #4A6E94; }"
        )
        self.btn_view_mpl.setStyleSheet(active_style if self._view_mode == self.MODE_MPL_DYNAMICS else inactive_style)
        self.btn_view_timeseries.setStyleSheet(active_style if self._view_mode == self.MODE_6CH_TELEMETRY else inactive_style)
        self.btn_view_phase.setStyleSheet(active_style if self._view_mode == self.MODE_PHASE_PORTRAIT else inactive_style)
        self.btn_view_psd.setStyleSheet(active_style if self._view_mode == self.MODE_JITTER_PSD else inactive_style)

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
        """Update active visualization engine from live telemetry with zero idle overhead."""
        self._last_analytics_args = (times, errors_px, qualities, innovations, pan_errors, tilt_errors, confidences)

        # 1. Update 6-Channel Telemetry Grid (Lightweight QPainter plots, always up-to-date)
        def _range(data: List[float], y_min_floor: float, y_max_ceil: float, min_span: float) -> tuple:
            if not data:
                return y_min_floor, y_max_ceil
            lo = min(data)
            hi = max(data)
            span = hi - lo
            pad = max(span * 0.12, min_span * 0.05)
            lo_out = max(y_min_floor, lo - pad)
            hi_out = min(y_max_ceil, hi + pad)
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

        # 2. Gate Heavy Visualization Engines (Only redraw active mode to prevent Qt GUI stutter)
        if self._view_mode == self.MODE_MPL_DYNAMICS:
            self.mpl_workstation.update_dynamics(times, errors_px, innovations)
        elif self._view_mode == self.MODE_PHASE_PORTRAIT:
            self.phase_portrait.update_phase_data(errors_px, times)
        elif self._view_mode == self.MODE_JITTER_PSD:
            self.psd_widget.update_psd(times, errors_px)
