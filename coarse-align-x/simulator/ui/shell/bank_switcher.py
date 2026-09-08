"""
HORIZON 5-Mode Bank Switcher Component
=======================================
Multi-bank test instrument switcher (Mission, Live, Track, Stress, Benchmark).
Active mode: lock-cyan (#7FD4E8) + field-raised (#202024) background.
Inactive modes: text-secondary (#8E8E96) + transparent background.
"""

from __future__ import annotations
from typing import Callable, List
from PySide6.QtCore import Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QPushButton, QWidget
from simulator.ui.foundation.tokens import (
    COLOR_FIELD,
    COLOR_FIELD_RAISED,
    COLOR_HAIRLINE_BORDER_HEX,
    COLOR_LOCK_CYAN,
    COLOR_TEXT_SECONDARY,
    SPACING_4,
    SPACING_8,
    SPACING_12,
    SPACING_16,
    TYPE_SCALE_BODY,
)


class ModeButton(QPushButton):
    """Individual bank switcher button primitive."""

    def __init__(self, mode_index: int, icon_str: str, label_str: str, parent: QWidget | None = None) -> None:
        super().__init__(f"{icon_str}  {label_str}", parent)
        self.mode_index = mode_index
        self.set_active(False)

    def set_active(self, active: bool) -> None:
        if active:
            self.setStyleSheet(
                f"""
                QPushButton {{
                    background-color: {COLOR_FIELD_RAISED};
                    color: {COLOR_LOCK_CYAN};
                    border: 1px solid {COLOR_LOCK_CYAN};
                    border-radius: 4px;
                    padding: {SPACING_8}px {SPACING_16}px;
                    font-family: 'General Sans', sans-serif;
                    font-size: {TYPE_SCALE_BODY}px;
                    font-weight: 700;
                }}
                """
            )
        else:
            self.setStyleSheet(
                f"""
                QPushButton {{
                    background-color: transparent;
                    color: {COLOR_TEXT_SECONDARY};
                    border: 1px solid transparent;
                    border-radius: 4px;
                    padding: {SPACING_8}px {SPACING_16}px;
                    font-family: 'General Sans', sans-serif;
                    font-size: {TYPE_SCALE_BODY}px;
                    font-weight: 500;
                }}
                QPushButton:hover {{
                    color: #F2F2F4;
                    background-color: rgba(255, 255, 255, 0.03);
                }}
                """
            )


class ModeSelectorBank(QFrame):
    """5-Mode Instrument Bank Switcher Bar."""

    mode_changed = Signal(int)  # Emits 0-indexed selected mode index

    MODES = [
        ("🎯", "Mission"),
        ("📡", "Live"),
        ("📈", "Track"),
        ("⚡", "Stress"),
        ("📊", "Benchmark"),
    ]

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.current_index = 0

        self.setStyleSheet(
            f"""
            QFrame {{
                background-color: {COLOR_FIELD};
                border-bottom: 1px solid {COLOR_HAIRLINE_BORDER_HEX};
            }}
            """
        )

        layout = QHBoxLayout(self)
        layout.setContentsMargins(SPACING_16, SPACING_4, SPACING_16, SPACING_4)
        layout.setSpacing(SPACING_8)

        self.buttons: List[ModeButton] = []
        for idx, (icon, label) in enumerate(self.MODES):
            btn = ModeButton(idx, icon, label, self)
            btn.clicked.connect(lambda _, i=idx: self.select_mode(i))
            layout.addWidget(btn)
            self.buttons.append(btn)

        layout.addStretch()
        self.select_mode(0)

    def select_mode(self, index: int) -> None:
        if index < 0 or index >= len(self.MODES):
            return
        self.current_index = index
        for idx, btn in enumerate(self.buttons):
            btn.set_active(idx == index)
        self.mode_changed.emit(index)
