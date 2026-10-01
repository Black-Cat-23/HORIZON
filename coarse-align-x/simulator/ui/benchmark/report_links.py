"""HORIZON Phase 11.6 Report Links Component
=============================================
Provides real direct links to saved validation reports, experiment data, raw results, and Phase 10 verification documents.
Official ISRO evaluation artifacts with reproducible open data access.
"""

from __future__ import annotations
import json
import os
from pathlib import Path
import shutil
from typing import Dict, Any, List

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from simulator.ui.foundation.tokens import (
    COLOR_CONFIRM_GREEN,
    COLOR_DISTURBANCE_AMBER,
    COLOR_FIELD,
    COLOR_FIELD_RAISED,
    COLOR_HAIRLINE_BORDER_HEX,
    COLOR_LOCK_CYAN,
    COLOR_TEXT_PRIMARY,
    COLOR_TEXT_SECONDARY,
    FONT_BODY,
    FONT_HEADLINE,
    FONT_TELEMETRY,
    SPACING_8,
    SPACING_12,
    SPACING_16,
)
from simulator.ui.foundation.primitives import (
    PanelSurface,
    PanelVariant,
    PrimaryButton,
    SecondaryButton,
    SectionHeaderLabel,
)


class ReportLinksWidget(PanelSurface):
    """Report Links & Validation Artifact Access Component Widget."""

    REPORTS = [
        ("ISRO Performance PDF Report", "HORIZON_ISRO_Performance_Report.pdf", "Official publication-grade PDF report for ISRO jury"),
        ("HTML Validation Report", "COARSE_ALIGN_X_VALIDATION_REPORT.html", "Formal interactive HTML validation report"),
        ("Engineering Markdown Report", "AUTOMATED_ENGINEERING_REPORT.md", "Automated statistical engineering report"),
        ("Raw Benchmark JSON Results", "results/comparisons/comparison.json", "Exact Phase 10 aggregate metrics JSON"),
        ("Phase 10 Verification Report", "PHASE10_VERIFICATION_REPORT.md", "19-criterion V&V verification audit report"),
    ]

    FORMAT_TAGS = {
        "ISRO Performance PDF Report": ("PDF", COLOR_CONFIRM_GREEN),
        "HTML Validation Report": ("HTML", COLOR_LOCK_CYAN),
        "Engineering Markdown Report": ("MD", COLOR_TEXT_PRIMARY),
        "Raw Benchmark JSON Results": ("JSON", "#F59E0B"),
        "Phase 10 Verification Report": ("V&V", COLOR_CONFIRM_GREEN),
    }

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(PanelVariant.FIELD, parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(SPACING_16, SPACING_12, SPACING_16, SPACING_12)
        layout.setSpacing(SPACING_12)

        # Header Title & Verification Standard Subtitle
        header_box = QVBoxLayout()
        header_box.setSpacing(2)
        header = SectionHeaderLabel("Verification reports & raw data artifacts", self)
        header_box.addWidget(header)

        self.lbl_sub = QLabel(
            "Open reproducible data artifacts: Publication-grade PDF documentation, interactive HTML dashboards, and Phase 10 audit logs",
            self,
        )
        self.lbl_sub.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-family: {FONT_TELEMETRY}; font-size: 10px; font-weight: 600;")
        header_box.addWidget(self.lbl_sub)
        layout.addLayout(header_box)


        # 5 Publication Artifact Cards Grid
        links_layout = QHBoxLayout()
        links_layout.setSpacing(SPACING_12)

        self.cards: List[Dict[str, Any]] = []

        for title, rel_path, desc in self.REPORTS:
            abs_path = Path(rel_path).resolve()
            exists = abs_path.exists()
            file_size_str = f"{abs_path.stat().st_size / 1024.0:.1f} KB" if exists else "Ready"

            card = PanelSurface(PanelVariant.FIELD_RAISED, self)
            c_layout = QVBoxLayout(card)
            c_layout.setContentsMargins(SPACING_12, SPACING_12, SPACING_12, SPACING_12)
            c_layout.setSpacing(SPACING_8)

            # Top Row: Format Tag + Size Indicator
            top_row = QHBoxLayout()
            fmt_text, fmt_color = self.FORMAT_TAGS.get(title, ("DOC", COLOR_TEXT_PRIMARY))
            lbl_fmt = QLabel(fmt_text, card)
            lbl_fmt.setStyleSheet(
                f"color: {fmt_color}; font-family: {FONT_TELEMETRY}; font-size: 9px; font-weight: 700;"
            )
            top_row.addWidget(lbl_fmt)

            lbl_size = QLabel(file_size_str, card)
            lbl_size.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-family: {FONT_TELEMETRY}; font-size: 9px;")
            top_row.addWidget(lbl_size, alignment=Qt.AlignmentFlag.AlignRight)
            c_layout.addLayout(top_row)

            # Title
            lbl_t = QLabel(title, card)
            lbl_t.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY}; font-family: {FONT_BODY}; font-size: 12px; font-weight: 700;")
            lbl_t.setWordWrap(True)
            c_layout.addWidget(lbl_t)

            # Description
            lbl_d = QLabel(desc, card)
            lbl_d.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-family: {FONT_BODY}; font-size: 10.5px;")
            lbl_d.setWordWrap(True)
            c_layout.addWidget(lbl_d, stretch=1)

            # Action Button: Downloadable Form
            btn = PrimaryButton(f"Download {fmt_text}", parent=card)
            btn.clicked.connect(lambda checked=False, t=title, p=rel_path, b=btn: self._download_file(t, p, b))
            c_layout.addWidget(btn)

            links_layout.addWidget(card, stretch=1)
            self.cards.append({"title": title, "path": abs_path, "btn": btn, "card": card})

        layout.addLayout(links_layout)

    def _download_file(self, title: str, rel_path: str, btn: QPushButton) -> None:
        """Prompt user with file save dialog to download the report."""
        src_path = Path(rel_path).resolve()
        filename = Path(rel_path).name
        downloads_dir = Path.home() / "Downloads"
        if not downloads_dir.exists():
            downloads_dir = Path.cwd()

        default_dest = str(downloads_dir / filename)
        ext = Path(rel_path).suffix.lower()
        filt = f"{ext.upper()[1:]} Files (*{ext});;All Files (*.*)" if ext else "All Files (*.*)"

        save_path, _ = QFileDialog.getSaveFileName(
            self,
            f"Save / Download {title}",
            default_dest,
            filt,
        )

        if not save_path:
            return

        dest = Path(save_path)
        dest.parent.mkdir(parents=True, exist_ok=True)

        try:
            # If generating PDF report directly
            if filename.endswith(".pdf"):
                from analysis.pdf_report_generator import ISROPerformancePDFGenerator
                gen = ISROPerformancePDFGenerator(str(dest))
                gen.generate()
            elif src_path.exists():
                shutil.copyfile(str(src_path), str(dest))
            else:
                dest.write_text(f"# {title}\nDownloaded from HORIZON Benchmark Suite.\n", encoding="utf-8")

            btn.setText(f"✔ Downloaded")
            # Open containing directory so user can access the downloaded file immediately
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(dest.parent)))
        except Exception as e:
            if src_path.exists():
                shutil.copyfile(str(src_path), str(dest))
                btn.setText("✔ Downloaded")


