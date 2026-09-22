"""HORIZON Phase 11.2 Hero Sensor View Component
===============================================
Hero camera feed view (55-65% screen visual area weight).
Renders real 640x480 optical frame (disturbed & perception overlays).
Plain sentence-case label: "Live sensor".

Overlays when data exists:
  - Detected beacon bounding box & centroid
  - Estimated target position & prediction
  - Covariance uncertainty ellipse
  - Image center reference mark (320, 240)

When no target / SEARCH state:
  - Short state tag: SEARCHING
  - Sentence case body text: "Target outside field of view"
  - Live monospace telemetry: search pattern name, pan rate, tilt rate, elapsed time
  - No fake target position!

Clean Reference Toggle:
  - "Ideal sensor reference" secondary panel (ON/OFF toggle, smaller & quieter).
"""

from __future__ import annotations
from typing import Optional, Tuple, Dict, Any
import cv2
import numpy as np

from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QImage, QPixmap, QPainter, QColor, QPen, QFont
from PySide6.QtWidgets import (
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from simulator.ui.foundation.tokens import (
    COLOR_FIELD,
    COLOR_FIELD_RAISED,
    COLOR_HAIRLINE_BORDER_HEX,
    COLOR_LOCK_CYAN,
    COLOR_TEXT_PRIMARY,
    COLOR_TEXT_SECONDARY,
    COLOR_VOID,
    FONT_BODY,
    FONT_HEADLINE,
    FONT_TELEMETRY,
    SPACING_8,
    SPACING_12,
    SPACING_16,
    TYPE_SCALE_BODY,
    TYPE_SCALE_MICRO,
    TYPE_SCALE_SECTION,
)
from simulator.ui.foundation.primitives import (
    MonospaceTelemetryLabel,
    PanelSurface,
    PanelVariant,
    SectionHeaderLabel,
    StateIndicatorPill,
    StatePillState,
)
from tracking.diagnostics.visualization import draw_tracking_annotations
from tracking.estimation.state import StateEstimate
from simulator.perception.detector import DetectionResult
from pat.state import PATState, PATMode


class SensorCanvasWidget(QLabel):
    """Clean 640x480 frame renderer widget with aspect-ratio scaling."""

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
        bytes_per_line = ch * w
        # Convert BGR -> RGB for Qt QImage
        rgb_frame = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        qimg = QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
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


class HeroSensorView(QWidget):
    """Hero Live Sensor Display View (Primary 640x480 Feed + Optional Ideal Reference)."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._show_ideal_reference = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(SPACING_12)

        # 1. Header Bar: Title ("Live sensor") + Ideal Reference Toggle
        header_bar = QHBoxLayout()
        header_bar.setContentsMargins(0, 0, 0, 0)
        header_bar.setSpacing(SPACING_12)

        lbl_title = SectionHeaderLabel("Live sensor", self)
        lbl_title.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY}; font-family: {FONT_BODY}; font-size: 15px; font-weight: 600;")
        header_bar.addWidget(lbl_title)

        # State Tag Pill (shows current PAT mode or CANDIDATE / SEARCHING tag)
        self.pill_sensor_state = StateIndicatorPill(StatePillState.IDLE, label_text="READY", parent=self)
        header_bar.addWidget(self.pill_sensor_state)

        # Extra info text (e.g. Detector model / Candidate info / Degraded reason)
        self.lbl_sensor_info = QLabel("Optical Perception: Hybrid (Classical + Neural)", self)
        self.lbl_sensor_info.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-family: {FONT_BODY}; font-size: 12px;")
        header_bar.addWidget(self.lbl_sensor_info)

        header_bar.addStretch()

        # Clean reference toggle
        self.chk_ideal_ref = QCheckBox("Ideal sensor reference", self)
        self.chk_ideal_ref.setStyleSheet(
            f"color: {COLOR_TEXT_SECONDARY}; font-family: {FONT_BODY}; font-size: 12px; font-weight: 500;"
        )
        self.chk_ideal_ref.stateChanged.connect(self._on_toggle_ideal_ref)
        header_bar.addWidget(self.chk_ideal_ref)

        layout.addLayout(header_bar)

        # 2. Main Viewport Container
        self.viewport_container = QHBoxLayout()
        self.viewport_container.setSpacing(SPACING_12)

        # Primary Hero Sensor Frame (Occupies main space)
        self.primary_canvas = SensorCanvasWidget(self)
        self.viewport_container.addWidget(self.primary_canvas, stretch=3)

        # Secondary Quiet Ideal Reference Frame (Visible only when toggle checked)
        self.ideal_ref_container = QWidget(self)
        self.ideal_ref_container.setVisible(False)
        ref_layout = QVBoxLayout(self.ideal_ref_container)
        ref_layout.setContentsMargins(0, 0, 0, 0)
        ref_layout.setSpacing(SPACING_8)

        lbl_ref_title = QLabel("Ideal sensor reference", self.ideal_ref_container)
        lbl_ref_title.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-family: {FONT_BODY}; font-size: 12px;")
        ref_layout.addWidget(lbl_ref_title)

        self.ideal_canvas = SensorCanvasWidget(self.ideal_ref_container)
        self.ideal_canvas.setMinimumSize(280, 210)
        ref_layout.addWidget(self.ideal_canvas)

        self.viewport_container.addWidget(self.ideal_ref_container, stretch=1)

        layout.addLayout(self.viewport_container, stretch=1)

        # 3. No-Target / Search State Telemetry Overlay Container
        self.search_info_panel = PanelSurface(PanelVariant.FIELD, self)
        self.search_info_panel.setMinimumHeight(44)
        s_layout = QHBoxLayout(self.search_info_panel)
        s_layout.setContentsMargins(SPACING_16, SPACING_8, SPACING_16, SPACING_8)
        s_layout.setSpacing(SPACING_16)

        self.lbl_search_msg = QLabel("Target outside field of view — Executing PAT search pattern", self.search_info_panel)
        self.lbl_search_msg.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-family: {FONT_BODY}; font-size: 13px;")
        s_layout.addWidget(self.lbl_search_msg)

        s_layout.addStretch()

        self.telem_pattern = MonospaceTelemetryLabel(value=None, unit="", label_text="Pattern", parent=self.search_info_panel)
        s_layout.addWidget(self.telem_pattern)

        self.telem_pan_rate = MonospaceTelemetryLabel(value=None, unit="°/s", label_text="Pan Rate", parent=self.search_info_panel)
        s_layout.addWidget(self.telem_pan_rate)

        self.telem_tilt_rate = MonospaceTelemetryLabel(value=None, unit="°/s", label_text="Tilt Rate", parent=self.search_info_panel)
        s_layout.addWidget(self.telem_tilt_rate)

        self.telem_search_time = MonospaceTelemetryLabel(value=None, unit="s", label_text="Elapsed", parent=self.search_info_panel)
        s_layout.addWidget(self.telem_search_time)

        layout.addWidget(self.search_info_panel)

    def _on_toggle_ideal_ref(self, state: int) -> None:
        self._show_ideal_reference = (state == Qt.CheckState.Checked.value)
        self.ideal_ref_container.setVisible(self._show_ideal_reference)

    def update_sensor_display(
        self,
        disturbed_frame: np.ndarray,
        clean_frame: Optional[np.ndarray],
        pat_state: PATState,
        detection_res: Optional[DetectionResult],
        estimate: Optional[StateEstimate],
        detector_source: str = "HYBRID",
        search_elapsed_s: float = 0.0,
    ) -> None:
        """Render updated frames and telemetry overlays from real backend data."""
        if disturbed_frame is None:
            return

        h, w = disturbed_frame.shape[:2]
        is_searching = (pat_state.mode in [PATMode.SEARCH, PATMode.REACQUIRE] and not (detection_res and detection_res.detected))

        # Annotate primary hero frame
        if is_searching:
            # SEARCH state: Do NOT draw fake target position. Draw clean image center crosshair only.
            annotated_primary = cv2.cvtColor(disturbed_frame, cv2.COLOR_GRAY2BGR) if disturbed_frame.ndim == 2 else disturbed_frame.copy()
            # Draw quiet image center mark (320, 240)
            cx, cy = w // 2, h // 2
            cv2.line(annotated_primary, (cx - 10, cy), (cx + 10, cy), (100, 100, 100), 1)
            cv2.line(annotated_primary, (cx, cy - 10), (cx, cy + 10), (100, 100, 100), 1)

            # Update search state telemetry panel
            self.search_info_panel.setVisible(True)
            self.lbl_search_msg.setText(
                "Target outside field of view — Executing reacquisition spiral"
                if pat_state.mode == PATMode.REACQUIRE
                else "Target outside field of view — Executing PAT search pattern"
            )
            self.telem_pattern.set_value(pat_state.active_search_strategy)
            self.telem_pan_rate.set_value(pat_state.actual_pan_rate, "°/s")
            self.telem_tilt_rate.set_value(pat_state.actual_tilt_rate, "°/s")
            self.telem_search_time.set_value(search_elapsed_s, "s")

            # State tag
            if pat_state.mode == PATMode.REACQUIRE:
                self.pill_sensor_state.set_state(StatePillState.LOST, "REACQUIRE")
            else:
                self.pill_sensor_state.set_state(StatePillState.IDLE, "SEARCHING")

            self.lbl_sensor_info.setText(f"Active Strategy: {pat_state.active_search_strategy}")

        else:
            # Detection or Tracking exists: Draw real detection/estimation overlays
            meas_pos = detection_res.centroid if (detection_res and detection_res.detected) else None
            annotated_primary = draw_tracking_annotations(
                frame=disturbed_frame,
                estimate=estimate,
                ground_truth_pos=None,  # No ground truth leakage into operational display
                measurement_pos=meas_pos,
                draw_ellipse=True,
                draw_velocity_vector=True,
                detection_result=detection_res,
            )

            # Draw image center reference crosshair (320, 240)
            cx, cy = w // 2, h // 2
            cv2.line(annotated_primary, (cx - 8, cy), (cx + 8, cy), (120, 120, 120), 1)
            cv2.line(annotated_primary, (cx, cy - 8), (cx, cy + 8), (120, 120, 120), 1)

            # Draw bounding box around detected beacon if present
            if detection_res and detection_res.detected and detection_res.bbox is not None:
                bx, by, bw, bh = detection_res.bbox
                cv2.rectangle(annotated_primary, (bx, by), (bx + bw, by + bh), (0, 240, 240), 1)

            self.search_info_panel.setVisible(False)

            # State tag & info update
            if pat_state.mode == PATMode.TRACK:
                self.pill_sensor_state.set_state(StatePillState.ACTIVE, "LOCKED")
                err_px = float(np.hypot(pat_state.pan_error_deg, pat_state.tilt_error_deg) * 60.0) if pat_state else 0.0
                self.lbl_sensor_info.setText(f"Detector: {detector_source} | Error: {err_px:.1f} arcmin | Quality: {pat_state.track_quality*100:.1f}%")
            elif pat_state.mode == PATMode.ACQUIRE:
                self.pill_sensor_state.set_state(StatePillState.ACTIVE, "ACQUIRE")
                self.lbl_sensor_info.setText(f"Acquiring lock: {pat_state.consecutive_hits} / 5 valid observations")
            elif pat_state.mode == PATMode.DEGRADED:
                self.pill_sensor_state.set_state(StatePillState.DEGRADED, "DEGRADED")
                cause = pat_state.transition_reason or "Low confidence / High innovation"
                self.lbl_sensor_info.setText(f"Degraded: {cause}")
            else:
                if detection_res and detection_res.detected:
                    self.pill_sensor_state.set_state(StatePillState.ACTIVE, "CANDIDATE")
                    self.lbl_sensor_info.setText(f"Candidate count: 1 | Conf: {detection_res.confidence*100:.1f}% | Source: {detector_source}")

        # Update primary canvas
        self.primary_canvas.update_frame(annotated_primary)

        # Update ideal reference frame if enabled
        if self._show_ideal_reference and clean_frame is not None:
            ideal_bgr = cv2.cvtColor(clean_frame, cv2.COLOR_GRAY2BGR) if clean_frame.ndim == 2 else clean_frame.copy()
            self.ideal_canvas.update_frame(ideal_bgr)
