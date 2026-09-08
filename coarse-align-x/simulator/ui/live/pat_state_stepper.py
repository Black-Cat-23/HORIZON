"""HORIZON Phase 11.2 PAT State Progression Display
======================================================
Live instrument state readout showing full PAT state machine lifecycle:
  SEARCH -> ACQUIRE -> TRACK -> DEGRADED -> REACQUIRE

Active State: StateIndicatorPill primitive with full semantic color.
Inactive States: Quieter unfilled/outlined pill with text-secondary styling.
"""

from __future__ import annotations
from typing import Dict
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from simulator.ui.foundation.tokens import (
    COLOR_FIELD,
    COLOR_FIELD_RAISED,
    COLOR_HAIRLINE_BORDER_HEX,
    COLOR_TEXT_PRIMARY,
    COLOR_TEXT_SECONDARY,
    FONT_BODY,
    SPACING_4,
    SPACING_8,
    SPACING_12,
    SPACING_16,
    TYPE_SCALE_MICRO,
)
from simulator.ui.foundation.primitives import (
    PanelSurface,
    PanelVariant,
    SectionHeaderLabel,
    StateIndicatorPill,
    StatePillState,
)
from pat.state import PATMode


class PATStateStepPill(QWidget):
    """Individual PAT state step pill (filled when active, outlined when inactive)."""

    def __init__(self, mode: PATMode, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.mode = mode
        self.is_active = False

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Active state indicator pill
        self.active_pill = StateIndicatorPill(self._map_state(mode), label_text=mode.value, parent=self)
        layout.addWidget(self.active_pill)

        # Inactive state label primitive
        self.inactive_lbl = QLabel(f" {mode.value} ", self)
        self.inactive_lbl.setStyleSheet(
            f"""
            QLabel {{
                background-color: transparent;
                color: {COLOR_TEXT_SECONDARY};
                font-family: 'General Sans', sans-serif;
                font-size: {TYPE_SCALE_MICRO}px;
                font-weight: 600;
                border: 1px solid {COLOR_HAIRLINE_BORDER_HEX};
                border-radius: 3px;
                padding: {SPACING_4}px {SPACING_8}px;
            }}
            """
        )
        layout.addWidget(self.inactive_lbl)

        self.set_active(False)

    def _map_state(self, mode: PATMode) -> StatePillState:
        if mode == PATMode.TRACK:
            return StatePillState.ACTIVE
        elif mode == PATMode.ACQUIRE:
            return StatePillState.CONFIRMED
        elif mode == PATMode.DEGRADED:
            return StatePillState.DEGRADED
        elif mode == PATMode.REACQUIRE:
            return StatePillState.LOST
        else:
            return StatePillState.IDLE

    def set_active(self, active: bool) -> None:
        self.is_active = active
        self.active_pill.setVisible(active)
        self.inactive_lbl.setVisible(not active)


class PATStateProgressionWidget(PanelSurface):
    """PAT State Machine Progression Stepper Readout."""

    PAT_SEQUENCE = [
        PATMode.SEARCH,
        PATMode.ACQUIRE,
        PATMode.TRACK,
        PATMode.DEGRADED,
        PATMode.REACQUIRE,
    ]

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(PanelVariant.FIELD, parent)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(SPACING_16, SPACING_12, SPACING_16, SPACING_12)
        main_layout.setSpacing(SPACING_8)

        # Title: "PAT state progression" (sentence case)
        header = SectionHeaderLabel("PAT state progression", self)
        header.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY}; font-family: {FONT_BODY}; font-size: 13px; font-weight: 600;")
        main_layout.addWidget(header)

        # Horizontal progression strip with step arrows ->
        strip_layout = QHBoxLayout()
        strip_layout.setContentsMargins(0, 0, 0, 0)
        strip_layout.setSpacing(SPACING_8)

        self.pills: Dict[PATMode, PATStateStepPill] = {}

        for idx, mode in enumerate(self.PAT_SEQUENCE):
            pill = PATStateStepPill(mode, self)
            strip_layout.addWidget(pill)
            self.pills[mode] = pill

            if idx < len(self.PAT_SEQUENCE) - 1:
                arrow = QLabel("→", self)
                arrow.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-size: 12px; font-weight: bold;")
                strip_layout.addWidget(arrow)

        strip_layout.addStretch()
        main_layout.addLayout(strip_layout)

        # Default active state: SEARCH
        self.set_active_mode(PATMode.SEARCH)

    def set_active_mode(self, active_mode: PATMode) -> None:
        """Update active PAT mode readout."""
        for mode, pill in self.pills.items():
            pill.set_active(mode == active_mode)
