"""HORIZON Phase 11.6 Benchmark Screen View Component
=====================================================
Scientific Results Workstation (Mode 4).
Statistical-rigor differentiator with honest distribution-level benchmarking.

Integrates:
  1. Baseline Comparison Table (B0 / B1 / B2 / Ours, monospace tabular figures, full distributions)
  2. Same-Seed Trial Inspector (Side-by-side comparison under exact same seed)
  3. Distribution Visuals (CDFs & Box plots for tracking error, acquisition, reacquisition, latency)
  4. Robustness Heatmap Matrix (Explicit MEASURED vs INTERPOLATED cell distinction)
  5. Failure Intelligence & Event Timeline Drill-Down (8 taxonomy categories)
  6. Architecture Ablation Study (Classical, Neural, Basic fusion, Fusion + optical, Full hybrid)
  7. Verification Reports & Data Artifact Links (Direct links to real Phase 10 files)
"""

from __future__ import annotations
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from simulator.ui.foundation.tokens import SPACING_12
from simulator.ui.foundation.primitives import SectionHeaderLabel

# Benchmark Subcomponents
from simulator.ui.benchmark.comparison_table import BaselineComparisonTableWidget
from simulator.ui.benchmark.same_seed_inspector import SameSeedInspectorWidget
from simulator.ui.benchmark.distribution_plots import DistributionVisualsWidget
from simulator.ui.benchmark.robustness_heatmap import RobustnessHeatmapWidget
from simulator.ui.benchmark.failure_intelligence import FailureIntelligenceWidget
from simulator.ui.benchmark.ablation_panel import AblationComparisonWidget
from simulator.ui.benchmark.report_links import ReportLinksWidget


class BenchmarkScreenView(QWidget):
    """Scientific Results Workstation Screen (Mode 4)."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(SPACING_12, SPACING_12, SPACING_12, SPACING_12)
        main_layout.setSpacing(SPACING_12)

        # Title Header: "Scientific benchmarking & statistical validation workstation"
        header = SectionHeaderLabel("Scientific benchmarking & statistical validation workstation", self)
        main_layout.addWidget(header)

        # Scrollable Area for Dense Results Workstation
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background: transparent;")

        scroll_content = QWidget(scroll)
        scroll_content.setStyleSheet("background: transparent;")
        content_layout = QVBoxLayout(scroll_content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(SPACING_12)

        # 1. Baseline Comparison Table
        self.comparison_table = BaselineComparisonTableWidget(scroll_content)
        content_layout.addWidget(self.comparison_table)

        # 2. Same-Seed Trial Inspector
        self.same_seed_inspector = SameSeedInspectorWidget(scroll_content)
        content_layout.addWidget(self.same_seed_inspector)

        # 3. Distribution Visuals (CDFs & Box plots)
        self.distribution_visuals = DistributionVisualsWidget(scroll_content)
        content_layout.addWidget(self.distribution_visuals)

        # 4. Robustness Heatmap Envelopes
        self.robustness_heatmap = RobustnessHeatmapWidget(scroll_content)
        content_layout.addWidget(self.robustness_heatmap)

        # 5. Failure Intelligence & Event Timeline
        self.failure_intelligence = FailureIntelligenceWidget(scroll_content)
        content_layout.addWidget(self.failure_intelligence)

        # 6. Architecture Ablation Study
        self.ablation_comparison = AblationComparisonWidget(scroll_content)
        content_layout.addWidget(self.ablation_comparison)

        # 7. Verification Report Links
        self.report_links = ReportLinksWidget(scroll_content)
        content_layout.addWidget(self.report_links)

        scroll.setWidget(scroll_content)
        main_layout.addWidget(scroll, stretch=1)
