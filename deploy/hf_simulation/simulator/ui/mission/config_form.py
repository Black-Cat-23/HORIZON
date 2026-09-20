"""HORIZON Phase 11.3 Scenario Configuration Form Component
============================================================
Center panel for scenario parameter customization.
Grouped into collapsible sections using ExpandableDiagnosticContainer.
Provides plain-language validation feedback — never auto-corrects silently.
"""

from __future__ import annotations
from typing import Optional, Tuple
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from simulator.ui.foundation.tokens import (
    COLOR_FIELD,
    COLOR_HAIRLINE_BORDER_HEX,
    COLOR_LOCK_CYAN,
    COLOR_LOST_RED,
    COLOR_TEXT_PRIMARY,
    COLOR_TEXT_SECONDARY,
    FONT_BODY,
    SPACING_8,
    SPACING_12,
    SPACING_16,
)
from simulator.ui.foundation.primitives import (
    ExpandableDiagnosticContainer,
    PanelSurface,
    PanelVariant,
    SectionHeaderLabel,
)
from simulator.core.config import AppConfig, SimulationConfig, TrajectoryConfig, TargetConfig
from simulator.disturbances.presets import get_preset_config
from simulator.ui.mission.scenario_data import ScenarioDefinition


class ScenarioConfigFormWidget(QWidget):
    """Scenario Parameter Configuration Form with Validation."""

    config_changed = Signal(object)      # Emits updated resolved AppConfig
    validation_failed = Signal(str)     # Emits error message

    TRAJECTORY_TYPES = ["figure8", "straight", "circular", "random", "sinusoidal", "spiral"]
    DETECTOR_MODES = ["HYBRID", "CLASSICAL", "NEURAL"]
    DISTURBANCE_PRESETS = ["NOMINAL", "DIFFICULT", "SEVERE", "RECOVERY", "ADVERSARIAL"]

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._current_config: Optional[AppConfig] = None
        self._validation_error: Optional[str] = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(SPACING_8)

        # Header Title: "Scenario configuration" (sentence case)
        header = SectionHeaderLabel("Scenario configuration", self)
        header.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY}; font-family: {FONT_BODY}; font-size: 14px; font-weight: 600;")
        layout.addWidget(header)

        # Validation Banner Frame
        self.banner_frame = QFrame(self)
        self.banner_frame.setVisible(False)
        self.banner_frame.setStyleSheet(
            f"background-color: rgba(232, 111, 127, 0.15); border: 1px solid {COLOR_LOST_RED}; border-radius: 4px; padding: 8px;"
        )
        banner_layout = QHBoxLayout(self.banner_frame)
        banner_layout.setContentsMargins(SPACING_12, SPACING_8, SPACING_12, SPACING_8)
        self.lbl_error = QLabel(self.banner_frame)
        self.lbl_error.setStyleSheet(f"color: {COLOR_LOST_RED}; font-family: {FONT_BODY}; font-size: 12px; font-weight: 600;")
        banner_layout.addWidget(self.lbl_error)
        layout.addWidget(self.banner_frame)

        # Scrollable form layout
        scroll_area = QScrollArea(self)
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        scroll_area.setStyleSheet("background: transparent;")
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        scroll_content = QWidget(scroll_area)
        scroll_content.setStyleSheet("background: transparent;")
        form_main_layout = QVBoxLayout(scroll_content)
        form_main_layout.setContentsMargins(0, 0, SPACING_8, 0)
        form_main_layout.setSpacing(SPACING_12)

        # ----------------------------------------------------------------------
        # 1. Target Parameters Section
        # ----------------------------------------------------------------------
        cont_target = ExpandableDiagnosticContainer("Target parameters", parent=scroll_content)
        cont_target.set_expanded(True)
        layout_t = QFormLayout(cont_target.content_widget)

        self.combo_traj = QComboBox(cont_target.content_widget)
        self.combo_traj.addItems(self.TRAJECTORY_TYPES)
        self.combo_traj.currentTextChanged.connect(self._on_field_changed)
        layout_t.addRow("Trajectory Pattern:", self.combo_traj)

        self.spin_beacon_dim = QDoubleSpinBox(cont_target.content_widget)
        self.spin_beacon_dim.setRange(2.0, 50.0)
        self.spin_beacon_dim.setValue(10.0)
        self.spin_beacon_dim.setSuffix(" px")
        self.spin_beacon_dim.valueChanged.connect(self._on_field_changed)
        layout_t.addRow("Beacon Diameter:", self.spin_beacon_dim)

        form_main_layout.addWidget(cont_target)

        # ----------------------------------------------------------------------
        # 2. Camera Parameters Section
        # ----------------------------------------------------------------------
        cont_cam = ExpandableDiagnosticContainer("Camera parameters", parent=scroll_content)
        cont_cam.set_expanded(True)
        layout_c = QFormLayout(cont_cam.content_widget)

        self.spin_fps = QSpinBox(cont_cam.content_widget)
        self.spin_fps.setRange(10, 120)
        self.spin_fps.setValue(30)
        self.spin_fps.setSuffix(" Hz")
        self.spin_fps.valueChanged.connect(self._on_field_changed)
        layout_c.addRow("Sampling Rate:", self.spin_fps)

        form_main_layout.addWidget(cont_cam)

        # ----------------------------------------------------------------------
        # 3. Perception Parameters Section
        # ----------------------------------------------------------------------
        cont_percep = ExpandableDiagnosticContainer("Perception parameters", parent=scroll_content)
        cont_percep.set_expanded(True)
        layout_p = QFormLayout(cont_percep.content_widget)

        self.combo_detector = QComboBox(cont_percep.content_widget)
        self.combo_detector.addItems(self.DETECTOR_MODES)
        self.combo_detector.currentTextChanged.connect(self._on_field_changed)
        layout_p.addRow("Detector Pipeline:", self.combo_detector)

        form_main_layout.addWidget(cont_percep)

        # ----------------------------------------------------------------------
        # 4. Disturbance Parameters Section
        # ----------------------------------------------------------------------
        cont_dist = ExpandableDiagnosticContainer("Disturbance parameters", parent=scroll_content)
        cont_dist.set_expanded(True)
        layout_d = QFormLayout(cont_dist.content_widget)

        self.combo_dist_preset = QComboBox(cont_dist.content_widget)
        self.combo_dist_preset.addItems(self.DISTURBANCE_PRESETS)
        self.combo_dist_preset.currentTextChanged.connect(self._on_field_changed)
        layout_d.addRow("Preset Profile:", self.combo_dist_preset)

        form_main_layout.addWidget(cont_dist)

        # ----------------------------------------------------------------------
        # 5. Advanced Parameters Container (Hidden / Collapsed by default)
        # ----------------------------------------------------------------------
        cont_adv = ExpandableDiagnosticContainer("Advanced configuration", parent=scroll_content)
        cont_adv.set_expanded(False)  # Collapsed by default as per Section 5
        layout_a = QFormLayout(cont_adv.content_widget)

        self.spin_duration = QDoubleSpinBox(cont_adv.content_widget)
        self.spin_duration.setRange(1.0, 300.0)
        self.spin_duration.setValue(30.0)
        self.spin_duration.setSuffix(" s")
        self.spin_duration.valueChanged.connect(self._on_field_changed)
        layout_a.addRow("Simulation Duration:", self.spin_duration)

        self.spin_seed = QSpinBox(cont_adv.content_widget)
        self.spin_seed.setRange(0, 999999)
        self.spin_seed.setValue(42)
        self.spin_seed.valueChanged.connect(self._on_field_changed)
        layout_a.addRow("Random Seed:", self.spin_seed)

        form_main_layout.addWidget(cont_adv)

        form_main_layout.addStretch()
        scroll_area.setWidget(scroll_content)
        layout.addWidget(scroll_area, stretch=1)

    def load_scenario(self, scenario: ScenarioDefinition) -> None:
        """Populate configuration fields from a selected ScenarioDefinition."""
        cfg = scenario.config
        self.combo_traj.setCurrentText(cfg.trajectory.type)
        self.spin_beacon_dim.setValue(float(cfg.target.size_px))
        self.spin_fps.setValue(int(cfg.simulation.frequency_hz))
        self.spin_duration.setValue(cfg.simulation.duration_seconds)
        self.spin_seed.setValue(cfg.simulation.seed)

        # Disturbance preset string
        if not cfg.disturbance.enabled:
            self.combo_dist_preset.setCurrentText("NOMINAL")
        elif cfg.disturbance.atmosphere.condition == "haze":
            self.combo_dist_preset.setCurrentText("DIFFICULT")
        elif cfg.disturbance.atmosphere.condition == "fog":
            self.combo_dist_preset.setCurrentText("SEVERE")
        elif cfg.disturbance.atmosphere.condition == "low_light":
            self.combo_dist_preset.setCurrentText("REACQUIRE")
        elif cfg.disturbance.atmosphere.condition == "rain":
            self.combo_dist_preset.setCurrentText("ADVERSARIAL")
        else:
            self.combo_dist_preset.setCurrentText("NOMINAL")

        self._validate_and_emit()

    def _on_field_changed(self) -> None:
        self._validate_and_emit()

    def _validate_and_emit(self) -> None:
        """Validate parameter inputs cleanly; show exact error banner if invalid."""
        dur = self.spin_duration.value()
        fps = self.spin_fps.value()
        b_dim = self.spin_beacon_dim.value()

        if dur <= 0.0:
            self._show_error("Validation Error: Simulation duration must be > 0 seconds")
            return
        if fps <= 0:
            self._show_error("Validation Error: Sampling rate must be > 0 Hz")
            return
        if b_dim <= 0.0:
            self._show_error("Validation Error: Beacon diameter must be > 0 px")
            return

        # Clear error banner
        self.banner_frame.setVisible(False)
        self._validation_error = None

        # Build resolved AppConfig
        dist_cfg = get_preset_config(self.combo_dist_preset.currentText())
        traj_cfg = TrajectoryConfig(type=self.combo_traj.currentText())

        resolved_config = AppConfig(
            trajectory=traj_cfg,
            disturbance=dist_cfg,
            simulation=SimulationConfig(
                frequency_hz=float(fps),
                duration_seconds=dur,
                seed=self.spin_seed.value(),
            ),
            target=TargetConfig(size_px=int(b_dim), intensity=255),
        )
        self._current_config = resolved_config
        self.config_changed.emit(resolved_config)

    def _show_error(self, message: str) -> None:
        self._validation_error = message
        self.lbl_error.setText(message)
        self.banner_frame.setVisible(True)
        self.validation_failed.emit(message)
