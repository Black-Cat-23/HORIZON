"""HORIZON Phase 11.4 State Estimate Panel Component
=====================================================
Displays state estimate vector components (X, Y, VX, VY, Innovation, Uncertainty).
Uses MonospaceTelemetryLabel primitive (continuously live-updating during run, explicit N/A when idle).
Accompanied by single short lines of plain-language context per value.
"""

from __future__ import annotations
from typing import Optional
import numpy as np
from PySide6.QtWidgets import QFormLayout, QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from simulator.ui.foundation.tokens import (
    COLOR_FIELD,
    COLOR_HAIRLINE_BORDER_HEX,
    COLOR_TEXT_PRIMARY,
    COLOR_TEXT_SECONDARY,
    FONT_BODY,
    SPACING_4,
    SPACING_8,
    SPACING_12,
    SPACING_16,
)
from simulator.ui.foundation.primitives import (
    MonospaceTelemetryLabel,
    PanelSurface,
    PanelVariant,
    SectionHeaderLabel,
)
from tracking.estimation.state import StateEstimate


class StateEstimatePanel(PanelSurface):
    """Kalman State Estimate Vector & Innovation Readout Panel."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(PanelVariant.FIELD, parent)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(SPACING_16, SPACING_12, SPACING_16, SPACING_12)
        main_layout.setSpacing(SPACING_8)

        # Header Title: "State estimate vector" (sentence case)
        header = SectionHeaderLabel("State estimate vector", self)
        header.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY}; font-family: {FONT_BODY}; font-size: 13px; font-weight: 600;")
        main_layout.addWidget(header)

        # Vector Fields Form
        form = QVBoxLayout()
        form.setSpacing(SPACING_4)

        self.telem_x = self._build_field("Position X", "px", "Estimated target X coordinate in sensor frame", form)
        self.telem_y = self._build_field("Position Y", "px", "Estimated target Y coordinate in sensor frame", form)
        self.telem_vx = self._build_field("Velocity Vx", "px/s", "Estimated horizontal target velocity", form)
        self.telem_vy = self._build_field("Velocity Vy", "px/s", "Estimated vertical target velocity", form)
        self.telem_innov = self._build_field("Innovation S", "px", "Measurement residual vs Kalman prediction", form)
        self.telem_uncert = self._build_field("Uncertainty P", "px", "Trace of 2D position covariance matrix", form)

        main_layout.addLayout(form)

    def _build_field(self, label: str, unit: str, context_text: str, parent_layout: QVBoxLayout) -> MonospaceTelemetryLabel:
        container = QWidget(self)
        c_layout = QVBoxLayout(container)
        c_layout.setContentsMargins(0, 0, 0, 0)
        c_layout.setSpacing(2)

        telem = MonospaceTelemetryLabel(value=None, unit=unit, label_text=label, parent=container)
        c_layout.addWidget(telem)

        lbl_ctx = QLabel(f"└  {context_text}", container)
        lbl_ctx.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-family: {FONT_BODY}; font-size: 11px; font-style: italic;")
        c_layout.addWidget(lbl_ctx)

        parent_layout.addWidget(container)
        return telem

    def update_estimate(self, estimate: Optional[StateEstimate]) -> None:
        """Update live monospace state vector values from real Kalman estimate."""
        if estimate is None:
            self.telem_x.set_value(None)
            self.telem_y.set_value(None)
            self.telem_vx.set_value(None)
            self.telem_vy.set_value(None)
            self.telem_innov.set_value(None)
            self.telem_uncert.set_value(None)
            return

        self.telem_x.set_value(estimate.estimated_x, "px")
        self.telem_y.set_value(estimate.estimated_y, "px")
        self.telem_vx.set_value(estimate.estimated_vx, "px/s")
        self.telem_vy.set_value(estimate.estimated_vy, "px/s")

        innov = float(np.linalg.norm(estimate.innovation)) if estimate.innovation is not None else 0.0
        self.telem_innov.set_value(innov, "px")

        uncert = float(np.hypot(estimate.position_sigma_x, estimate.position_sigma_y))
        self.telem_uncert.set_value(uncert, "px")
