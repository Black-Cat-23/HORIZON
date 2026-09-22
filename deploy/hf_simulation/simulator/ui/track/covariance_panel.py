"""HORIZON Phase 11.4 Covariance Diagnostic Panel
=================================================
Provides selectable 1-sigma / 2-sigma / 3-sigma diagnostic views.
Displays mathematically accurate covariance matrix parameters (P_xx, P_yy, major axis, minor axis, orientation).
"""

from __future__ import annotations
from typing import Optional
import numpy as np

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QFormLayout, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from simulator.ui.foundation.tokens import (
    COLOR_FIELD,
    COLOR_FIELD_RAISED,
    COLOR_HAIRLINE_BORDER_HEX,
    COLOR_LOCK_CYAN,
    COLOR_TEXT_PRIMARY,
    COLOR_TEXT_SECONDARY,
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


class CovarianceDiagnosticPanel(PanelSurface):
    """Selectable 1/2/3-Sigma Covariance Diagnostic Panel."""

    sigma_changed = Signal(float)  # Emits 1.0, 2.0, or 3.0

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(PanelVariant.FIELD, parent)
        self.selected_sigma = 2.0

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(SPACING_16, SPACING_12, SPACING_16, SPACING_12)
        main_layout.setSpacing(SPACING_8)

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

        # Live Covariance Metrics (MonospaceTelemetryLabel for live updating values)
        grid = QFormLayout()
        grid.setHorizontalSpacing(SPACING_16)
        grid.setVerticalSpacing(SPACING_4)

        self.telem_pxx = MonospaceTelemetryLabel(value=None, unit="px²", label_text="P_xx Variance", parent=self)
        self.telem_pyy = MonospaceTelemetryLabel(value=None, unit="px²", label_text="P_yy Variance", parent=self)
        self.telem_major = MonospaceTelemetryLabel(value=None, unit="px", label_text="Semi-Major Axis", parent=self)
        self.telem_minor = MonospaceTelemetryLabel(value=None, unit="px", label_text="Semi-Minor Axis", parent=self)
        self.telem_orient = MonospaceTelemetryLabel(value=None, unit="°", label_text="Orientation", parent=self)

        grid.addRow(self.telem_pxx)
        grid.addRow(self.telem_pyy)
        grid.addRow(self.telem_major)
        grid.addRow(self.telem_minor)
        grid.addRow(self.telem_orient)

        main_layout.addLayout(grid)
        self._last_estimate: Optional[StateEstimate] = None
        self.select_sigma(2.0)

    def select_sigma(self, sigma: float) -> None:
        self.selected_sigma = sigma
        for btn, s in [(self.btn_1sig, 1.0), (self.btn_2sig, 2.0), (self.btn_3sig, 3.0)]:
            if s == sigma:
                btn.setStyleSheet(
                    f"background-color: {COLOR_FIELD_RAISED}; color: {COLOR_LOCK_CYAN}; border: 1px solid {COLOR_LOCK_CYAN}; border-radius: 3px; padding: 4px 8px; font-weight: 700; font-size: 11px;"
                )
            else:
                btn.setStyleSheet(
                    f"background-color: transparent; color: {COLOR_TEXT_SECONDARY}; border: 1px solid {COLOR_HAIRLINE_BORDER_HEX}; border-radius: 3px; padding: 4px 8px; font-size: 11px;"
                )

        if hasattr(self, "_last_estimate") and self._last_estimate is not None:
            self.update_covariance(self._last_estimate)

        self.sigma_changed.emit(sigma)

    def update_covariance(self, estimate: Optional[StateEstimate]) -> None:
        self._last_estimate = estimate
        if estimate is None or estimate.covariance is None:
            self.telem_pxx.set_value(None)
            self.telem_pyy.set_value(None)
            self.telem_major.set_value(None)
            self.telem_minor.set_value(None)
            self.telem_orient.set_value(None)
            return

        P = estimate.covariance
        self.telem_pxx.set_value(P[0, 0], "px²")
        self.telem_pyy.set_value(P[1, 1], "px²")

        try:
            conf_level = 0.683 if self.selected_sigma == 1.0 else (0.954 if self.selected_sigma == 2.0 else 0.997)
            ellipse_data = compute_covariance_ellipse(
                P=P,
                center_x=estimate.estimated_x,
                center_y=estimate.estimated_y,
                confidence_level=conf_level,
            )
            sig_str = "1-σ" if self.selected_sigma == 1.0 else ("2-σ" if self.selected_sigma == 2.0 else "3-σ")
            if hasattr(self.telem_major, "_desc_label"):
                self.telem_major._desc_label.setText(f"Semi-Major Axis ({sig_str}):")
            if hasattr(self.telem_minor, "_desc_label"):
                self.telem_minor._desc_label.setText(f"Semi-Minor Axis ({sig_str}):")
            self.telem_major.set_value(ellipse_data.semi_major_axis, "px")
            self.telem_minor.set_value(ellipse_data.semi_minor_axis, "px")
            self.telem_orient.set_value(ellipse_data.orientation_deg, "°")
        except Exception:
            self.telem_major.set_value(None)
            self.telem_minor.set_value(None)
            self.telem_orient.set_value(None)
