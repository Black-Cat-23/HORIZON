"""HORIZON Phase 11.2 Telemetry Panel Component
=================================================
Telemetry panel grouped by domain with sentence-case section labels:
  - Target: position, velocity, confidence, track quality
  - Camera: pan, tilt, pan rate, tilt rate
  - Control: pan error, tilt error, command rate, actual rate
  - Computation: FPS, latency

Every value uses MonospaceTelemetryLabel primitive. Initial state: N/A.
"""

from __future__ import annotations
from typing import Optional
from PySide6.QtWidgets import QFrame, QGridLayout, QHBoxLayout, QVBoxLayout, QWidget

from simulator.ui.foundation.tokens import (
    COLOR_FIELD,
    COLOR_FIELD_RAISED,
    COLOR_HAIRLINE_BORDER_HEX,
    COLOR_TEXT_PRIMARY,
    COLOR_TEXT_SECONDARY,
    FONT_BODY,
    SPACING_8,
    SPACING_12,
    SPACING_16,
)
from simulator.ui.foundation.primitives import (
    MonospaceTelemetryLabel,
    PanelSurface,
    PanelVariant,
    SectionHeaderLabel,
)
from pat.state import PATState
from tracking.estimation.state import StateEstimate
from simulator.perception.detector import DetectionResult


