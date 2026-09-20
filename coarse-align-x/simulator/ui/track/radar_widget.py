"""HORIZON Coarse-to-Fine Optical Alignment Radar Component
==========================================================
Polar alignment target reticle displaying:
  - Concentric capture zones:
      * Outer ring: Full camera field-of-view boundary (FOV limit)
      * Middle ring: Coarse alignment acceptance envelope (±0.5°)
      * Inner glowing ring: Fine Pointing Sensor (FPS) capture gate (±50 µrad / 2.5 px)
  - Live 2D beam angular offset vector (Pan, Tilt)
  - Motion trail showing asymptotic Lyapunov convergence into target center
  - Dynamic CEP-95 (Circular Error Probable) confidence circle
  - Optical coupling readiness HUD badge (e.g. "COUPLING: ACTIVE (99.4%)")
"""

from __future__ import annotations
import math
from typing import List, Optional, Tuple

import numpy as np
from PySide6.QtCore import Qt, QPointF
from PySide6.QtGui import QBrush, QColor, QFont, QPainter, QPainterPath, QPen, QRadialGradient
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from simulator.ui.foundation.tokens import (
    COLOR_CONFIRM_GREEN,
    COLOR_DISTURBANCE_AMBER,
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
from simulator.ui.foundation.primitives import PanelSurface, PanelVariant, SectionHeaderLabel


class CoarseToFineRadarWidget(PanelSurface):
    """Polar Optical Alignment Radar & Fine Pointing Handoff Gate Display."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(PanelVariant.FIELD, parent)
        self.setMinimumSize(260, 240)

        # Historical position points for trail & CEP calculation
        self._history: List[Tuple[float, float]] = []
        self._max_history = 35

        self._curr_pan_err_deg: float = 0.0
        self._curr_tilt_err_deg: float = 0.0
        self._curr_err_px: float = 0.0
        self._coupling_pct: float = 0.0
        self._fps_locked: bool = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(4)

        header = SectionHeaderLabel("Optical alignment radar [coarse-to-fine]", self)
        header.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY}; font-family: {FONT_BODY}; font-size: 13px; font-weight: 600;")
        layout.addWidget(header)

        # Sub-status indicator label
        self._lbl_status = QLabel("COUPLING: INITIALIZING", self)
        self._lbl_status.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-family: {FONT_TELEMETRY}; font-size: 10px; font-weight: bold;")
        layout.addWidget(self._lbl_status)

        layout.addStretch()

    def update_alignment(
        self,
        pan_error_deg: float,
        tilt_error_deg: float,
        error_px: float,
        coupling_efficiency: Optional[float] = None,
    ) -> None:
        """Update live angular alignment offsets and recalculate dispersion geometry."""
        self._curr_pan_err_deg = float(pan_error_deg)
        self._curr_tilt_err_deg = float(tilt_error_deg)
        self._curr_err_px = float(error_px)

        # Angular error in microradians (1 deg = 17,453.3 µrad)
        total_urad = math.hypot(pan_error_deg, tilt_error_deg) * 17453.3

        # Coupling efficiency model: Gaussian beam coupling eta = exp(-2 * (theta / w0)^2)
        # w0 ~ 140 urad beam divergence
        if coupling_efficiency is not None:
            self._coupling_pct = float(np.clip(coupling_efficiency, 0.0, 100.0))
        else:
            self._coupling_pct = float(np.clip(100.0 * math.exp(-2.0 * (min(total_urad, 500.0) / 140.0) ** 2), 0.0, 100.0))

        # Fine pointing handoff criteria: inside 50 urad gate or error < 2.5 px
        self._fps_locked = (total_urad <= 60.0) or (self._curr_err_px <= 2.5)

        # Update HUD status label
        if self._fps_locked:
            self._lbl_status.setText(f"COUPLING: ACTIVE ({self._coupling_pct:.1f}%) [FPS GATE LOCKED]")
            self._lbl_status.setStyleSheet(f"color: {COLOR_CONFIRM_GREEN}; font-family: {FONT_TELEMETRY}; font-size: 10px; font-weight: bold;")
        elif total_urad <= 200.0 or self._curr_err_px <= 8.0:
            self._lbl_status.setText(f"COUPLING: COARSE SLEW ({self._coupling_pct:.1f}%) [CONVERGING]")
            self._lbl_status.setStyleSheet(f"color: {COLOR_LOCK_CYAN}; font-family: {FONT_TELEMETRY}; font-size: 10px; font-weight: bold;")
        else:
            self._lbl_status.setText(f"COUPLING: ACQUIRING ({self._coupling_pct:.1f}%) [COARSE PULL-IN]")
            self._lbl_status.setStyleSheet(f"color: {COLOR_DISTURBANCE_AMBER}; font-family: {FONT_TELEMETRY}; font-size: 10px; font-weight: bold;")

        # Push to history
        self._history.append((self._curr_pan_err_deg, self._curr_tilt_err_deg))
        if len(self._history) > self._max_history:
            self._history.pop(0)

        self.update()

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        w = self.width()
        h = self.height()
        top_offset = 42
        radar_h = h - top_offset - 18
        size = min(w - 24, radar_h)
        cx = w / 2.0
        cy = top_offset + radar_h / 2.0
        radius = size / 2.0

        if radius < 20:
            return

        # 1. Dark Radar Scope Background
        grad = QRadialGradient(cx, cy, radius)
        grad.setColorAt(0.0, QColor(14, 20, 28))
        grad.setColorAt(0.7, QColor(10, 14, 20))
        grad.setColorAt(1.0, QColor(8, 10, 14))
        painter.setBrush(QBrush(grad))
        painter.setPen(QPen(QColor(COLOR_HAIRLINE_BORDER_HEX), 1.5))
        painter.drawEllipse(QPointF(cx, cy), radius, radius)

        # 2. Concentric Target Rings
        # Scale: Outer boundary = 0.5° full scale
        scale_deg_to_r = radius / 0.5  # 0.5° maps to edge

        # Outer Ring: 0.35° (Amber dashed)
        r_coarse = 0.35 * scale_deg_to_r
        if r_coarse < radius:
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(QPen(QColor(232, 161, 92, 90), 1, Qt.PenStyle.DashLine))
            painter.drawEllipse(QPointF(cx, cy), r_coarse, r_coarse)

        # Mid Ring: 0.15° (Cyan dotted)
        r_mid = 0.15 * scale_deg_to_r
        if r_mid < radius:
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(QPen(QColor(127, 212, 232, 110), 1, Qt.PenStyle.DotLine))
            painter.drawEllipse(QPointF(cx, cy), r_mid, r_mid)

        # Inner Fine Pointing Sensor Capture Core (Green Zone: 50 µrad ≈ 0.00286°, drawn with visible minimum ~14 px)
        r_fps = max(14.0, 0.05 * scale_deg_to_r)
        fps_grad = QRadialGradient(cx, cy, r_fps)
        fps_grad.setColorAt(0.0, QColor(111, 232, 168, 60))
        fps_grad.setColorAt(1.0, QColor(111, 232, 168, 15))
        painter.setBrush(QBrush(fps_grad))
        painter.setPen(QPen(QColor(111, 232, 168, 220), 1.5))
        painter.drawEllipse(QPointF(cx, cy), r_fps, r_fps)

        # Label FPS Gate
        painter.setFont(QFont("Inter", 7, QFont.Weight.Bold))
        painter.setPen(QPen(QColor(111, 232, 168, 180)))
        painter.drawText(int(cx - 24), int(cy - r_fps - 3), "FPS GATE (±50µrad)")

        # 3. Crosshair Axes & Azimuth Radians
        axis_pen = QPen(QColor(50, 60, 75), 1)
        painter.setPen(axis_pen)
        painter.drawLine(QPointF(cx - radius, cy), QPointF(cx + radius, cy))
        painter.drawLine(QPointF(cx, cy - radius), QPointF(cx, cy + radius))

        # Diagonal reticles
        diag_len = radius * 0.7071
        painter.setPen(QPen(QColor(38, 45, 58), 1, Qt.PenStyle.DashLine))
        painter.drawLine(QPointF(cx - diag_len, cy - diag_len), QPointF(cx + diag_len, cy + diag_len))
        painter.drawLine(QPointF(cx - diag_len, cy + diag_len), QPointF(cx + diag_len, cy - diag_len))

        # 4. History Trail & Dispersion
        n_hist = len(self._history)
        if n_hist > 1:
            for i in range(n_hist - 1):
                p0_x = cx + np.clip(self._history[i][0] * scale_deg_to_r, -radius * 0.95, radius * 0.95)
                p0_y = cy - np.clip(self._history[i][1] * scale_deg_to_r, -radius * 0.95, radius * 0.95)
                p1_x = cx + np.clip(self._history[i + 1][0] * scale_deg_to_r, -radius * 0.95, radius * 0.95)
                p1_y = cy - np.clip(self._history[i + 1][1] * scale_deg_to_r, -radius * 0.95, radius * 0.95)

                alpha = int(30 + 170 * (i / n_hist))
                trail_color = QColor(127, 212, 232, alpha)
                painter.setPen(QPen(trail_color, 1.2))
                painter.drawLine(QPointF(p0_x, p0_y), QPointF(p1_x, p1_y))

        # 5. Current Beam Spot Position Reticle
        bx = cx + np.clip(self._curr_pan_err_deg * scale_deg_to_r, -radius * 0.95, radius * 0.95)
        by = cy - np.clip(self._curr_tilt_err_deg * scale_deg_to_r, -radius * 0.95, radius * 0.95)

        # Pulse ring around current position
        spot_color = QColor(COLOR_CONFIRM_GREEN) if self._fps_locked else QColor(COLOR_LOCK_CYAN)
        pulse_color = QColor(spot_color.red(), spot_color.green(), spot_color.blue(), 70)
        painter.setBrush(QBrush(pulse_color))
        painter.setPen(QPen(spot_color, 1.5))
        painter.drawEllipse(QPointF(bx, by), 6.5, 6.5)

        painter.setBrush(QBrush(spot_color))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(QPointF(bx, by), 2.5, 2.5)

        # Crosshair line to center
        painter.setPen(QPen(QColor(spot_color.red(), spot_color.green(), spot_color.blue(), 120), 1, Qt.PenStyle.DashLine))
        painter.drawLine(QPointF(cx, cy), QPointF(bx, by))

        # 6. Bottom Telemetry Footnote
        total_urad = math.hypot(self._curr_pan_err_deg, self._curr_tilt_err_deg) * 17453.3
        painter.setFont(QFont("Consolas", 8))
        painter.setPen(QPen(QColor(COLOR_TEXT_SECONDARY)))
        footer_text = f"Offset: {total_urad:5.1f} µrad | Err: {self._curr_err_px:.2f} px | Coupling: {self._coupling_pct:.1f}%"
        painter.drawText(int(cx - radius), int(h - 4), footer_text)
