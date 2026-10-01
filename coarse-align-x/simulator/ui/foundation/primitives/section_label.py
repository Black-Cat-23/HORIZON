"""
Section Header Label Component Primitive (Patched Title Case Scoping)
====================================================================
Structural header for grouped content (Title Case / Sentence Case, 12px, text-secondary).
"""

from __future__ import annotations
from PySide6.QtWidgets import QLabel, QWidget
from simulator.ui.foundation.tokens import (
    COLOR_TEXT_PRIMARY,
    FONT_BODY,
    TYPE_SCALE_BODY,
)


class SectionHeaderLabel(QLabel):
    """Structural section header primitive in Title Case / Sentence Case."""

    def __init__(self, text: str = "", parent: QWidget | None = None) -> None:
        super().__init__(text.title() if text else "", parent)
        self.setStyleSheet(
            f"""
            QLabel {{
                color: {COLOR_TEXT_PRIMARY};
                font-family: 'Magnolia Script', cursive, sans-serif;
                font-size: 20px;
                font-weight: 700;
                letter-spacing: 0.5px;
            }}
            """
        )

    def setText(self, text: str) -> None:
        super().setText(text.title() if text else "")
