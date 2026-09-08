"""HORIZON Phase 11.4 Filter Geometry & Observation View
=========================================================
Primary large geometry view rendering 640x480 filter state observations.
Features:
  - Measured centroid (perception detector measurement)
  - Estimated centroid (Kalman filter state estimate)
  - Predicted centroid (Kalman filter state prediction)
  - Ground-truth evaluation marker — ONLY when Evaluation Mode toggle is ON
  - Covariance uncertainty ellipse (mathematically scaled to selected 1-sigma / 2-sigma / 3-sigma)
  - Tracking error vector ray
  - Image center reference mark (320, 240)
  - Ground-Truth Firewall: Evaluation mode toggle OFF by default, clearly labeled as offline reference only.
"""

from __future__ import annotations
from typing import Optional, Tuple
import cv2
import numpy as np

from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
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
    COLOR_VOID,
    FONT_BODY,
    FONT_TELEMETRY,
    SPACING_8,
    SPACING_12,
    SPACING_16,
)
from simulator.ui.foundation.primitives import (
    PanelSurface,
    PanelVariant,
    SectionHeaderLabel,
    StateIndicatorPill,
    StatePillState,
)
from tracking.estimation.covariance import compute_covariance_ellipse
from tracking.estimation.state import StateEstimate
from simulator.perception.detector import DetectionResult


