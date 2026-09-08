"""Unit tests for Phase 11.3 Mission Control Screen (Scenario Gallery, Config Form, Resolved Summary, Preview).
"""

import pytest
from PySide6.QtWidgets import QApplication

from simulator.ui.mission import MissionScreenView
from simulator.ui.mission.scenario_data import get_default_scenarios, ScenarioDefinition
from simulator.ui.mission.scenario_gallery import ScenarioGalleryWidget
from simulator.ui.mission.config_form import ScenarioConfigFormWidget
from simulator.ui.mission.resolved_summary import ResolvedConfigSummaryWidget
from simulator.ui.mission.experiment_preview import ExperimentPreviewWidget
from simulator.core.config import AppConfig


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


def test_scenario_data_definitions():
    """Verify all 13 required scenario definitions are populated."""
    scenarios = get_default_scenarios()
    assert len(scenarios) == 13

    expected_ids = {
        "nominal_acq", "straight", "circular", "figure8", "random",
        "low_light", "fog_haze", "jitter", "platform_motion", "multi_distractor",
        "recovery", "severe_combined", "custom"
    }
    loaded_ids = {s.scenario_id for s in scenarios}
    assert expected_ids == loaded_ids


def test_scenario_trajectory_preview_math():
    """Verify preview trajectory points are generated mathematically from configuration."""
    scenarios = get_default_scenarios()
    for scen in scenarios:
        pts = scen.generate_preview_path(num_points=50)
        assert len(pts) == 50
        assert isinstance(pts[0][0], float)
        assert isinstance(pts[0][1], float)


def test_scenario_gallery_widget(qapp):
    """Verify ScenarioGalleryWidget loads tiles and handles selection."""
    gallery = ScenarioGalleryWidget()
    assert len(gallery.tile_widgets) == 13

    selected = []
    gallery.scenario_selected.connect(lambda s: selected.append(s))

    gallery.select_scenario("figure8")
    assert len(selected) == 1
    assert selected[0].scenario_id == "figure8"
    assert gallery.tile_widgets["figure8"].is_selected


def test_config_form_validation(qapp):
    """Verify ScenarioConfigFormWidget validates parameters and displays error banner."""
    form = ScenarioConfigFormWidget()
    scenarios = get_default_scenarios()
    form.load_scenario(scenarios[0])

    assert form._validation_error is None
    assert not form.banner_frame.isVisible()

    # Set invalid duration <= 0
    form.spin_duration.setMinimum(-10.0)
    form.spin_duration.setValue(-5.0)
    assert form._validation_error is not None
    assert "duration" in form.lbl_error.text().lower()

    # Restore valid duration
    form.spin_duration.setValue(30.0)
    assert form._validation_error is None


def test_resolved_config_summary_body_font(qapp):
    """Verify ResolvedConfigSummaryWidget uses body font (General Sans) in text-primary (NO monospace)."""
    summary = ResolvedConfigSummaryWidget()
    scenarios = get_default_scenarios()
    summary.update_summary(scenarios[0], scenarios[0].config)

    assert "General Sans" in summary.lbl_scenario.styleSheet()
    assert "JetBrains Mono" not in summary.lbl_scenario.styleSheet()
    assert summary.lbl_scenario.text() == "Nominal acquisition"


def test_experiment_preview_widget(qapp):
    """Verify ExperimentPreviewWidget renders static preview map."""
    preview = ExperimentPreviewWidget()
    scenarios = get_default_scenarios()
    preview.update_preview(scenarios[0], scenarios[0].config)
    assert preview.canvas_label.pixmap() is not None


def test_mission_screen_view_launch(qapp):
    """Verify MissionScreenView composite widget emits launch_requested signal."""
    screen = MissionScreenView()
    scenarios = get_default_scenarios()
    screen._on_scenario_selected(scenarios[0])
    screen._on_config_changed(scenarios[0].config)
    launched_configs = []
    screen.launch_requested.connect(lambda cfg: launched_configs.append(cfg))

    # Trigger launch
    screen._on_launch_clicked()
    assert len(launched_configs) == 1
    assert isinstance(launched_configs[0], AppConfig)
