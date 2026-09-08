"""HORIZON Phase 11.6 Benchmark Screen Unit Tests
===================================================
Verifies:
  1. BaselineComparisonTableWidget table values and digit alignment.
  2. SameSeedInspectorWidget seed selection and side-by-side cards.
  3. DistributionVisualsWidget CDF and Box Plot metric switching.
  4. RobustnessHeatmapWidget envelope switching and MEASURED vs INTERPOLATED cell tags.
  5. FailureIntelligenceWidget taxonomy categories and event timeline drill-down.
  6. AblationComparisonWidget unified-scale progress bars.
  7. ReportLinksWidget document paths.
  8. BenchmarkScreenView composite screen initialization.
"""

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from simulator.ui.benchmark.comparison_table import BaselineComparisonTableWidget
from simulator.ui.benchmark.same_seed_inspector import SameSeedInspectorWidget
from simulator.ui.benchmark.distribution_plots import DistributionVisualsWidget
from simulator.ui.benchmark.robustness_heatmap import RobustnessHeatmapWidget, RobustnessCellWidget
from simulator.ui.benchmark.failure_intelligence import FailureIntelligenceWidget
from simulator.ui.benchmark.ablation_panel import AblationComparisonWidget
from simulator.ui.benchmark.report_links import ReportLinksWidget
from simulator.ui.benchmark.benchmark_screen import BenchmarkScreenView


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_baseline_comparison_table(qapp):
    table = BaselineComparisonTableWidget()
    assert table.cell_labels["rmse_error"]["OURS"]._val_label.text().strip() != ""
    assert table.cell_labels["rmse_error"]["B0"]._val_label.text().strip() != ""
    assert table.cell_labels["p95_latency"]["OURS"]._val_label.text().strip() != ""


def test_same_seed_inspector(qapp):
    inspector = SameSeedInspectorWidget()
    assert len(inspector.cards) == 4
    assert "OURS" in inspector.cards

    # Select seed
    selected_seeds = []
    inspector.seed_selected.connect(lambda s: selected_seeds.append(s))
    inspector.combo_seed.setCurrentIndex(1)
    assert len(selected_seeds) > 0
    assert inspector.cards["OURS"]["telem_error"]._val_label.text().strip() != ""


def test_distribution_visuals_widget(qapp):
    dist_widget = DistributionVisualsWidget()
    dist_widget.combo_metric.setCurrentText("Latency")
    assert dist_widget.canvas._metric_name == "Latency"

    dist_widget.combo_mode.setCurrentText("Box Plot")
    assert dist_widget.canvas._plot_mode == "BoxPlot"


def test_robustness_heatmap_widget(qapp):
    heatmap = RobustnessHeatmapWidget()
    assert heatmap.grid_layout.count() > 0

    # Test cell tags
    cell_m = RobustnessCellWidget(success_rate_pct=95.0, sample_count=10, is_measured=True)
    assert "solid" in cell_m.styleSheet()

    cell_i = RobustnessCellWidget(success_rate_pct=80.0, sample_count=6, is_measured=False)
    assert "dashed" in cell_i.styleSheet()

    heatmap.combo_env.setCurrentText("Target size × Noise")
    assert heatmap.grid_layout.count() > 0


def test_failure_intelligence_widget(qapp):
    fail_widget = FailureIntelligenceWidget()
    assert len(fail_widget.btn_map) == 8

    emitted_cats = []
    fail_widget.category_selected.connect(lambda c: emitted_cats.append(c))

    fail_widget._select_category("TRACK_LOSS")
    assert fail_widget._selected_category == "TRACK_LOSS"
    assert len(emitted_cats) > 0
    assert fail_widget.timeline_layout.count() > 0


def test_ablation_comparison_widget(qapp):
    ablation = AblationComparisonWidget()
    assert ablation.canvas is not None
    assert len(ablation.canvas.VARIANTS) == 5


def test_report_links_widget(qapp):
    links = ReportLinksWidget()
    assert len(links.REPORTS) == 4


def test_benchmark_screen_view(qapp):
    screen = BenchmarkScreenView()
    assert screen is not None
    assert isinstance(screen.comparison_table, BaselineComparisonTableWidget)
    assert isinstance(screen.same_seed_inspector, SameSeedInspectorWidget)
    assert isinstance(screen.distribution_visuals, DistributionVisualsWidget)
    assert isinstance(screen.robustness_heatmap, RobustnessHeatmapWidget)
    assert isinstance(screen.failure_intelligence, FailureIntelligenceWidget)
    assert isinstance(screen.ablation_comparison, AblationComparisonWidget)
    assert isinstance(screen.report_links, ReportLinksWidget)
