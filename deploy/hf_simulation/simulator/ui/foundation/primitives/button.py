"""
Button Component Primitives
===========================
PrimaryButton (solid compact neutral) and SecondaryButton (outline/text-only variant).
"""

from __future__ import annotations
from PySide6.QtWidgets import QPushButton, QWidget
from simulator.ui.foundation.tokens import (
    COLOR_FIELD_RAISED,
    COLOR_HAIRLINE_BORDER_HEX,
    COLOR_TEXT_PRIMARY,
    COLOR_TEXT_SECONDARY,
    SPACING_8,
    SPACING_16,
    TYPE_SCALE_BODY,
)


class PrimaryButton(QPushButton):
    """Solid compact neutral primary button."""

    def __init__(self, text: str = "", parent: QWidget | None = None) -> None:
        super().__init__(text, parent)
        self.setStyleSheet(
            f"""
            QPushButton {{
                background-color: {COLOR_FIELD_RAISED};
                color: {COLOR_TEXT_PRIMARY};
                border: 1px solid {COLOR_HAIRLINE_BORDER_HEX};
                border-radius: 4px;
                padding: {SPACING_8}px {SPACING_16}px;
                font-size: {TYPE_SCALE_BODY}px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: #242E52;
            }}
            QPushButton:pressed {{
                background-color: #171E36;
            }}
            """
        )


class SecondaryButton(QPushButton):
    """Quiet outline or text-only secondary button."""

    def __init__(self, text: str = "", parent: QWidget | None = None) -> None:
        super().__init__(text, parent)
        self.setStyleSheet(
            f"""
            QPushButton {{
                background-color: transparent;
                color: {COLOR_TEXT_SECONDARY};
                border: 1px solid {COLOR_HAIRLINE_BORDER_HEX};
                border-radius: 4px;
                padding: {SPACING_8}px {SPACING_16}px;
                font-size: {TYPE_SCALE_BODY}px;
            }}
            QPushButton:hover {{
                color: {COLOR_TEXT_PRIMARY};
                border-color: #404B70;
            }}
            QPushButton:pressed {{
                color: {COLOR_TEXT_SECONDARY};
            }}
            """
        )
