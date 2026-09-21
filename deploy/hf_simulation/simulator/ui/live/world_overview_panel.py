"""HORIZON Phase 11.2 World Overview Panel Component
===================================================
Secondary macro view displaying 2000x2000 simulation space.
Overlays (strictly bound to real-time telemetry):
  - Target trajectory (historical path)
  - Target position (world coordinate)
  - Camera reference position (boresight coordinate)
  - Camera FOV footprint polygon (640x480 subpixel window projected on 2000x2000 canvas)
  - Active search path footprint (when in SEARCH/REACQUIRE mode)
No decorative geometry, no starfields, no fake background art.
"""

from __future__ import annotations
from typing import List, Optional, Tuple
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
from simulator.ui.foundation.primitives import SectionHeaderLabel
from pat.state import PATMode, PATState


class WorldOverviewPanel(QWidget):
    """World Overview Display View (2000x2000 Macro Space)."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(SPACING_8)

        # Title Label: "World overview" (sentence case)
        header = SectionHeaderLabel("World overview (2000×2000)", self)
        header.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY}; font-family: {FONT_BODY}; font-size: 13px; font-weight: 600;")
        layout.addWidget(header)

        self.canvas_label = QLabel(self)
        self.canvas_label.setMinimumSize(260, 260)
        self.canvas_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.canvas_label.setStyleSheet(
            f"background-color: {COLOR_VOID}; border: 1px solid {COLOR_HAIRLINE_BORDER_HEX}; border-radius: 4px;"
        )
        layout.addWidget(self.canvas_label, stretch=1)

        self._current_pixmap: Optional[QPixmap] = None

    def update_world_display(
        self,
        world_frame: np.ndarray,
        target_pos: Optional[Tuple[float, float]],
        boresight_pos: Tuple[float, float],
        path_history: List[Tuple[float, float]],
        pat_state: PATState,
    ) -> None:
        """Render updated 2000x2000 macro view with live camera FOV footprint & target trajectory."""
        if world_frame is None or world_frame.size == 0:
            return

        # Create BGR canvas from 2000x2000 monochrome frame
        if world_frame.ndim == 2:
            canvas = cv2.cvtColor(world_frame, cv2.COLOR_GRAY2BGR)
        else:
            canvas = world_frame.copy()

        h_world, w_world = canvas.shape[:2]

        # 1. Draw Target Trajectory Path History (Thin Cyan line)
        if path_history and len(path_history) > 1:
            pts = np.array(path_history, dtype=np.int32).reshape((-1, 1, 2))
            cv2.polylines(canvas, [pts], isClosed=False, color=(200, 150, 0), thickness=2, lineType=cv2.LINE_AA)

        # 2. Draw Target Position Marker (Clean Amber Dot)
        if target_pos is not None:
            tx, ty = int(round(target_pos[0])), int(round(target_pos[1]))
            if 0 <= tx < w_world and 0 <= ty < h_world:
                cv2.circle(canvas, (tx, ty), 6, (0, 165, 255), -1, cv2.LINE_AA)
                cv2.circle(canvas, (tx, ty), 10, (0, 165, 255), 1, cv2.LINE_AA)

        # 3. Draw Camera Boresight Position (Bright Cyan Crosshair)
        bx, by = int(round(boresight_pos[0])), int(round(boresight_pos[1]))
        if 0 <= bx < w_world and 0 <= by < h_world:
            cv2.line(canvas, (bx - 15, by), (bx + 15, by), (232, 212, 127), 2)
            cv2.line(canvas, (bx, by - 15), (bx, by + 15), (232, 212, 127), 2)

        # 4. Draw Camera FOV Footprint Polygon (640x480 bounds around boresight)
        w_fov, h_fov = 640, 480
        left = int(round(bx - w_fov / 2.0))
        top = int(round(by - h_fov / 2.0))
        right = left + w_fov
        bottom = top + h_fov
        cv2.rectangle(canvas, (left, top), (right, bottom), (232, 212, 127), 2, cv2.LINE_AA)

        # 5. Draw Active Search Path Footprint if in SEARCH or REACQUIRE mode
        if pat_state and pat_state.mode in [PATMode.SEARCH, PATMode.REACQUIRE]:
            # Draw quiet search radius / spiral indicator around boresight
            search_r = int(min(w_world, h_world) * 0.15)
            cv2.circle(canvas, (bx, by), search_r, (100, 200, 255), 1, cv2.LINE_AA)
            cv2.putText(canvas, f"SEARCH: {pat_state.active_search_strategy}", (bx + 20, by - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (100, 200, 255), 2, cv2.LINE_AA)

        # Convert to QPixmap for rendering full 2000x2000 macro space
        rgb_frame = cv2.cvtColor(canvas, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_frame.shape
        qimg = QImage(rgb_frame.data, w, h, ch * w, QImage.Format.Format_RGB888)
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
