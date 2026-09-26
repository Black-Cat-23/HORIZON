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

    # ------------------------------------------------------------------
    # External Video Path — completely separate from update_world_display
    # The virtual camera path NEVER calls this method.
    # This method NEVER calls anything from the virtual world / gimbal.
    # Camera motion here is derived solely from the live IMM-EKF estimate.
    # ------------------------------------------------------------------
    def update_video_tracking_display(
        self,
        estimate,           # StateEstimate — provides estimated_x/y, predicted_x/y
        detection_res,      # DetectionResult — centroid and detected flag
        pat_state,          # PATState — mode for colour-coding
        path_history: List[Tuple[float, float]],   # rolling estimate trail (sensor px)
        frame_w: int = 640,
        frame_h: int = 480,
    ) -> None:
        """
        Render sensor-space (640×480) camera tracking overview for external video source.

        The 'camera boresight' indicator moves to the IMM-EKF estimated beacon position.
        This is algorithmically derived — the controller computes a pan/tilt command to
        keep the boresight centred on the estimate; this view shows where that boresight
        would be in sensor pixel space.

        Completely separate code path from update_world_display (virtual camera).
        No virtual world geometry, no SimulationEngine, no gimbal object accessed here.
        """
        # Build a dark sensor-space canvas (same size as the video frame)
        canvas = np.full((frame_h, frame_w, 3), (10, 14, 20), dtype=np.uint8)

        # ── 1. Sensor boundary ──────────────────────────────────────────
        cv2.rectangle(canvas, (0, 0), (frame_w - 1, frame_h - 1), (45, 55, 65), 1)

        # ── 2. Estimate trail (rolling history of IMM-EKF positions) ────
        if path_history and len(path_history) > 1:
            pts = np.array(path_history, dtype=np.int32).reshape((-1, 1, 2))
            cv2.polylines(canvas, [pts], isClosed=False,
                          color=(60, 140, 180), thickness=1, lineType=cv2.LINE_AA)

        # ── 3. Algorithm-computed boresight (IMM-EKF estimate) ──────────
        # The controller drives the gimbal to null (estimate_x - cx, estimate_y - cy).
        # In sensor space the boresight crosshair sits at the estimated centroid.
        if estimate is not None:
            bx = int(round(float(estimate.estimated_x)))
            by = int(round(float(estimate.estimated_y)))
            bx = int(np.clip(bx, 0, frame_w - 1))
            by = int(np.clip(by, 0, frame_h - 1))

            # Boresight crosshair (cyan / amber based on PAT mode)
            from pat.state import PATMode
            if pat_state is not None and pat_state.mode == PATMode.TRACK:
                cross_col = (127, 212, 232)   # cyan — locked
            elif pat_state is not None and pat_state.mode in (PATMode.DEGRADED,):
                cross_col = (92, 161, 232)    # amber — degraded
            elif pat_state is not None and pat_state.mode in (PATMode.REACQUIRE, PATMode.SEARCH):
                cross_col = (80, 80, 220)     # red-blue — searching
            else:
                cross_col = (180, 180, 180)   # neutral

            cv2.line(canvas, (bx - 18, by), (bx + 18, by), cross_col, 1, cv2.LINE_AA)
            cv2.line(canvas, (bx, by - 18), (bx, by + 18), cross_col, 1, cv2.LINE_AA)
            cv2.circle(canvas, (bx, by), 6, cross_col, 1, cv2.LINE_AA)

            # Predicted position (one step ahead — where the filter expects it next)
            if hasattr(estimate, "predicted_x") and estimate.predicted_x is not None:
                px = int(np.clip(round(float(estimate.predicted_x)), 0, frame_w - 1))
                py = int(np.clip(round(float(estimate.predicted_y)), 0, frame_h - 1))
                cv2.drawMarker(canvas, (px, py), (60, 60, 160),
                               markerType=cv2.MARKER_CROSS, markerSize=10, thickness=1)

            # Uncertainty ellipse (1-sigma, derived from position_uncertainty scalar)
            if hasattr(estimate, "position_uncertainty") and estimate.position_uncertainty > 0:
                r = int(np.clip(round(float(estimate.position_uncertainty)), 2, 80))
                cv2.ellipse(canvas, (bx, by), (r, r), 0, 0, 360,
                            (40, 80, 100), 1, cv2.LINE_AA)

        # ── 4. Raw measurement dot (where HYBRID actually saw the beacon) ─
        if detection_res is not None and detection_res.detected and detection_res.centroid:
            mu = int(np.clip(round(detection_res.centroid[0]), 0, frame_w - 1))
            mv = int(np.clip(round(detection_res.centroid[1]), 0, frame_h - 1))
            cv2.circle(canvas, (mu, mv), 4, (111, 232, 168), -1, cv2.LINE_AA)
            cv2.circle(canvas, (mu, mv), 7, (111, 232, 168), 1, cv2.LINE_AA)

        # ── 5. Overlay: mode badge ───────────────────────────────────────
        if pat_state is not None:
            mode_text = pat_state.mode.value
        else:
            mode_text = "SEARCH"
        cv2.putText(canvas, f"SENSOR VIEW  |  PAT: {mode_text}",
                    (8, 16), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (120, 130, 145), 1, cv2.LINE_AA)
        cv2.putText(canvas, f"{frame_w}x{frame_h} px",
                    (frame_w - 72, 16), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (80, 90, 100), 1, cv2.LINE_AA)

        # ── 6. Render to QLabel ──────────────────────────────────────────
        rgb = cv2.cvtColor(canvas, cv2.COLOR_BGR2RGB)
        qimg = QImage(rgb.data, frame_w, frame_h, frame_w * 3, QImage.Format.Format_RGB888)
        self._current_pixmap = QPixmap.fromImage(qimg)
        scaled = self._current_pixmap.scaled(
            self.canvas_label.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.canvas_label.setPixmap(scaled)

