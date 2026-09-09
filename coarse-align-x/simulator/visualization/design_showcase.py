"""
HORIZON Design Foundation Layer Component Showcase (Patched)
============================================================
Non-shipped PySide6 engineering verification viewer to inspect every Phase 11.0 primitive
against realistic states (IDLE, ACTIVE, CONFIRMED, DEGRADED, LOST, N/A) using true neutral surfaces.

Usage:
    python -m simulator.visualization.design_showcase
"""

from __future__ import annotations
import sys
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from simulator.ui.foundation.tokens import (
    COLOR_VOID,
    COLOR_TEXT_PRIMARY,
    COLOR_TEXT_SECONDARY,
    SPACING_8,
    SPACING_12,
    SPACING_16,
    SPACING_24,
    TYPE_SCALE_TITLE,
)
from simulator.ui.foundation.primitives import (
    ExpandableDiagnosticContainer,
    MonospaceTelemetryLabel,
    PanelSurface,
    PanelVariant,
    PrimaryButton,
    SecondaryButton,
    SectionHeaderLabel,
    StateIndicatorPill,
    StatePillState,
)


class DesignShowcaseWindow(QMainWindow):
    """Component showcase window for Phase 11.0 Acceptance Verification."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("HORIZON Phase 11.0 — Design Foundation Showcase (Patched)")
        self.resize(1000, 750)
        self.setStyleSheet(f"QMainWindow {{ background-color: {COLOR_VOID}; }}")

        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(SPACING_24, SPACING_24, SPACING_24, SPACING_24)
        main_layout.setSpacing(SPACING_16)

        # Header Title
        title_label = QLabel("HORIZON Design System Foundation", self)
        title_label.setStyleSheet(
            f"color: {COLOR_TEXT_PRIMARY}; font-family: 'Space Grotesk', sans-serif; font-size: {TYPE_SCALE_TITLE}px; font-weight: 700;"
        )
        main_layout.addWidget(title_label)

        subtitle_label = QLabel("Non-shipped verification showcase for true neutral surfaces, motion curves, and primitives.", self)
        subtitle_label.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-family: 'General Sans', sans-serif; font-size: 14px;")
        main_layout.addWidget(subtitle_label)

        # Horizontal Row for 3 Panel Variant Surfaces (void, field, field-raised)
        panels_layout = QHBoxLayout()
        panels_layout.setSpacing(SPACING_16)

        # Panel 1: Void Surface
        self.panel_void = PanelSurface(PanelVariant.VOID, self)
        p1_layout = QVBoxLayout(self.panel_void)
        p1_layout.setContentsMargins(SPACING_16, SPACING_16, SPACING_16, SPACING_16)
        p1_layout.setSpacing(SPACING_12)
        p1_layout.addWidget(SectionHeaderLabel("Surface Variant 1: Void (#0A0A0B)", self.panel_void))
        p1_layout.addWidget(StateIndicatorPill(StatePillState.IDLE, parent=self.panel_void))
        p1_layout.addWidget(MonospaceTelemetryLabel(value=0.00, unit="px", font_size_px=16, parent=self.panel_void))
        p1_layout.addStretch()
        panels_layout.addWidget(self.panel_void)

        # Panel 2: Field Surface
        self.panel_field = PanelSurface(PanelVariant.FIELD, self)
        p2_layout = QVBoxLayout(self.panel_field)
        p2_layout.setContentsMargins(SPACING_16, SPACING_16, SPACING_16, SPACING_16)
        p2_layout.setSpacing(SPACING_12)
        p2_layout.addWidget(SectionHeaderLabel("Surface Variant 2: Field (#16161A)", self.panel_field))
        self.pill_active = StateIndicatorPill(StatePillState.ACTIVE, parent=self.panel_field)
        p2_layout.addWidget(self.pill_active)
        self.pill_confirmed = StateIndicatorPill(StatePillState.CONFIRMED, parent=self.panel_field)
        p2_layout.addWidget(self.pill_confirmed)
        p2_layout.addWidget(MonospaceTelemetryLabel(value=14.82, unit="px/s", font_size_px=16, parent=self.panel_field))
        p2_layout.addStretch()
        panels_layout.addWidget(self.panel_field)

        # Panel 3: Field-Raised Surface
        self.panel_raised = PanelSurface(PanelVariant.FIELD_RAISED, self)
        p3_layout = QVBoxLayout(self.panel_raised)
        p3_layout.setContentsMargins(SPACING_16, SPACING_16, SPACING_16, SPACING_16)
        p3_layout.setSpacing(SPACING_12)
        p3_layout.addWidget(SectionHeaderLabel("Surface Variant 3: Raised (#202024)", self.panel_raised))
        self.pill_degraded = StateIndicatorPill(StatePillState.DEGRADED, parent=self.panel_raised)
        p3_layout.addWidget(self.pill_degraded)
        self.pill_lost = StateIndicatorPill(StatePillState.LOST, parent=self.panel_raised)
        p3_layout.addWidget(self.pill_lost)
        p3_layout.addWidget(MonospaceTelemetryLabel(value=None, unit="px (Offline)", font_size_px=16, parent=self.panel_raised))
        p3_layout.addStretch()
        panels_layout.addWidget(self.panel_raised)

        main_layout.addLayout(panels_layout)

        # Interactive Controls & Buttons Row
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(SPACING_12)

        self.btn_primary = PrimaryButton("Execute Step", self)
        self.btn_secondary = SecondaryButton("Reset Controls", self)
        self.btn_cycle = SecondaryButton("⚡ Cycle State Pills", self)
        self.btn_cycle.clicked.connect(self._cycle_states)

        btn_layout.addWidget(self.btn_primary)
        btn_layout.addWidget(self.btn_secondary)
        btn_layout.addWidget(self.btn_cycle)
        btn_layout.addStretch()
        main_layout.addLayout(btn_layout)

        # Expandable Diagnostic Container
        diag_container = ExpandableDiagnosticContainer("Diagnostic Telemetry State Registers", self)
        diag_inner = QVBoxLayout()
        diag_inner.addWidget(SectionHeaderLabel("Register Telemetry Dump", diag_container))
        diag_inner.addWidget(MonospaceTelemetryLabel(value=1024.50, unit="Hz", font_size_px=14, parent=diag_container))
        diag_inner.addWidget(MonospaceTelemetryLabel(value=0.0167, unit="s", font_size_px=14, parent=diag_container))
        diag_container.content_layout.addLayout(diag_inner)
        main_layout.addWidget(diag_container)

        main_layout.addStretch()

        self._state_index = 0

    def _cycle_states(self) -> None:
        states = [StatePillState.IDLE, StatePillState.ACTIVE, StatePillState.CONFIRMED, StatePillState.DEGRADED, StatePillState.LOST]
        self._state_index = (self._state_index + 1) % len(states)
        next_state = states[self._state_index]
        self.pill_active.set_state(next_state)


def main() -> None:
    app = QApplication.instance() or QApplication(sys.argv)
    window = DesignShowcaseWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
