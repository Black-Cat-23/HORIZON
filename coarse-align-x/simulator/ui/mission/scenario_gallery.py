"""HORIZON Phase 11.3 Scenario Gallery Component
=================================================
Scrolling scenario selection gallery (Left ~1/3 width of screen).
Renders the 13 scenario tiles mapped directly to real backend configurations.
"""

from __future__ import annotations
from typing import Dict, List
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QScrollArea, QVBoxLayout, QWidget

from simulator.ui.foundation.tokens import (
    COLOR_FIELD,
    COLOR_HAIRLINE_BORDER_HEX,
    COLOR_TEXT_PRIMARY,
    FONT_BODY,
    SPACING_8,
    SPACING_12,
    SPACING_16,
)
from simulator.ui.foundation.primitives import SectionHeaderLabel
from simulator.ui.mission.scenario_data import ScenarioDefinition, get_default_scenarios
from simulator.ui.mission.scenario_tile import ScenarioTileWidget


class ScenarioGalleryWidget(QWidget):
    """Scenario Gallery list container widget."""

    scenario_selected = Signal(object)  # Emits selected ScenarioDefinition

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.scenarios = get_default_scenarios()
        self.tile_widgets: Dict[str, ScenarioTileWidget] = {}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(SPACING_8)

        # Title Label: "Scenario gallery" (sentence case)
        header = SectionHeaderLabel("Scenario gallery", self)
        header.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY}; font-family: {FONT_BODY}; font-size: 14px; font-weight: 600;")
        layout.addWidget(header)

        # Scrollable list area
        scroll_area = QScrollArea(self)
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        scroll_area.setStyleSheet("background: transparent;")
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        scroll_content = QWidget(scroll_area)
        scroll_content.setStyleSheet("background: transparent;")
        self.list_layout = QVBoxLayout(scroll_content)
        self.list_layout.setContentsMargins(0, 0, SPACING_8, 0)
        self.list_layout.setSpacing(SPACING_8)

        for scenario in self.scenarios:
            tile = ScenarioTileWidget(scenario, scroll_content)
            tile.clicked.connect(self._on_tile_clicked)
            self.list_layout.addWidget(tile)
            self.tile_widgets[scenario.scenario_id] = tile

        self.list_layout.addStretch()
        scroll_area.setWidget(scroll_content)
        layout.addWidget(scroll_area, stretch=1)

        # Select first scenario ("nominal_acq") by default
        if self.scenarios:
            self.select_scenario(self.scenarios[0].scenario_id)

    def _on_tile_clicked(self, scenario_id: str) -> None:
        self.select_scenario(scenario_id)

    def select_scenario(self, scenario_id: str) -> None:
        selected_scen = None
        for sid, tile in self.tile_widgets.items():
            is_match = (sid == scenario_id)
            tile.set_selected(is_match)
            if is_match:
                selected_scen = tile.scenario

        if selected_scen:
            self.scenario_selected.emit(selected_scen)
