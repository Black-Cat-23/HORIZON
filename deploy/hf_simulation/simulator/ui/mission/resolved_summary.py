"""HORIZON Phase 11.3 Resolved Configuration Summary Component
===================================================================
Technical summary rendering static resolved configuration values.
IMPORTANT: Uses body typeface (General Sans) in text-primary — NOT monospace,
since these are static resolved configuration parameters, not live-updating telemetry.
"""

from __future__ import annotations
from typing import Optional
from PySide6.QtWidgets import QFormLayout, QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from simulator.ui.foundation.tokens import (
    COLOR_FIELD,
    COLOR_HAIRLINE_BORDER_HEX,
    COLOR_LOCK_CYAN,
    COLOR_TEXT_PRIMARY,
    COLOR_TEXT_SECONDARY,
    FONT_BODY,
    SPACING_8,
    SPACING_12,
    SPACING_16,
)
from simulator.ui.foundation.primitives import PanelSurface, PanelVariant, SectionHeaderLabel
from simulator.core.config import AppConfig
from simulator.ui.mission.scenario_data import ScenarioDefinition


class ResolvedConfigSummaryWidget(PanelSurface):
    """Static Resolved Configuration Technical Summary Box."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(PanelVariant.FIELD, parent)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(SPACING_16, SPACING_16, SPACING_16, SPACING_16)
        main_layout.setSpacing(SPACING_12)

        # Header Title: "Resolved configuration" (sentence case)
        header = SectionHeaderLabel("Resolved configuration", self)
        header.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY}; font-family: {FONT_BODY}; font-size: 13px; font-weight: 600;")
        main_layout.addWidget(header)

        # Static Technical Summary Table (General Sans body typeface, text-primary)
        form_layout = QFormLayout()
        form_layout.setHorizontalSpacing(SPACING_16)
        form_layout.setVerticalSpacing(SPACING_8)

        self.lbl_exp_id = self._create_value_label("EXP_NOMINAL_01")
        self.lbl_scenario = self._create_value_label("Nominal acquisition")
        self.lbl_target = self._create_value_label("10px, Figure-8")
        self.lbl_camera = self._create_value_label("640x480, 4x3 deg, 5 deg/s max")
        self.lbl_perception = self._create_value_label("Hybrid (Classical + Neural)")
        self.lbl_estimation = self._create_value_label("Kalman Filter (PV)")
        self.lbl_control = self._create_value_label("PAT Controller (PID + FF)")
        self.lbl_disturbance = self._create_value_label("Nominal")
        self.lbl_seed = self._create_value_label("42")
        self.lbl_duration = self._create_value_label("30.0s")

        form_layout.addRow(self._create_field_label("Experiment:"), self.lbl_exp_id)
        form_layout.addRow(self._create_field_label("Scenario:"), self.lbl_scenario)
        form_layout.addRow(self._create_field_label("Target:"), self.lbl_target)
        form_layout.addRow(self._create_field_label("Camera:"), self.lbl_camera)
        form_layout.addRow(self._create_field_label("Perception:"), self.lbl_perception)
        form_layout.addRow(self._create_field_label("Estimation:"), self.lbl_estimation)
        form_layout.addRow(self._create_field_label("Control:"), self.lbl_control)
        form_layout.addRow(self._create_field_label("Disturbance:"), self.lbl_disturbance)
        form_layout.addRow(self._create_field_label("Seed:"), self.lbl_seed)
        form_layout.addRow(self._create_field_label("Duration:"), self.lbl_duration)

        main_layout.addLayout(form_layout)

    def _create_field_label(self, text: str) -> QLabel:
        lbl = QLabel(text, self)
        lbl.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-family: {FONT_BODY}; font-size: 12px; font-weight: 500;")
        return lbl

    def _create_value_label(self, text: str) -> QLabel:
        lbl = QLabel(text, self)
        # General Sans body font in text-primary (strictly NO monospace!)
        lbl.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY}; font-family: {FONT_BODY}; font-size: 12px; font-weight: 600;")
        return lbl

    def update_summary(self, scenario: ScenarioDefinition, config: AppConfig) -> None:
        """Update static summary readouts from real resolved configuration."""
        self.lbl_exp_id.setText(f"EXP_{scenario.scenario_id.upper()[:12]}")
        self.lbl_scenario.setText(scenario.name)
        self.lbl_target.setText(f"{config.target.size_px}px, {config.trajectory.type.capitalize()}")
        self.lbl_camera.setText(f"640x480, 4x3 deg, {int(config.simulation.frequency_hz)} Hz")
        self.lbl_perception.setText("Hybrid (Classical + Neural)")
        self.lbl_estimation.setText("Kalman Filter (PV)")
        self.lbl_control.setText("PAT Controller (PID + FF)")

        dist_str = "Nominal"
        if config.disturbance.enabled:
            dist_str = config.disturbance.atmosphere.condition.capitalize() or "Custom"
        self.lbl_disturbance.setText(dist_str)

        self.lbl_seed.setText(str(config.simulation.seed))
        self.lbl_duration.setText(f"{config.simulation.duration_seconds:.1f}s")