class GeometryCanvasWidget(QLabel):
    """Canvas widget for rendering filter geometry overlays."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumSize(480, 360)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet(f"background-color: {COLOR_VOID}; border: 1px solid {COLOR_HAIRLINE_BORDER_HEX}; border-radius: 4px;")
        self._current_pixmap: Optional[QPixmap] = None

    def update_frame(self, frame_bgr: np.ndarray) -> None:
        if frame_bgr is None or frame_bgr.size == 0:
            return
        h, w, ch = frame_bgr.shape
        rgb_frame = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        qimg = QImage(rgb_frame.data, w, h, ch * w, QImage.Format.Format_RGB888)
        self._current_pixmap = QPixmap.fromImage(qimg)
        self._repaint_canvas()

    def _repaint_canvas(self) -> None:
        if self._current_pixmap is not None:
            scaled = self._current_pixmap.scaled(
                self.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            self.setPixmap(scaled)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._repaint_canvas()


class TrackGeometryView(QWidget):
    """Filter Geometry & State Observation Display View."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._sigma_level = 2.0  # 2-sigma (95.4%) default
        self._eval_mode_enabled = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(SPACING_12)

        # 1. Header Bar: Title + Ground-Truth Firewall Evaluation Toggle
        header_bar = QHBoxLayout()
        header_bar.setContentsMargins(0, 0, 0, 0)
        header_bar.setSpacing(SPACING_12)

        lbl_title = SectionHeaderLabel("Filter geometry & state observation", self)
        lbl_title.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY}; font-family: {FONT_BODY}; font-size: 15px; font-weight: 600;")
        header_bar.addWidget(lbl_title)

        header_bar.addStretch()

        # Ground-Truth Firewall Toggle (OFF by default, labeled offline reference only)
        self.chk_eval_mode = QCheckBox("Ground-truth evaluation reference [OFFLINE EVAL ONLY]", self)
        self.chk_eval_mode.setStyleSheet(
            f"color: {COLOR_TEXT_SECONDARY}; font-family: {FONT_BODY}; font-size: 12px; font-weight: 500;"
        )
        self.chk_eval_mode.stateChanged.connect(self._on_eval_mode_toggled)
        header_bar.addWidget(self.chk_eval_mode)

        layout.addLayout(header_bar)

        # 2. Main Canvas Area
        self.canvas = GeometryCanvasWidget(self)
        layout.addWidget(self.canvas, stretch=1)

    def set_sigma_level(self, sigma: float) -> None:
        """Update selected covariance ellipse confidence level (1.0, 2.0, 3.0)."""
        self._sigma_level = sigma

    def _on_eval_mode_toggled(self, state: int) -> None:
        self._eval_mode_enabled = (state == Qt.CheckState.Checked.value)
        if self._eval_mode_enabled:
            self.chk_eval_mode.setStyleSheet(
                f"color: {COLOR_LOCK_CYAN}; font-family: {FONT_BODY}; font-size: 12px; font-weight: 700;"
            )
        else:
            self.chk_eval_mode.setStyleSheet(
                f"color: {COLOR_TEXT_SECONDARY}; font-family: {FONT_BODY}; font-size: 12px; font-weight: 500;"
            )

    def render_geometry(
        self,
        sensor_frame: np.ndarray,
        detection_res: Optional[DetectionResult],
        estimate: Optional[StateEstimate],
        ground_truth_pos: Optional[Tuple[float, float]] = None,
    ) -> None:
        """Render filter state observation overlays with mathematical covariance ellipse accuracy."""
        if sensor_frame is None or sensor_frame.size == 0:
            return

        h, w = sensor_frame.shape[:2]
        canvas = cv2.cvtColor(sensor_frame, cv2.COLOR_GRAY2BGR) if sensor_frame.ndim == 2 else sensor_frame.copy()

        # 1. Image Center Reference Crosshair (320, 240)
        cx, cy = w // 2, h // 2
        cv2.line(canvas, (cx - 10, cy), (cx + 10, cy), (90, 90, 95), 1)
        cv2.line(canvas, (cx, cy - 10), (cx, cy + 10), (90, 90, 95), 1)

        # 2. Ground-Truth Marker — ONLY rendered when Evaluation Mode is active (Ground-truth firewall)
        if self._eval_mode_enabled and ground_truth_pos is not None:
            gt_x, gt_y = int(round(ground_truth_pos[0])), int(round(ground_truth_pos[1]))
            if 0 <= gt_x < w and 0 <= gt_y < h:
                # White circle + crosshair labeled GT EVAL
                cv2.circle(canvas, (gt_x, gt_y), 5, (255, 255, 255), 1, cv2.LINE_AA)
                cv2.line(canvas, (gt_x - 8, gt_y), (gt_x + 8, gt_y), (255, 255, 255), 1)
                cv2.line(canvas, (gt_x, gt_y - 8), (gt_x, gt_y + 8), (255, 255, 255), 1)
                cv2.putText(canvas, "GT [EVAL]", (gt_x + 8, gt_y - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (255, 255, 255), 1, cv2.LINE_AA)

        # 3. Measured Centroid Marker (Bright Red Reticle)
        meas_x, meas_y = None, None
        if detection_res and detection_res.detected and detection_res.centroid:
            meas_x, meas_y = int(round(detection_res.centroid[0])), int(round(detection_res.centroid[1]))
            if 0 <= meas_x < w and 0 <= meas_y < h:
                cv2.line(canvas, (meas_x - 7, meas_y), (meas_x + 7, meas_y), (0, 0, 240), 1)
                cv2.line(canvas, (meas_x, meas_y - 7), (meas_x, meas_y + 7), (0, 0, 240), 1)
                cv2.circle(canvas, (meas_x, meas_y), 2, (0, 0, 255), -1)
                cv2.putText(canvas, "MEAS", (meas_x + 8, meas_y - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 0, 255), 1, cv2.LINE_AA)

        # 4. Filter State Estimate & Covariance Ellipse
        if estimate is not None:
            est_x, est_y = int(round(estimate.estimated_x)), int(round(estimate.estimated_y))

            # Predicted Centroid Marker (Amber 'x' Marker)
            pred_x, pred_y = int(round(estimate.predicted_x)), int(round(estimate.predicted_y))
            if 0 <= pred_x < w and 0 <= pred_y < h:
                cv2.drawMarker(canvas, (pred_x, pred_y), (0, 215, 255), cv2.MARKER_TILTED_CROSS, 8, 1)
                cv2.putText(canvas, "PRED", (pred_x + 8, pred_y - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 215, 255), 1, cv2.LINE_AA)

            # Mathematically Accurate Covariance Ellipse (Thin Cyan)
            if estimate.covariance is not None:
                try:
                    conf_level = 0.683 if self._sigma_level == 1.0 else (0.954 if self._sigma_level == 2.0 else 0.997)
                    ellipse_data = compute_covariance_ellipse(
                        P=estimate.covariance,
                        center_x=estimate.estimated_x,
                        center_y=estimate.estimated_y,
                        confidence_level=conf_level,
                    )
                    c_pt = (int(round(ellipse_data.center_x)), int(round(ellipse_data.center_y)))
                    axes_pt = (
                        max(1, int(round(ellipse_data.semi_major_axis))),
                        max(1, int(round(ellipse_data.semi_minor_axis))),
                    )
                    ang = int(round(ellipse_data.orientation_deg))

                    if axes_pt[0] < 500 and axes_pt[1] < 500:
                        cv2.ellipse(
                            canvas,
                            center=c_pt,
                            axes=axes_pt,
                            angle=ang,
                            startAngle=0,
                            endAngle=360,
                            color=(232, 212, 127),
                            thickness=1,
                            lineType=cv2.LINE_AA,
                        )
                except Exception:
                    pass

            # Estimated Position Reticle (Bright Cyan)
            if 0 <= est_x < w and 0 <= est_y < h:
                cv2.circle(canvas, (est_x, est_y), 5, (232, 212, 127), 1, cv2.LINE_AA)
                cv2.line(canvas, (est_x - 8, est_y), (est_x + 8, est_y), (232, 212, 127), 1)
                cv2.line(canvas, (est_x, est_y - 8), (est_x, est_y + 8), (232, 212, 127), 1)
                cv2.putText(canvas, "EST", (est_x + 8, est_y + 12), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (232, 212, 127), 1, cv2.LINE_AA)

                # Tracking Error Vector Line (connecting measurement to estimate)
                if meas_x is not None and meas_y is not None:
                    cv2.line(canvas, (meas_x, meas_y), (est_x, est_y), (0, 165, 255), 1, cv2.LINE_AA)

        self.canvas.update_frame(canvas)
