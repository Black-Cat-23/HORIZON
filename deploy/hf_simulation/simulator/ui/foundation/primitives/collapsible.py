"""
Expandable Diagnostic Container Component Primitive
===================================================
Collapsible container for Diagnostic-tier content (collapsed by default).
"""

from __future__ import annotations
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget
from simulator.ui.foundation.tokens import (
    COLOR_FIELD,
    COLOR_HAIRLINE_BORDER_HEX,
    COLOR_TEXT_PRIMARY,
    COLOR_TEXT_SECONDARY,
    SPACING_4,
    SPACING_8,
    SPACING_12,
    TYPE_SCALE_BODY,
)


class ExpandableDiagnosticContainer(QFrame):
    """Collapsible diagnostic panel container, collapsed by default."""

    def __init__(self, title: str = "Diagnostic Telemetry", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.is_expanded = False

        self.setStyleSheet(
            f"""
            QFrame {{
                background-color: {COLOR_FIELD};
                border: 1px solid {COLOR_HAIRLINE_BORDER_HEX};
                border-radius: 4px;
            }}
            """
        )

        self._root_layout = QVBoxLayout(self)
        self._root_layout.setContentsMargins(SPACING_8, SPACING_8, SPACING_8, SPACING_8)
        self._root_layout.setSpacing(SPACING_8)

        # Header Toggle Bar
        self._header_button = QPushButton(f"▶ {title}", self)
        self._header_button.setStyleSheet(
            f"""
            QPushButton {{
                background-color: transparent;
                color: {COLOR_TEXT_SECONDARY};
                border: none;
                text-align: left;
                font-size: {TYPE_SCALE_BODY}px;
                font-weight: 600;
                padding: {SPACING_4}px;
            }}
            QPushButton:hover {{
                color: {COLOR_TEXT_PRIMARY};
            }}
            """
        )
        self._header_button.clicked.connect(self.toggle)
        self._root_layout.addWidget(self._header_button)

        # Content Area
        self.content_widget = QWidget(self)
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(SPACING_8, SPACING_8, SPACING_8, SPACING_8)
        self.content_layout.setSpacing(SPACING_8)
        self.content_widget.setVisible(False)
        self._root_layout.addWidget(self.content_widget)

    def toggle(self) -> None:
        self.is_expanded = not self.is_expanded
        self.content_widget.setVisible(self.is_expanded)
        icon = "▼" if self.is_expanded else "▶"
        clean_text = self._header_button.text().lstrip("▶▼ ")
        self._header_button.setText(f"{icon} {clean_text}")

    def set_expanded(self, expanded: bool) -> None:
        if self.is_expanded != expanded:
            self.toggle()
