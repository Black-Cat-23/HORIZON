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
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QScrollArea,
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

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(12, 10, 12, 10)
        root_layout.setSpacing(10)

        # ----------------------------------------------------------------------
        # Top Institutional Header Strip
        # ----------------------------------------------------------------------
        top_banner = QHBoxLayout()
        top_banner.setContentsMargins(0, 0, 0, 0)
        top_banner.setSpacing(8)

        lbl_screen_title = QLabel("PRE-FLIGHT CONOPS BRIEFING & PAT EXPERIMENT DEFINITION WORKSTATION", self)
        lbl_screen_title.setStyleSheet(
            f"color: {COLOR_TEXT_PRIMARY}; font-family: {FONT_BODY}; font-size: 12.5px; font-weight: 700; letter-spacing: 0.6px;"
        )
        top_banner.addWidget(lbl_screen_title)

        top_banner.addStretch()

        lbl_std = QLabel("CCSDS 141.0-B-1 FLIGHT READINESS REVIEW (FRR)  |  HORIZON-PAT", self)
        lbl_std.setStyleSheet("color: #8A94A0; font-family: 'Consolas', monospace; font-size: 10.5px; font-weight: 600;")
        top_banner.addWidget(lbl_std)

        root_layout.addLayout(top_banner)

        # ----------------------------------------------------------------------
        # 3-Column Main Content Layout
        # ----------------------------------------------------------------------
        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(12)

        # 1. LEFT COLUMN (~30% width): Scenario Gallery
        self.gallery = ScenarioGalleryWidget(self)
        self.gallery.scenario_selected.connect(self._on_scenario_selected)
        main_layout.addWidget(self.gallery, stretch=3)

        # 2. CENTER COLUMN (~35% width): Scenario Parameter Configuration Form
        self.config_form = ScenarioConfigFormWidget(self)
        self.config_form.config_changed.connect(self._on_config_changed)
        self.config_form.validation_failed.connect(self._on_validation_failed)
        main_layout.addWidget(self.config_form, stretch=3)

        # 3. RIGHT COLUMN (~35% width): Scrollable container for Summary + Preview + Persistent Launch Button
        right_column = QVBoxLayout()
        right_column.setSpacing(10)

        right_scroll = QScrollArea(self)
        right_scroll.setWidgetResizable(True)
        right_scroll.setFrameShape(QFrame.Shape.NoFrame)
        right_scroll.setStyleSheet("background: transparent;")
        right_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        right_content = QWidget(right_scroll)
        right_content_layout = QVBoxLayout(right_content)
        right_content_layout.setContentsMargins(0, 0, 4, 18)
        right_content_layout.setSpacing(12)

        # Resolved Configuration Technical Summary Box
        self.summary_box = ResolvedConfigSummaryWidget(right_content)
        right_content_layout.addWidget(self.summary_box)

        # Scientific Pre-Flight Corridor Visualizer
        self.preview_box = ExperimentPreviewWidget(right_content)
        right_content_layout.addWidget(self.preview_box)

        right_content_layout.addStretch()
        right_scroll.setWidget(right_content)
        right_column.addWidget(right_scroll, stretch=1)

        # Launch Action Button: Aerospace Authorization Console (Docked at bottom of right column)
        self.btn_launch = PrimaryButton("AUTHORIZE FLIGHT RUN (CONOPS ENGAGE)", parent=self)
        self.btn_launch.setStyleSheet(
            """
            QPushButton {
                background-color: #1C334D;
                color: #79B8FF;
                border: 1px solid #388BFD;
                border-radius: 4px;
                font-family: 'General Sans', sans-serif;
                font-size: 13.5px;
                font-weight: 700;
                letter-spacing: 0.6px;
                padding: 11px 20px;
                min-height: 22px;
            }
            QPushButton:hover {
                background-color: #244264;
                color: #FFFFFF;
                border-color: #58A6FF;
            }
            """
        )
        self.btn_launch.clicked.connect(self._on_launch_clicked)
        right_column.addWidget(self.btn_launch)

        main_layout.addLayout(right_column, stretch=3)
        root_layout.addLayout(main_layout, stretch=1)

        # Auto-initialize with first scenario so preview & summary are NEVER blank
        if self.gallery.scenarios:
            self._on_scenario_selected(self.gallery.scenarios[0])

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
