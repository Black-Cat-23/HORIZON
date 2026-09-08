"""
Section Header Label Component Primitive (Patched Title Case Scoping)
====================================================================
Structural header for grouped content (Title Case / Sentence Case, 12px, text-secondary).
"""

from __future__ import annotations
from PySide6.QtWidgets import QLabel, QWidget
from simulator.ui.foundation.tokens import (
    COLOR_TEXT_SECONDARY,
    TYPE_SCALE_MICRO,
)


class SectionHeaderLabel(QLabel):
    """Structural section header primitive in Title Case / Sentence Case."""

    def __init__(self, text: str = "", parent: QWidget | None = None) -> None:
        super().__init__(text.title() if text else "", parent)
        self.setStyleSheet(
            f"""
            QLabel {{
                color: {COLOR_TEXT_SECONDARY};
                font-family: 'General Sans', -apple-system, sans-serif;
                font-size: {TYPE_SCALE_MICRO}px;
                font-weight: 600;
            }}
            """
        )

    def setText(self, text: str) -> None:
        super().setText(text.title() if text else "")
