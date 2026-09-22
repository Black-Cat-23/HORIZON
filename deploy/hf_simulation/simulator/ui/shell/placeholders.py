"""
Mode Placeholder Views
======================
Calm, honest placeholders built from PanelSurface primitive.
Renders mode name in headline typeface and short body text in text-secondary.
"""

from __future__ import annotations
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget
from simulator.ui.foundation.tokens import (
    COLOR_TEXT_PRIMARY,
    COLOR_TEXT_SECONDARY,
    FONT_BODY,
    FONT_HEADLINE,
    SPACING_16,
    SPACING_24,
    TYPE_SCALE_TITLE,
)
from simulator.ui.foundation.primitives import PanelSurface, PanelVariant


class ModePlaceholderView(QWidget):
    """Honest placeholder view for Phase 11.1 App Shell."""

    PLACEHOLDER_INFO = {
        0: ("Mission Setup & Target Configuration", "Mission Screen — Phase 11.2"),
        1: ("Live Telemetry & PAT Closed-Loop Control", "Live Screen — Phase 11.3"),
        2: ("Track Performance & Estimation Diagnostics", "Track Screen — Phase 11.4"),
        3: ("Stress Laboratory & Disturbance Envelope", "Stress Screen — Phase 11.5"),
        4: ("Benchmark Battlefield & Baseline Evaluation", "Benchmark Screen — Phase 11.6"),
    }

    def __init__(self, mode_index: int = 0, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.mode_index = mode_index

        layout = QVBoxLayout(self)
        layout.setContentsMargins(SPACING_24, SPACING_24, SPACING_24, SPACING_24)

        surface = PanelSurface(PanelVariant.FIELD, self)
        s_layout = QVBoxLayout(surface)
        s_layout.setContentsMargins(SPACING_24, SPACING_24, SPACING_24, SPACING_24)
        s_layout.setSpacing(SPACING_16)

        title_text, subtitle_text = self.PLACEHOLDER_INFO.get(mode_index, ("Instrument Mode", "Phase 11 Placeholder"))

        lbl_title = QLabel(title_text, surface)
        lbl_title.setStyleSheet(
            f"color: {COLOR_TEXT_PRIMARY}; font-family: {FONT_HEADLINE}; font-size: {TYPE_SCALE_TITLE}px; font-weight: 700;"
        )
        s_layout.addWidget(lbl_title)

        lbl_sub = QLabel(subtitle_text, surface)
        lbl_sub.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-family: {FONT_BODY}; font-size: 14px;")
        s_layout.addWidget(lbl_sub)

        s_layout.addStretch()
        layout.addWidget(surface)
