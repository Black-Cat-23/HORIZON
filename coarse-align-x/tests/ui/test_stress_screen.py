"""HORIZON Phase 11.5 Stress Screen & Disturbance Controls Unit Tests
===================================================================
Verifies:
  1. DisturbanceControlsWidget presets, user adjustments, and DisturbanceConfig generation.
  2. SystemResponsePanelWidget real telemetry and response readouts.
  3. StressScreenView component integration, HeroSensorView reuse, and "Run stress test" action.
  4. Real backend disturbance pipeline application on control change (zero UI faking/interpolation).
"""

import pytest
import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from simulator.ui.stress.disturbance_controls import DisturbanceControlsWidget
from simulator.ui.stress.system_response_panel import SystemResponsePanelWidget
from simulator.ui.stress.stress_screen import StressScreenView
from simulator.ui.live.hero_sensor_view import HeroSensorView
from simulator.disturbances.config import DisturbanceConfig
from simulator.disturbances.pipeline import DisturbanceTelemetry
from pat.state import PATMode, PATState


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_disturbance_controls_widget(qapp):
    widget = DisturbanceControlsWidget()
    assert widget.combo_preset.currentText() == "NOMINAL"

    emitted_configs = []
    widget.disturbance_changed.connect(lambda cfg: emitted_configs.append(cfg))

    # Select SEVERE preset
    widget.combo_preset.setCurrentText("SEVERE")
    assert len(emitted_configs) > 0
    severe_cfg = emitted_configs[-1]
    assert isinstance(severe_cfg, DisturbanceConfig)
    assert severe_cfg.enabled is True

    # Adjust Gaussian noise spinbox to a custom unique value -> Preset switches to CUSTOM
    current_val = widget.spin_gaussian.value()
    new_val = 19.5 if current_val != 19.5 else 18.5
    widget.spin_gaussian.setValue(new_val)
    assert widget.combo_preset.currentText() == "CUSTOM"
    custom_cfg = emitted_configs[-1]
    assert custom_cfg.gaussian.sigma == new_val


def test_system_response_panel_widget(qapp):
    panel = SystemResponsePanelWidget()
    telem = DisturbanceTelemetry(
        disturbance_enabled=True,
        salt_pepper_enabled=True,
        salt_pepper_probability=0.02,
        gaussian_enabled=True,
        gaussian_sigma=5.0,
        poisson_enabled=False,
        poisson_parameter=100.0,
        camera_jitter_enabled=True,
        camera_jitter_x=2.0,
        camera_jitter_y=1.0,
        platform_motion_enabled=True,
        platform_model="linear",
        platform_offset_x=3.0,
        platform_offset_y=4.0,
        platform_velocity_x=10.0,
        platform_velocity_y=5.0,
        atmosphere_enabled=True,
        atmosphere_condition="haze",
        contrast_factor=0.8,
        brightness_factor=1.0,
    )
    pat_state = PATState(mode=PATMode.TRACK, track_quality=0.92)

    panel.update_telemetry(dist_telem=telem, pat_state=pat_state, detection_res=None, fps=30.0)

    assert panel.telem_g_sig._val_label.text().strip() != ""
    assert panel.telem_sp_prob._val_label.text().strip() != ""
    assert panel.pill_pat_state.text().strip() == "LOCKED"
    assert panel.telem_quality._val_label.text().strip() != ""


def test_stress_screen_view(qapp):
    screen = StressScreenView()
    assert screen is not None

    # Verify HeroSensorView reuse
    assert isinstance(screen.hero_sensor_view, HeroSensorView)
    assert isinstance(screen.controls_widget, DisturbanceControlsWidget)
    assert isinstance(screen.response_panel, SystemResponsePanelWidget)

    # Test single simulation step
    screen._on_sim_step()

    # Test disturbance change updates backend pipeline directly
    new_cfg = DisturbanceConfig(enabled=True)
    screen._on_disturbance_changed(new_cfg)
    assert screen._engine._disturbance_pipeline._config == new_cfg

    # Test sentence case button "Run stress test" action execution
    emitted_run = []
    screen.controls_widget.run_test_requested.connect(lambda: emitted_run.append(True))
    screen.controls_widget.btn_run_test.click()
    assert len(emitted_run) == 1
