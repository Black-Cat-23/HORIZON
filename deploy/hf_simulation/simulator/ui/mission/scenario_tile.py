"""HORIZON Phase 11.3 Scenario Tile Component
=============================================
Individual scenario tile primitive for the Scenario Gallery.
Displays:
  - Miniature trajectory preview generated mathematically FROM actual scenario path.
  - Scenario name (sentence case).
  - One-line objective in plain language.
  - Difficulty tag pill.
  - Real parameter summary.
"""

from __future__ import annotations
from typing import Optional, List, Tuple
import cv2
import numpy as np

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from simulator.ui.foundation.tokens import (
    COLOR_FIELD,
    COLOR_FIELD_RAISED,
    COLOR_HAIRLINE_BORDER_HEX,
    COLOR_LOCK_CYAN,
    COLOR_TEXT_PRIMARY,
    COLOR_TEXT_SECONDARY,
    COLOR_VOID,
    FONT_BODY,
    SPACING_8,
    SPACING_12,
    SPACING_16,
    TYPE_SCALE_BODY,
    TYPE_SCALE_MICRO,
)
from simulator.ui.foundation.primitives import StateIndicatorPill, StatePillState
from simulator.ui.mission.scenario_data import ScenarioDefinition


class ScenarioThumbnailCanvas(QLabel):
    """Miniature 90x60 trajectory preview canvas."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedSize(90, 60)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet(f"background-color: {COLOR_VOID}; border: 1px solid {COLOR_HAIRLINE_BORDER_HEX}; border-radius: 4px;")

    def render_preview(self, path_points: List[Tuple[float, float]], world_size: float = 2000.0) -> None:
        if not path_points:
            return

        canvas = np.zeros((60, 90, 3), dtype=np.uint8)

        # Scale path points to 90x60 canvas
        scale_x = 90.0 / world_size
        scale_y = 60.0 / world_size

        pixel_pts: List[Tuple[int, int]] = []
        for x, y in path_points:
            px = int(round(x * scale_x))
            py = int(round(y * scale_y))
            # Clamp inside canvas
            px = max(2, min(87, px))
            py = max(2, min(57, py))
            pixel_pts.append((px, py))

        if len(pixel_pts) > 1:
            pts_arr = np.array(pixel_pts, dtype=np.int32).reshape((-1, 1, 2))
            cv2.polylines(canvas, [pts_arr], isClosed=False, color=(232, 212, 127), thickness=1, lineType=cv2.LINE_AA)

        # Draw start position dot
        if pixel_pts:
            cv2.circle(canvas, pixel_pts[0], 2, (0, 165, 255), -1, cv2.LINE_AA)

        qimg = QImage(canvas.data, 90, 60, 90 * 3, QImage.Format.Format_RGB888)
        self.setPixmap(QPixmap.fromImage(qimg))


class ScenarioTileWidget(QFrame):
    """Scenario selection tile primitive."""

    clicked = Signal(str)  # Emits scenario_id

    def __init__(self, scenario: ScenarioDefinition, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.scenario = scenario
        self.is_selected = False

        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(SPACING_12, SPACING_12, SPACING_12, SPACING_12)
        main_layout.setSpacing(SPACING_12)

        # 1. Thumbnail Trajectory Canvas
        self.thumb_canvas = ScenarioThumbnailCanvas(self)
        self.thumb_canvas.render_preview(scenario.generate_preview_path())
        main_layout.addWidget(self.thumb_canvas)

        # 2. Information Stack
        info_stack = QVBoxLayout()
        info_stack.setSpacing(4)

        # Name + Difficulty Pill Bar
        title_bar = QHBoxLayout()
        title_bar.setSpacing(SPACING_8)

        self.lbl_name = QLabel(scenario.name, self)
        self.lbl_name.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY}; font-family: {FONT_BODY}; font-size: 14px; font-weight: 700;")
        title_bar.addWidget(self.lbl_name)

        diff_state = StatePillState.IDLE if scenario.difficulty == "Nominal" else (
            StatePillState.CONFIRMED if scenario.difficulty == "Moderate" else (
                StatePillState.DEGRADED if scenario.difficulty == "Severe" else StatePillState.LOST
            )
        )
        self.pill_diff = StateIndicatorPill(diff_state, label_text=scenario.difficulty.upper(), parent=self)
        title_bar.addWidget(self.pill_diff)
        title_bar.addStretch()

        info_stack.addLayout(title_bar)

        # One-line Objective
        self.lbl_obj = QLabel(scenario.objective, self)
        self.lbl_obj.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-family: {FONT_BODY}; font-size: 12px;")
        self.lbl_obj.setWordWrap(True)
        info_stack.addWidget(self.lbl_obj)

        # Parameter Summary
        self.lbl_summary = QLabel(scenario.param_summary, self)
        self.lbl_summary.setStyleSheet(f"color: {COLOR_LOCK_CYAN}; font-family: {FONT_BODY}; font-size: 11px; font-weight: 500;")
        info_stack.addWidget(self.lbl_summary)

        main_layout.addLayout(info_stack, stretch=1)

        self.set_selected(False)

    def set_selected(self, selected: bool) -> None:
        self.is_selected = selected
        if selected:
            self.setStyleSheet(
                f"""
                QFrame {{
                    background-color: {COLOR_FIELD_RAISED};
                    border: 1px solid {COLOR_LOCK_CYAN};
                    border-radius: 6px;
                }}
                """
            )
        else:
            self.setStyleSheet(
                f"""
                QFrame {{
                    background-color: {COLOR_FIELD};
                    border: 1px solid {COLOR_HAIRLINE_BORDER_HEX};
                    border-radius: 6px;
                }}
                QFrame:hover {{
                    border: 1px solid rgba(255, 255, 255, 0.2);
                    background-color: rgba(255, 255, 255, 0.02);
                }}
                """
            )

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.scenario.scenario_id)
        super().mousePressEvent(event)
