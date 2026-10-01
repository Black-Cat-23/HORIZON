"""HORIZON Phase 11.4 State Estimate Panel Component
=====================================================
Displays state estimate vector components (X, Y, VX, VY, Innovation, Uncertainty)
along with Dual-Stage PAT Actuator Allocation (Gimbal Coarse Slew vs FSM Piezo Deflection).
Uses MonospaceTelemetryLabel primitive (continuously live-updating during run, explicit N/A when idle).
Accompanied by clean technical context lines.
"""

from __future__ import annotations
import math
from typing import Optional
import numpy as np
from PySide6.QtWidgets import QFrame, QGridLayout, QHBoxLayout, QLabel, QVBoxLayout, QWidget

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

# Physical conversion factor: 1 px ≈ 17.453 µrad
PX_TO_URAD = 17.45329


class StateEstimatePanel(PanelSurface):
    """Kalman State Estimate Vector & Dual-Stage PAT Actuator Readout Panel."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(PanelVariant.FIELD, parent)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(SPACING_16, SPACING_8, SPACING_16, SPACING_8)
        main_layout.setSpacing(6)

        # Header Title: "IMM-Kalman state vector & actuators"
        header = SectionHeaderLabel("IMM-Kalman state vector & actuators", self)
        header.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY}; font-family: {FONT_BODY}; font-size: 12px; font-weight: 700; letter-spacing: 0.5px;")
        main_layout.addWidget(header)

        # Vector Fields Form (Compact 2-column layout for spatial kinematics)
        vector_container = QWidget(self)
        v_grid = QGridLayout(vector_container)
        v_grid.setContentsMargins(0, 0, 0, 0)
        v_grid.setHorizontalSpacing(SPACING_12)
        v_grid.setVerticalSpacing(4)

        self.telem_x = self._build_compact_field("Position X", "px", "Target horizontal centroid", v_grid, 0, 0)
        self.telem_y = self._build_compact_field("Position Y", "px", "Target vertical centroid", v_grid, 0, 1)
        self.telem_vx = self._build_compact_field("Velocity Vx", "px/s", "Horizontal velocity", v_grid, 1, 0)
        self.telem_vy = self._build_compact_field("Velocity Vy", "px/s", "Vertical velocity", v_grid, 1, 1)
        self.telem_innov = self._build_compact_field("Innovation S", "px", "Measurement residual", v_grid, 2, 0)
        self.telem_uncert = self._build_compact_field("Uncertainty P", "px", "Position 1-σ radius", v_grid, 2, 1)

        main_layout.addWidget(vector_container)

        # Hairline Divider
        sep = QFrame(self)
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color: #282E38; margin: 2px 0px;")
        main_layout.addWidget(sep)

        # Dual-Stage Actuator Allocation Readout
        actuator_container = QWidget(self)
        a_grid = QGridLayout(actuator_container)
        a_grid.setContentsMargins(0, 0, 0, 0)
        a_grid.setHorizontalSpacing(SPACING_12)
        a_grid.setVerticalSpacing(2)

        self.telem_gimbal = MonospaceTelemetryLabel(value=None, unit="°/s", label_text="Coarse Slew Rate", font_size_px=11, parent=actuator_container)
        self.telem_fsm = MonospaceTelemetryLabel(value=None, unit="µrad", label_text="FSM Piezo Deflection", font_size_px=11, parent=actuator_container)

        a_grid.addWidget(self.telem_gimbal, 0, 0)
        a_grid.addWidget(self.telem_fsm, 0, 1)
        main_layout.addWidget(actuator_container)

    def _build_compact_field(
        self, label: str, unit: str, context_text: str, grid: QGridLayout, row: int, col: int
    ) -> MonospaceTelemetryLabel:
        container = QWidget(self)
        c_layout = QVBoxLayout(container)
        c_layout.setContentsMargins(0, 0, 0, 0)
        c_layout.setSpacing(1)

        telem = MonospaceTelemetryLabel(value=None, unit=unit, label_text=label, font_size_px=11, parent=container)
        c_layout.addWidget(telem)

        lbl_ctx = QLabel(f"└  {context_text}", container)
        lbl_ctx.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-family: {FONT_BODY}; font-size: 10px; font-style: italic;")
        c_layout.addWidget(lbl_ctx)

        grid.addWidget(container, row, col)
        return telem

    def update_estimate(self, estimate: Optional[StateEstimate], pat_state: Optional[object] = None) -> None:
        """Update live monospace state vector values and dual-stage actuator commands."""
        if estimate is None:
            self.telem_x.set_value(None)
            self.telem_y.set_value(None)
            self.telem_vx.set_value(None)
            self.telem_vy.set_value(None)
            self.telem_innov.set_value(None)
            self.telem_uncert.set_value(None)
            self.telem_gimbal.set_value(None)
            self.telem_fsm.set_value(None)
            return

        self.telem_x.set_value(estimate.estimated_x, "px")
        self.telem_y.set_value(estimate.estimated_y, "px")
        self.telem_vx.set_value(estimate.estimated_vx, "px/s")
        self.telem_vy.set_value(estimate.estimated_vy, "px/s")

        innov = float(np.linalg.norm(estimate.innovation)) if estimate.innovation is not None else 0.0
        self.telem_innov.set_value(innov, "px")

        uncert = float(np.hypot(estimate.position_sigma_x, estimate.position_sigma_y))
        self.telem_uncert.set_value(uncert, "px")

        # Dual-stage actuator allocation
        if pat_state is not None:
            pan_deg = getattr(pat_state, "pan_error_deg", 0.0)
            tilt_deg = getattr(pat_state, "tilt_error_deg", 0.0)
            err_ang = float(math.hypot(pan_deg, tilt_deg))
            # Physical camera optical conversion factor: 640 px / 4.0 deg FOV = 160.0 px/deg
            err_px = err_ang * 160.0

            # Slew rate: proportional coarse gimbal command clamped to ±1.5 °/s
            slew_rate = min(1.50, err_ang * 1.8)
            self.telem_gimbal.set_value(slew_rate, "°/s")

            # FSM Piezo deflection in microradians (linear optical stroke ±50 µrad)
            fsm_stroke = min(50.0, err_px * PX_TO_URAD)
            self.telem_fsm.set_value(fsm_stroke, "µrad")
        else:
            self.telem_gimbal.set_value(None)
            self.telem_fsm.set_value(None)
