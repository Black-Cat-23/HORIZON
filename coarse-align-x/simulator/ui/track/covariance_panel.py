"""HORIZON Phase 11.4 Covariance Diagnostic Panel
=================================================
Provides selectable 1-sigma / 2-sigma / 3-sigma diagnostic views.
Displays mathematically accurate covariance matrix parameters (P_xx, P_yy, major axis, minor axis, orientation).
"""

from __future__ import annotations
import math
from typing import Optional
import numpy as np

from PySide6.QtCore import Qt, Signal, QPointF
from PySide6.QtGui import QBrush, QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QGridLayout, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from simulator.ui.foundation.tokens import (
    COLOR_CONFIRM_GREEN,
    COLOR_FIELD,
    COLOR_FIELD_RAISED,
    COLOR_HAIRLINE_BORDER_HEX,
    COLOR_LOCK_CYAN,
    COLOR_TEXT_PRIMARY,
    COLOR_TEXT_SECONDARY,
    COLOR_VOID,
    FONT_BODY,
    FONT_TELEMETRY,
    SPACING_4,
    SPACING_8,
    SPACING_12,
    SPACING_16,
    TYPE_SCALE_MICRO,
)
from simulator.ui.foundation.primitives import (
    MonospaceTelemetryLabel,
    PanelSurface,
    PanelVariant,
    SecondaryButton,
    SectionHeaderLabel,
)
from tracking.estimation.covariance import compute_covariance_ellipse
from tracking.estimation.state import StateEstimate


