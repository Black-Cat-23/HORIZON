"""
State Indicator Pill Component Primitive (Patched All-Caps Scoping)
===================================================================
Uses ONLY the four fixed semantic colors (lock-cyan, confirm-green, disturbance-amber, lost-red)
plus an explicit neutral IDLE state using neither color.
Restricted to short ALL-CAPS tags with 0.03em letter-spacing.
"""

from __future__ import annotations
from enum import Enum
from PySide6.QtWidgets import QLabel, QWidget
from simulator.ui.foundation.tokens import (
    COLOR_CONFIRM_GREEN,
    COLOR_DISTURBANCE_AMBER,
    COLOR_FIELD_RAISED,
    COLOR_LOCK_CYAN,
    COLOR_LOST_RED,
    COLOR_TEXT_SECONDARY,
    SPACING_4,
    SPACING_8,
    TYPE_SCALE_MICRO,
)


class StatePillState(str, Enum):
    IDLE = "IDLE"
    ACTIVE = "ACTIVE"
    CONFIRMED = "CONFIRMED"
    DEGRADED = "DEGRADED"
    LOST = "LOST"


class StateIndicatorPill(QLabel):
    """Semantic status indicator pill primitive."""

    def __init__(self, state: StatePillState = StatePillState.IDLE, label_text: str | None = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.state = state
        self.custom_text = label_text
        self._update_appearance()

    def set_state(self, state: StatePillState, label_text: str | None = None) -> None:
        self.state = state
        if label_text is not None:
            self.custom_text = label_text
        self._update_appearance()

    def _update_appearance(self) -> None:
        bg_color = COLOR_FIELD_RAISED
        text_color = COLOR_TEXT_SECONDARY
        raw_text = self.custom_text or self.state.value
        text = raw_text.upper()

        if self.state == StatePillState.ACTIVE:
            text_color = COLOR_LOCK_CYAN
            bg_color = "rgba(127, 212, 232, 0.15)"
        elif self.state == StatePillState.CONFIRMED:
            text_color = COLOR_CONFIRM_GREEN
            bg_color = "rgba(111, 232, 168, 0.15)"
        elif self.state == StatePillState.DEGRADED:
            text_color = COLOR_DISTURBANCE_AMBER
            bg_color = "rgba(232, 161, 92, 0.15)"
        elif self.state == StatePillState.LOST:
            text_color = COLOR_LOST_RED
            bg_color = "rgba(232, 111, 127, 0.15)"

        self.setText(f" {text} ")
        self.setStyleSheet(
            f"""
            QLabel {{
                background-color: {bg_color};
                color: {text_color};
                font-family: 'General Sans', -apple-system, sans-serif;
                font-size: {TYPE_SCALE_MICRO}px;
                font-weight: 700;
                border-radius: 3px;
                padding: {SPACING_4}px {SPACING_8}px;
                letter-spacing: 0.5px;
            }}
            """
        )