class TelemetryPanel(PanelSurface):
    """Domain-grouped Live Telemetry Panel Widget."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(PanelVariant.FIELD, parent)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(SPACING_16, SPACING_16, SPACING_16, SPACING_16)
        main_layout.setSpacing(SPACING_16)

        # ----------------------------------------------------------------------
        # 1. Target Telemetry Group
        # ----------------------------------------------------------------------
        main_layout.addWidget(SectionHeaderLabel("Target telemetry", self))
        grid_target = QGridLayout()
        grid_target.setHorizontalSpacing(SPACING_16)
        grid_target.setVerticalSpacing(SPACING_8)

        self.telem_target_pos = MonospaceTelemetryLabel(value=None, unit="px", label_text="Position (x,y)", parent=self)
        self.telem_target_vel = MonospaceTelemetryLabel(value=None, unit="px/s", label_text="Velocity (vx,vy)", parent=self)
        self.telem_confidence = MonospaceTelemetryLabel(value=None, unit="%", label_text="Confidence", parent=self)
        self.telem_quality = MonospaceTelemetryLabel(value=None, unit="%", label_text="Track quality", parent=self)

        grid_target.addWidget(self.telem_target_pos, 0, 0)
        grid_target.addWidget(self.telem_target_vel, 0, 1)
        grid_target.addWidget(self.telem_confidence, 1, 0)
        grid_target.addWidget(self.telem_quality, 1, 1)
        main_layout.addLayout(grid_target)

        # Hairline Separator
        sep1 = QFrame(self)
        sep1.setStyleSheet(f"background-color: {COLOR_HAIRLINE_BORDER_HEX}; max-height: 1px;")
        main_layout.addWidget(sep1)

        # ----------------------------------------------------------------------
        # 2. Camera Telemetry Group
        # ----------------------------------------------------------------------
        main_layout.addWidget(SectionHeaderLabel("Camera telemetry", self))
        grid_cam = QGridLayout()
        grid_cam.setHorizontalSpacing(SPACING_16)
        grid_cam.setVerticalSpacing(SPACING_8)

        self.telem_cam_pan = MonospaceTelemetryLabel(value=None, unit="°", label_text="Pan angle", parent=self)
        self.telem_cam_tilt = MonospaceTelemetryLabel(value=None, unit="°", label_text="Tilt angle", parent=self)
        self.telem_cam_pan_rate = MonospaceTelemetryLabel(value=None, unit="°/s", label_text="Pan rate", parent=self)
        self.telem_cam_tilt_rate = MonospaceTelemetryLabel(value=None, unit="°/s", label_text="Tilt rate", parent=self)

        grid_cam.addWidget(self.telem_cam_pan, 0, 0)
        grid_cam.addWidget(self.telem_cam_tilt, 0, 1)
        grid_cam.addWidget(self.telem_cam_pan_rate, 1, 0)
        grid_cam.addWidget(self.telem_cam_tilt_rate, 1, 1)
        main_layout.addLayout(grid_cam)

        # Hairline Separator
        sep2 = QFrame(self)
        sep2.setStyleSheet(f"background-color: {COLOR_HAIRLINE_BORDER_HEX}; max-height: 1px;")
        main_layout.addWidget(sep2)

        # ----------------------------------------------------------------------
        # 3. Control Telemetry Group
        # ----------------------------------------------------------------------
        main_layout.addWidget(SectionHeaderLabel("PAT control telemetry", self))
        grid_ctrl = QGridLayout()
        grid_ctrl.setHorizontalSpacing(SPACING_16)
        grid_ctrl.setVerticalSpacing(SPACING_8)

        self.telem_pan_error = MonospaceTelemetryLabel(value=None, unit="°", label_text="Pan error", parent=self)
        self.telem_tilt_error = MonospaceTelemetryLabel(value=None, unit="°", label_text="Tilt error", parent=self)
        self.telem_cmd_rate = MonospaceTelemetryLabel(value=None, unit="°/s", label_text="Command rate", parent=self)
        self.telem_act_rate = MonospaceTelemetryLabel(value=None, unit="°/s", label_text="Actual rate", parent=self)

        grid_ctrl.addWidget(self.telem_pan_error, 0, 0)
        grid_ctrl.addWidget(self.telem_tilt_error, 0, 1)
        grid_ctrl.addWidget(self.telem_cmd_rate, 1, 0)
        grid_ctrl.addWidget(self.telem_act_rate, 1, 1)
        main_layout.addLayout(grid_ctrl)

        # Hairline Separator
        sep3 = QFrame(self)
        sep3.setStyleSheet(f"background-color: {COLOR_HAIRLINE_BORDER_HEX}; max-height: 1px;")
        main_layout.addWidget(sep3)

        # ----------------------------------------------------------------------
        # 4. Computation Telemetry Group
        # ----------------------------------------------------------------------
        main_layout.addWidget(SectionHeaderLabel("Computation telemetry", self))
        grid_comp = QGridLayout()
        grid_comp.setHorizontalSpacing(SPACING_16)
        grid_comp.setVerticalSpacing(SPACING_8)

        self.telem_fps = MonospaceTelemetryLabel(value=None, unit="FPS", label_text="Framerate", parent=self)
        self.telem_latency = MonospaceTelemetryLabel(value=None, unit="ms", label_text="Pipeline latency", parent=self)

        grid_comp.addWidget(self.telem_fps, 0, 0)
        grid_comp.addWidget(self.telem_latency, 0, 1)
        main_layout.addLayout(grid_comp)

        main_layout.addStretch()

    def update_telemetry(
        self,
        pat_state: Optional[PATState],
        detection_res: Optional[DetectionResult],
        estimate: Optional[StateEstimate],
        camera_pan: float,
        camera_tilt: float,
        camera_pan_rate: float,
        camera_tilt_rate: float,
        cmd_pan_rate: float,
        cmd_tilt_rate: float,
        fps: float,
        latency_ms: float,
    ) -> None:
        """Update live telemetry values from real backend state."""
        if pat_state is None:
            # Idle / N/A state
            self.telem_target_pos.set_value(None)
            self.telem_target_vel.set_value(None)
            self.telem_confidence.set_value(None)
            self.telem_quality.set_value(None)
            self.telem_cam_pan.set_value(None)
            self.telem_cam_tilt.set_value(None)
            self.telem_cam_pan_rate.set_value(None)
            self.telem_cam_tilt_rate.set_value(None)
            self.telem_pan_error.set_value(None)
            self.telem_tilt_error.set_value(None)
            self.telem_cmd_rate.set_value(None)
            self.telem_act_rate.set_value(None)
            self.telem_fps.set_value(None)
            self.telem_latency.set_value(None)
            return

        # Target Telemetry
        if estimate is not None:
            self.telem_target_pos.set_value(f"{estimate.estimated_x:.1f}, {estimate.estimated_y:.1f}")
            self.telem_target_vel.set_value(f"{estimate.estimated_vx:.1f}, {estimate.estimated_vy:.1f}")
        else:
            self.telem_target_pos.set_value(None)
            self.telem_target_vel.set_value(None)

        if detection_res and detection_res.detected:
            self.telem_confidence.set_value(detection_res.confidence * 100.0, "%")
        else:
            self.telem_confidence.set_value(0.0, "%")

        self.telem_quality.set_value(pat_state.track_quality * 100.0, "%")

        # Camera Telemetry
        self.telem_cam_pan.set_value(camera_pan, "°")
        self.telem_cam_tilt.set_value(camera_tilt, "°")
        self.telem_cam_pan_rate.set_value(camera_pan_rate, "°/s")
        self.telem_cam_tilt_rate.set_value(camera_tilt_rate, "°/s")

        # Control Telemetry
        self.telem_pan_error.set_value(pat_state.pan_error_deg, "°")
        self.telem_tilt_error.set_value(pat_state.tilt_error_deg, "°")
        self.telem_cmd_rate.set_value(cmd_pan_rate, "°/s")
        self.telem_act_rate.set_value(pat_state.actual_pan_rate, "°/s")

        # Computation Telemetry
        self.telem_fps.set_value(fps, "FPS")
        self.telem_latency.set_value(latency_ms, "ms")
