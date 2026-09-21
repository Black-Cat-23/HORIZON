"""HORIZON Phase 11.3 Mission Screen View Component
===================================================
Composite main view for Mode 0 ("Mission Control").
Integrates:
  - LEFT (~1/3 width): Scenario Gallery (13 scenario tiles mapped directly to real backend configs)
  - CENTER: Scenario Configuration Form (Collapsible grouped parameter form with live validation)
  - RIGHT: Resolved Configuration Technical Summary (Body font, text-primary) + Static Map Preview + "Launch experiment" Primary Action

Emits launch_requested(AppConfig) signal when valid experiment launch is triggered.
"""

from __future__ import annotations
from typing import Optional
from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QMessageBox,
    QVBoxLayout,
    QWidget,
)

from simulator.ui.foundation.tokens import (
    COLOR_LOCK_CYAN,
    COLOR_TEXT_PRIMARY,
    FONT_BODY,
    SPACING_12,
    SPACING_16,
)
from simulator.ui.foundation.primitives import PrimaryButton
from simulator.core.config import AppConfig
from simulator.ui.mission.config_form import ScenarioConfigFormWidget
from simulator.ui.mission.experiment_preview import ExperimentPreviewWidget
from simulator.ui.mission.resolved_summary import ResolvedConfigSummaryWidget
from simulator.ui.mission.scenario_data import ScenarioDefinition
from simulator.ui.mission.scenario_gallery import ScenarioGalleryWidget


class MissionScreenView(QWidget):
    """Phase 11.3 Mission Control & Scenario Definition Screen."""

    launch_requested = Signal(object)  # Emits resolved AppConfig instance

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self._active_scenario: Optional[ScenarioDefinition] = None
        self._resolved_config: Optional[AppConfig] = None
        self._is_config_valid = True

        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(12)

        # 1. LEFT COLUMN (~1/3 width): Scenario Gallery
        self.gallery = ScenarioGalleryWidget(self)
        self.gallery.scenario_selected.connect(self._on_scenario_selected)
        main_layout.addWidget(self.gallery, stretch=3)

        # 2. CENTER COLUMN: Scenario Parameter Configuration Form
        self.config_form = ScenarioConfigFormWidget(self)
        self.config_form.config_changed.connect(self._on_config_changed)
        self.config_form.validation_failed.connect(self._on_validation_failed)
        main_layout.addWidget(self.config_form, stretch=3)

        # 3. RIGHT COLUMN: Resolved Summary + Map Preview + Launch Action
        right_column = QVBoxLayout()
        right_column.setSpacing(12)

        # Resolved Configuration Technical Summary Box
        self.summary_box = ResolvedConfigSummaryWidget(self)
        right_column.addWidget(self.summary_box)

        # Static Experiment Map Preview Box
        self.preview_box = ExperimentPreviewWidget(self)
        right_column.addWidget(self.preview_box, stretch=1)

        # Launch Primary Action Button: "Launch experiment" (sentence case per patched button rules)
        self.btn_launch = PrimaryButton("Launch experiment", parent=self)
        self.btn_launch.setStyleSheet(
            f"""
            QPushButton {{
                background-color: {COLOR_LOCK_CYAN};
                color: #0A0A0B;
                font-family: {FONT_BODY};
                font-size: 15px;
                font-weight: 700;
                border-radius: 4px;
                padding: 12px 24px;
            }}
            QPushButton:hover {{
                background-color: #A3E4F2;
            }}
            """
        )
        self.btn_launch.clicked.connect(self._on_launch_clicked)
        right_column.addWidget(self.btn_launch)

        main_layout.addLayout(right_column, stretch=3)

    def _on_scenario_selected(self, scenario: ScenarioDefinition) -> None:
        self._active_scenario = scenario
        self.config_form.load_scenario(scenario)

    def _on_config_changed(self, resolved_config: AppConfig) -> None:
        self._resolved_config = resolved_config
        self._is_config_valid = True

        if self._active_scenario:
            self.summary_box.update_summary(self._active_scenario, resolved_config)
            self.preview_box.update_preview(self._active_scenario, resolved_config)

    def _on_validation_failed(self, error_message: str) -> None:
        self._is_config_valid = False

    def _on_launch_clicked(self) -> None:
        """Validate and launch experiment, transitioning to Live tracking screen."""
        if not self._is_config_valid or self._resolved_config is None:
            QMessageBox.warning(
                self,
                "Invalid Mission Configuration",
                "Cannot launch experiment: Configuration contains invalid parameters.\n\n"
                "Please fix the parameters highlighted in the configuration section.",
            )
            return

        # Emit launch_requested signal with resolved AppConfig
        self.launch_requested.emit(self._resolved_config)
