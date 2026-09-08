"""HORIZON Phase 11.6 Report Links Component
=============================================
Provides real direct links to saved validation reports, experiment data, raw results, and Phase 10 verification documents.
No placeholder links allowed!
"""

from __future__ import annotations
import os
from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from simulator.ui.foundation.tokens import (
    COLOR_FIELD,
    COLOR_FIELD_RAISED,
    COLOR_HAIRLINE_BORDER_HEX,
    COLOR_LOCK_CYAN,
    COLOR_TEXT_PRIMARY,
    COLOR_TEXT_SECONDARY,
    FONT_BODY,
    SPACING_8,
    SPACING_12,
    SPACING_16,
)
from simulator.ui.foundation.primitives import PanelSurface, PanelVariant, SectionHeaderLabel, PrimaryButton


class ReportLinksWidget(PanelSurface):
    """Report Links & Validation Artifact Access Component Widget."""

    REPORTS = [
        ("HTML Validation Report", "COARSE_ALIGN_X_VALIDATION_REPORT.html", "Formal interactive HTML validation report"),
        ("Engineering Markdown Report", "AUTOMATED_ENGINEERING_REPORT.md", "Automated statistical engineering report"),
        ("Raw Benchmark JSON Results", "results/comparisons/comparison.json", "Exact Phase 10 aggregate metrics JSON"),
        ("Phase 10 Verification Report", "PHASE10_VERIFICATION_REPORT.md", "19-criterion V&V verification audit report"),
    ]

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(PanelVariant.FIELD, parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(SPACING_16, SPACING_12, SPACING_16, SPACING_12)
        layout.setSpacing(SPACING_12)

        # Header Title: "Verification reports & raw data artifacts"
        header = SectionHeaderLabel("Verification reports & raw data artifacts", self)
        layout.addWidget(header)

        links_layout = QHBoxLayout()
        links_layout.setSpacing(SPACING_12)

        for title, rel_path, desc in self.REPORTS:
            abs_path = Path(rel_path).resolve()
            exists = abs_path.exists()

            card = PanelSurface(PanelVariant.FIELD_RAISED, self)
            c_layout = QVBoxLayout(card)
            c_layout.setContentsMargins(SPACING_12, SPACING_12, SPACING_12, SPACING_12)
            c_layout.setSpacing(SPACING_8)

            lbl_t = QLabel(title, card)
            lbl_t.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY}; font-family: {FONT_BODY}; font-size: 12px; font-weight: 600;")
            c_layout.addWidget(lbl_t)

            lbl_d = QLabel(desc, card)
            lbl_d.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-family: {FONT_BODY}; font-size: 11px;")
            c_layout.addWidget(lbl_d)

            btn = PrimaryButton("Open document", parent=card)
            btn.setEnabled(exists)
            btn.clicked.connect(lambda checked=False, p=abs_path: self._open_file(p))
            c_layout.addWidget(btn)

            links_layout.addWidget(card, stretch=1)

        layout.addLayout(links_layout)

    def _open_file(self, path: Path) -> None:
        """Open file using OS default handler or desktop service."""
        if path.exists():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))
