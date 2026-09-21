"""HORIZON Phase 11.3 Experiment Preview Component
===================================================
Static (non-running) preview rendering mini 2000x2000 world map,
predicted target trajectory path, initial target position, and camera FOV footprint.
Purely static visualization generated from resolved AppConfig — does not execute simulation.
"""

from __future__ import annotations
from typing import Optional, List, Tuple
import cv2
import numpy as np

from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from simulator.ui.foundation.tokens import (
    COLOR_FIELD,
    COLOR_HAIRLINE_BORDER_HEX,
    COLOR_LOCK_CYAN,
    COLOR_TEXT_PRIMARY,
    COLOR_TEXT_SECONDARY,
    COLOR_VOID,
    FONT_BODY,
    SPACING_8,
    SPACING_12,
)
from simulator.ui.foundation.primitives import PanelSurface, PanelVariant, SectionHeaderLabel
from simulator.core.config import AppConfig
from simulator.ui.mission.scenario_data import ScenarioDefinition


class ExperimentPreviewWidget(PanelSurface):
    """Static Non-Executing Experiment Preview Display."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(PanelVariant.FIELD, parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(SPACING_12, SPACING_12, SPACING_12, SPACING_12)
        layout.setSpacing(SPACING_8)

        # Title: "Experiment preview" (sentence case)
        header = SectionHeaderLabel("Experiment preview (static map)", self)
        header.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY}; font-family: {FONT_BODY}; font-size: 13px; font-weight: 600;")
        layout.addWidget(header)

        self.canvas_label = QLabel(self)
        self.canvas_label.setMinimumSize(240, 200)
        self.canvas_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.canvas_label.setStyleSheet(
            f"background-color: {COLOR_VOID}; border: 1px solid {COLOR_HAIRLINE_BORDER_HEX}; border-radius: 4px;"
        )
        layout.addWidget(self.canvas_label, stretch=1)

        self._current_pixmap: Optional[QPixmap] = None

    def update_preview(self, scenario: ScenarioDefinition, config: AppConfig) -> None:
        """Render static 2000x2000 map preview from resolved AppConfig."""
        world_size = 2000.0
        canvas = np.zeros((2000, 2000, 3), dtype=np.uint8)

        # 1. Draw subtle background grid lines
        grid_step = 200
        for x in range(0, 2000, grid_step):
            cv2.line(canvas, (x, 0), (x, 2000), (30, 30, 35), 1)
        for y in range(0, 2000, grid_step):
            cv2.line(canvas, (0, y), (2000, y), (30, 30, 35), 1)

        # 2. Generate and draw predicted target trajectory path
        pts = scenario.generate_preview_path(num_points=120)
        if pts and len(pts) > 1:
            pixel_pts = np.array([(int(round(x)), int(round(y))) for x, y in pts], dtype=np.int32).reshape((-1, 1, 2))
            cv2.polylines(canvas, [pixel_pts], isClosed=False, color=(232, 212, 127), thickness=3, lineType=cv2.LINE_AA)

        # 3. Draw initial target position marker
        if pts:
            tx, ty = int(round(pts[0][0])), int(round(pts[0][1]))
            cv2.circle(canvas, (tx, ty), 12, (0, 165, 255), -1, cv2.LINE_AA)
            cv2.circle(canvas, (tx, ty), 20, (0, 165, 255), 2, cv2.LINE_AA)

        # 4. Draw camera boresight (1000, 1000) & initial FOV footprint rectangle (640x480)
        bx, by = 1000, 1000
        cv2.line(canvas, (bx - 25, by), (bx + 25, by), (232, 212, 127), 2)
        cv2.line(canvas, (bx, by - 25), (bx, by + 25), (232, 212, 127), 2)

        left, top = bx - 320, by - 240
        right, bottom = bx + 320, by + 240
        cv2.rectangle(canvas, (left, top), (right, bottom), (232, 212, 127), 3, cv2.LINE_AA)

        # Annotate text
        cv2.putText(canvas, f"PREVIEW: {scenario.name}", (40, 80), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (240, 240, 240), 2, cv2.LINE_AA)
        cv2.putText(canvas, f"Disturbance: {config.disturbance.atmosphere.condition.upper() if config.disturbance.enabled else 'NOMINAL'}", (40, 140), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (140, 140, 150), 2, cv2.LINE_AA)

        # Convert to QPixmap
        rgb_frame = cv2.cvtColor(canvas, cv2.COLOR_BGR2RGB)
        qimg = QImage(rgb_frame.data, 2000, 2000, 2000 * 3, QImage.Format.Format_RGB888)
        self._current_pixmap = QPixmap.fromImage(qimg)

        scaled = self._current_pixmap.scaled(
            self.canvas_label.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.canvas_label.setPixmap(scaled)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if self._current_pixmap is not None:
            scaled = self._current_pixmap.scaled(
                self.canvas_label.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            self.canvas_label.setPixmap(scaled)