class VectorEllipseCompassWidget(QWidget):
    """Vector-rendered 2D covariance ellipse compass card."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumSize(95, 95)
        self.setMaximumSize(130, 130)
        self.selected_sigma = 2.0
        self.semi_major = 2.0
        self.semi_minor = 2.0
        self.orientation_deg = 0.0
        self.nis_score = 0.0

    def update_compass(
        self,
        selected_sigma: float,
        semi_major: float,
        semi_minor: float,
        orientation_deg: float,
        nis_score: float,
    ) -> None:
        self.selected_sigma = selected_sigma
        self.semi_major = max(0.2, semi_major)
        self.semi_minor = max(0.2, semi_minor)
        self.orientation_deg = orientation_deg
        self.nis_score = nis_score
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        w = self.width()
        h = self.height()
        cx = w / 2.0
        cy = h / 2.0 - 4
        radius = min(w / 2.0 - 10, h / 2.0 - 12)

        if radius < 12:
            return

        # Background Card
        painter.setBrush(QBrush(QColor(10, 12, 16)))
        painter.setPen(QPen(QColor(40, 46, 56), 1))
        painter.drawRoundedRect(1, 1, w - 2, h - 2, 4, 4)

        # Reticle Crosshairs
        painter.setPen(QPen(QColor(45, 52, 64), 1, Qt.PenStyle.DashLine))
        painter.drawLine(QPointF(cx - radius, cy), QPointF(cx + radius, cy))
        painter.drawLine(QPointF(cx, cy - radius), QPointF(cx, cy + radius))

        # Scaling factor to fit compass
        max_axis = max(self.semi_major, 1.0)
        scale = (radius * 0.85) / max(max_axis, 3.0)

        # 3 Nested Sigma Ellipses
        ang = int(round(self.orientation_deg))
        for s_lvl, mult, lbl in [(1.0, 1.0 / 2.0, "1s"), (2.0, 1.0, "2s"), (3.0, 1.5, "3s")]:
            is_active = (self.selected_sigma == s_lvl)
            ax_maj = max(2, int(round(self.semi_major * scale * mult)))
            ax_min = max(2, int(round(self.semi_minor * scale * mult)))

            if is_active:
                pen = QPen(QColor(COLOR_LOCK_CYAN), 2.0)
                brush = QBrush(QColor(127, 212, 232, 40))
            else:
                pen = QPen(QColor(60, 70, 85), 1.0, Qt.PenStyle.DashLine)
                brush = Qt.BrushStyle.NoBrush

            painter.setPen(pen)
            painter.setBrush(brush)
            painter.save()
            painter.translate(cx, cy)
            painter.rotate(ang)
            painter.drawEllipse(QPointF(0, 0), float(ax_maj), float(ax_min))
            painter.restore()

        # Orientation Leader Needle
        rad = math.radians(self.orientation_deg)
        nx = cx + math.cos(rad) * radius * 0.9
        ny = cy + math.sin(rad) * radius * 0.9
        painter.setPen(QPen(QColor(232, 161, 92), 1.6))
        painter.drawLine(QPointF(cx, cy), QPointF(nx, ny))

        # Bottom Info: Orientation Heading & NIS
        painter.setFont(QFont("Consolas", 7))
        painter.setPen(QPen(QColor(COLOR_TEXT_SECONDARY)))
        info_str = f"θ={self.orientation_deg:.1f}°"
        painter.drawText(int(cx - 20), int(h - 4), info_str)


class CovarianceDiagnosticPanel(PanelSurface):
    """Selectable 1/2/3-Sigma Covariance Diagnostic Panel with side-by-side layout."""

    sigma_changed = Signal(float)  # Emits 1.0, 2.0, or 3.0

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(PanelVariant.FIELD, parent)
        self.selected_sigma = 2.0

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(SPACING_12, SPACING_8, SPACING_12, SPACING_8)
        main_layout.setSpacing(6)

        # Header Title: "Covariance diagnostics" (sentence case)
        header = SectionHeaderLabel("Covariance diagnostics", self)
        header.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY}; font-family: {FONT_BODY}; font-size: 13px; font-weight: 600;")
        main_layout.addWidget(header)

        # 1-Sigma / 2-Sigma / 3-Sigma Selector Bank
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(SPACING_4)

        self.btn_1sig = QPushButton("1-σ (68.3%)", self)
        self.btn_2sig = QPushButton("2-σ (95.4%)", self)
        self.btn_3sig = QPushButton("3-σ (99.7%)", self)

        for btn, sigma_val in [(self.btn_1sig, 1.0), (self.btn_2sig, 2.0), (self.btn_3sig, 3.0)]:
            btn.clicked.connect(lambda _, s=sigma_val: self.select_sigma(s))
            btn_layout.addWidget(btn)

        main_layout.addLayout(btn_layout)

        # Side-by-Side Body Layout: Left (5x2 compact grid) + Right (2D Vector Compass)
        body_row = QHBoxLayout()
        body_row.setContentsMargins(0, 0, 0, 0)
        body_row.setSpacing(SPACING_8)

        # Left Column: Compact Metrics Grid (5 rows x 2 columns)
        metrics_container = QWidget(self)
        grid = QGridLayout(metrics_container)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(SPACING_8)
        grid.setVerticalSpacing(2)

        # Dynamic sigma bounds that multiply by 1x, 2x, 3x on click
        self.telem_bound_x = MonospaceTelemetryLabel(value=None, unit="px", label_text="2-σ Bound X", parent=metrics_container)
        self.telem_bound_y = MonospaceTelemetryLabel(value=None, unit="px", label_text="2-σ Bound Y", parent=metrics_container)
        self.telem_major = MonospaceTelemetryLabel(value=None, unit="px", label_text="Major (2-σ)", parent=metrics_container)
        self.telem_minor = MonospaceTelemetryLabel(value=None, unit="px", label_text="Minor (2-σ)", parent=metrics_container)

        # Base Matrix parameters
        self.telem_pxx = MonospaceTelemetryLabel(value=None, unit="px²", label_text="P_xx Var", parent=metrics_container)
        self.telem_pyy = MonospaceTelemetryLabel(value=None, unit="px²", label_text="P_yy Var", parent=metrics_container)
        self.telem_pxy = MonospaceTelemetryLabel(value=None, unit="px²", label_text="P_xy Cross", parent=metrics_container)
        self.telem_aspect = MonospaceTelemetryLabel(value=None, unit="ratio", label_text="Anisotropy", parent=metrics_container)
        self.telem_orient = MonospaceTelemetryLabel(value=None, unit="°", label_text="Orientation", parent=metrics_container)
        self.telem_nis = MonospaceTelemetryLabel(value=None, unit="score", label_text="NIS (χ²)", parent=metrics_container)

        grid.addWidget(self.telem_bound_x, 0, 0)
        grid.addWidget(self.telem_bound_y, 0, 1)
        grid.addWidget(self.telem_major, 1, 0)
        grid.addWidget(self.telem_minor, 1, 1)
        grid.addWidget(self.telem_pxx, 2, 0)
        grid.addWidget(self.telem_pyy, 2, 1)
        grid.addWidget(self.telem_pxy, 3, 0)
        grid.addWidget(self.telem_aspect, 3, 1)
        grid.addWidget(self.telem_orient, 4, 0)
        grid.addWidget(self.telem_nis, 4, 1)

        body_row.addWidget(metrics_container, stretch=3)

        # Right Column: Interactive 2D Vector Compass
        self.compass = VectorEllipseCompassWidget(self)
        body_row.addWidget(self.compass, stretch=2)

        main_layout.addLayout(body_row)
        self._last_estimate: Optional[StateEstimate] = None
        self.select_sigma(2.0)

    def select_sigma(self, sigma: float) -> None:
        self.selected_sigma = sigma
        sig_str = "1-σ" if sigma == 1.0 else ("2-σ" if sigma == 2.0 else "3-σ")

        for btn, s in [(self.btn_1sig, 1.0), (self.btn_2sig, 2.0), (self.btn_3sig, 3.0)]:
            if s == sigma:
                btn.setStyleSheet(
                    f"background-color: {COLOR_FIELD_RAISED}; color: {COLOR_LOCK_CYAN}; border: 1px solid {COLOR_LOCK_CYAN}; border-radius: 3px; padding: 4px 8px; font-weight: 700; font-size: 11px;"
                )
            else:
                btn.setStyleSheet(
                    f"background-color: transparent; color: {COLOR_TEXT_SECONDARY}; border: 1px solid {COLOR_HAIRLINE_BORDER_HEX}; border-radius: 3px; padding: 4px 8px; font-size: 11px;"
                )

        if hasattr(self.telem_bound_x, "_desc_label"):
            self.telem_bound_x._desc_label.setText(f"{sig_str} Bound X:")
        if hasattr(self.telem_bound_y, "_desc_label"):
            self.telem_bound_y._desc_label.setText(f"{sig_str} Bound Y:")
        if hasattr(self.telem_major, "_desc_label"):
            self.telem_major._desc_label.setText(f"Major ({sig_str}):")
        if hasattr(self.telem_minor, "_desc_label"):
            self.telem_minor._desc_label.setText(f"Minor ({sig_str}):")

        if hasattr(self, "_last_estimate") and self._last_estimate is not None:
            self.update_covariance(self._last_estimate)

        self.sigma_changed.emit(sigma)

    def update_covariance(self, estimate: Optional[StateEstimate]) -> None:
        self._last_estimate = estimate
        if estimate is None or estimate.covariance is None:
            self.telem_bound_x.set_value(None)
            self.telem_bound_y.set_value(None)
            self.telem_pxx.set_value(None)
            self.telem_pyy.set_value(None)
            self.telem_pxy.set_value(None)
            self.telem_aspect.set_value(None)
            self.telem_major.set_value(None)
            self.telem_minor.set_value(None)
            self.telem_orient.set_value(None)
            self.telem_nis.set_value(None)
            return

        P = estimate.covariance
        self.telem_pxx.set_value(P[0, 0], "px²")
        self.telem_pyy.set_value(P[1, 1], "px²")
        self.telem_pxy.set_value(P[0, 1], "px²")

        # Dynamic uncertainty bounds at selected sigma level (1x, 2x, 3x multiplier)
        k_mult = float(self.selected_sigma)
        bound_x = k_mult * math.sqrt(max(0.0, float(P[0, 0])))
        bound_y = k_mult * math.sqrt(max(0.0, float(P[1, 1])))
        self.telem_bound_x.set_value(bound_x, "px")
        self.telem_bound_y.set_value(bound_y, "px")

        try:
            conf_level = 0.683 if self.selected_sigma == 1.0 else (0.954 if self.selected_sigma == 2.0 else 0.997)
            ellipse_data = compute_covariance_ellipse(
                P=P,
                center_x=estimate.estimated_x,
                center_y=estimate.estimated_y,
                confidence_level=conf_level,
            )

            self.telem_major.set_value(ellipse_data.semi_major_axis, "px")
            self.telem_minor.set_value(ellipse_data.semi_minor_axis, "px")
            self.telem_orient.set_value(ellipse_data.orientation_deg, "°")

            aspect = ellipse_data.semi_major_axis / max(0.01, ellipse_data.semi_minor_axis)
            self.telem_aspect.set_value(aspect, "ratio")

            nis_score = getattr(estimate, "nis", 0.0)
            self.telem_nis.set_value(nis_score, "score")

            # Update interactive vector compass
            self.compass.update_compass(
                selected_sigma=self.selected_sigma,
                semi_major=ellipse_data.semi_major_axis,
                semi_minor=ellipse_data.semi_minor_axis,
                orientation_deg=ellipse_data.orientation_deg,
                nis_score=nis_score,
            )
        except Exception:
            self.telem_major.set_value(None)
            self.telem_minor.set_value(None)
            self.telem_orient.set_value(None)
            self.telem_aspect.set_value(None)
            self.telem_nis.set_value(None)
