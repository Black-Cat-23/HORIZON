"""HORIZON Phase 11.5 System Response & Disturbance Telemetry Panel
=====================================================================
Displays effective disturbance levels and system response metrics:
  - Supports Staged/Configuring vs Live Running states.
  - Disturbance: Effective Gaussian sigma, Salt & Pepper, Jitter offset, Platform displacement, Atmosphere contrast.
  - System Response: Perception confidence, Track quality, Tracking error, PAT State pill, Pipeline FPS.
"""

from __future__ import annotations
import math
from typing import Optional
import numpy as np
from PySide6.QtWidgets import QFormLayout, QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from simulator.ui.foundation.tokens import (
    COLOR_HAIRLINE_BORDER_HEX,
    COLOR_TEXT_SECONDARY,
    FONT_BODY,
    SPACING_4,
    SPACING_8,
    SPACING_12,
    SPACING_16,
)
from simulator.ui.foundation.primitives import (
    MonospaceTelemetryLabel,
    PanelSurface,
    PanelVariant,
    SectionHeaderLabel,
    StateIndicatorPill,
    StatePillState,
)
from simulator.disturbances.pipeline import DisturbanceTelemetry
from simulator.disturbances.config import DisturbanceConfig
from pat.state import PATMode, PATState
from simulator.perception.detector import DetectionResult

class SystemResponsePanelWidget(PanelSurface):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(PanelVariant.FIELD, parent)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(SPACING_16, SPACING_12, SPACING_16, SPACING_12)
        main_layout.setSpacing(SPACING_12)

        main_layout.addWidget(SectionHeaderLabel("Active disturbance telemetry", self))
        grid_d = QFormLayout()
        grid_d.setHorizontalSpacing(SPACING_16)
        grid_d.setVerticalSpacing(SPACING_4)

        self.telem_g_sig = MonospaceTelemetryLabel(value=None, unit="σ", label_text="Gaussian Noise", parent=self)
        self.telem_sp_prob = MonospaceTelemetryLabel(value=None, unit="p", label_text="Salt & Pepper", parent=self)
        self.telem_jitter_offset = MonospaceTelemetryLabel(value=None, unit="px", label_text="Jitter Offset", parent=self)
        self.telem_plat_disp = MonospaceTelemetryLabel(value=None, unit="px", label_text="Platform Offset", parent=self)
        self.telem_atmo_trans = MonospaceTelemetryLabel(value=None, unit="x", label_text="Contrast Factor", parent=self)

        grid_d.addRow(self.telem_g_sig)
        grid_d.addRow(self.telem_sp_prob)
        grid_d.addRow(self.telem_jitter_offset)
        grid_d.addRow(self.telem_plat_disp)
        grid_d.addRow(self.telem_atmo_trans)
        main_layout.addLayout(grid_d)

        sep = QFrame(self)
        sep.setStyleSheet(f"background-color: {COLOR_HAIRLINE_BORDER_HEX}; max-height: 1px;")
        main_layout.addWidget(sep)

        main_layout.addWidget(SectionHeaderLabel("System causal response", self))

        pill_bar = QHBoxLayout()
        pill_bar.setSpacing(SPACING_8)
        lbl_pat_title = QLabel("PAT State:", self)
        lbl_pat_title.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-family: {FONT_BODY}; font-size: 12px;")
        pill_bar.addWidget(lbl_pat_title)

        self.pill_pat_state = StateIndicatorPill(StatePillState.IDLE, label_text="IDLE", parent=self)
        pill_bar.addWidget(self.pill_pat_state)
        pill_bar.addStretch()
        main_layout.addLayout(pill_bar)

        grid_r = QFormLayout()
        grid_r.setHorizontalSpacing(SPACING_16)
        grid_r.setVerticalSpacing(SPACING_4)

        self.telem_conf = MonospaceTelemetryLabel(value=None, unit="%", label_text="Perception Conf", parent=self)
        self.telem_quality = MonospaceTelemetryLabel(value=None, unit="%", label_text="Track Quality", parent=self)
        self.telem_error = MonospaceTelemetryLabel(value=None, unit="px", label_text="Tracking Error", parent=self)
        self.telem_peak_err = MonospaceTelemetryLabel(value=None, unit="px", label_text="Peak Error", parent=self)
        self.telem_reacq_lat = MonospaceTelemetryLabel(value=None, unit="ms", label_text="Reacq Latency", parent=self)
        self.telem_fps = MonospaceTelemetryLabel(value=None, unit="FPS", label_text="Pipeline Rate", parent=self)

        grid_r.addRow(self.telem_conf)
        grid_r.addRow(self.telem_quality)
        grid_r.addRow(self.telem_error)
        grid_r.addRow(self.telem_peak_err)
        grid_r.addRow(self.telem_reacq_lat)
        grid_r.addRow(self.telem_fps)
        main_layout.addLayout(grid_r)

        main_layout.addStretch()
        
        self._peak_error_px = 0.0
        self._last_reacq_ms = 0.0

    def update_telemetry(
        self,
        screen_state: str,
        staged_config: DisturbanceConfig,
        dist_telem: Optional[DisturbanceTelemetry],
        pat_state: Optional[PATState],
        detection_res: Optional[DetectionResult],
        fps: float,
    ) -> None:
        # Handle Staged/Idle states
        if screen_state != "running":
            # Show staged parameters
            if staged_config.enabled:
                self.telem_g_sig.set_value(f"{staged_config.gaussian.sigma if staged_config.gaussian.enabled else 0.0} (stgd)", "")
                self.telem_sp_prob.set_value(f"{staged_config.salt_pepper.probability if staged_config.salt_pepper.enabled else 0.0} (stgd)", "")
                self.telem_jitter_offset.set_value(f"{staged_config.camera_jitter.max_x_px if staged_config.camera_jitter.enabled else 0.0} (stgd)", "")
                self.telem_plat_disp.set_value(f"{staged_config.platform_motion.velocity_x if staged_config.platform_motion.enabled else 0.0} (stgd)", "")
                self.telem_atmo_trans.set_value(f"{staged_config.atmosphere.severity if staged_config.atmosphere.enabled else 0.0} (stgd)", "")
            else:
                self.telem_g_sig.set_value("0.0 (stgd)", "")
                self.telem_sp_prob.set_value("0.0 (stgd)", "")
                self.telem_jitter_offset.set_value("0.0 (stgd)", "")
                self.telem_plat_disp.set_value("0.0 (stgd)", "")
                self.telem_atmo_trans.set_value("0.0 (stgd)", "")

            self.pill_pat_state.set_state(StatePillState.IDLE, "OFFLINE")
            self.telem_quality.set_value("--", "")
            self.telem_error.set_value("--", "")
            self.telem_peak_err.set_value("--", "")
            self.telem_reacq_lat.set_value("--", "")
            self.telem_conf.set_value("--", "")
            self.telem_fps.set_value("--", "")
            return

        # Handle Running State
        if dist_telem is not None and dist_telem.disturbance_enabled:
            self.telem_g_sig.set_value(dist_telem.gaussian_sigma if dist_telem.gaussian_enabled else 0.0, "σ")
            self.telem_sp_prob.set_value(dist_telem.salt_pepper_probability if dist_telem.salt_pepper_enabled else 0.0, "p")
            j_off = float(np.hypot(dist_telem.camera_jitter_x, dist_telem.camera_jitter_y)) if dist_telem.camera_jitter_enabled else 0.0
            self.telem_jitter_offset.set_value(j_off, "px")
            p_off = float(np.hypot(dist_telem.platform_offset_x, dist_telem.platform_offset_y)) if dist_telem.platform_motion_enabled else 0.0
            self.telem_plat_disp.set_value(p_off, "px")
            self.telem_atmo_trans.set_value(dist_telem.contrast_factor if dist_telem.atmosphere_enabled else 1.0, "x")
        else:
            self.telem_g_sig.set_value(0.0, "σ")
            self.telem_sp_prob.set_value(0.0, "p")
            self.telem_jitter_offset.set_value(0.0, "px")
            self.telem_plat_disp.set_value(0.0, "px")
            self.telem_atmo_trans.set_value(1.0, "x")

        if pat_state is not None:
            if pat_state.mode == PATMode.TRACK:
                self.pill_pat_state.set_state(StatePillState.ACTIVE, "LOCKED")
            elif pat_state.mode == PATMode.ACQUIRE:
                self.pill_pat_state.set_state(StatePillState.CONFIRMED, "ACQUIRE")
            elif pat_state.mode == PATMode.DEGRADED:
                self.pill_pat_state.set_state(StatePillState.DEGRADED, "DEGRADED")
            elif pat_state.mode == PATMode.REACQUIRE:
                self.pill_pat_state.set_state(StatePillState.LOST, "REACQUIRE")
                self._last_reacq_ms = pat_state.mode_duration_s * 1000.0
            else:
                self.pill_pat_state.set_state(StatePillState.IDLE, "SEARCHING")
                self._last_reacq_ms = pat_state.mode_duration_s * 1000.0

            self.telem_quality.set_value(pat_state.track_quality * 100.0, "%")
            err_px = float(np.hypot(pat_state.pan_error_deg, pat_state.tilt_error_deg) * 160.0)
            
            if err_px > self._peak_error_px:
                self._peak_error_px = err_px
            self._peak_error_px *= 0.99 

            self.telem_error.set_value(err_px, "px")
            self.telem_peak_err.set_value(self._peak_error_px, "px")
            self.telem_reacq_lat.set_value(self._last_reacq_ms, "ms")
        else:
            self.pill_pat_state.set_state(StatePillState.IDLE, "READY")
            self.telem_quality.set_value(None)
            self.telem_error.set_value(None)
            self.telem_peak_err.set_value(None)
            self.telem_reacq_lat.set_value(None)

        if detection_res and detection_res.detected:
            self.telem_conf.set_value(detection_res.confidence * 100.0, "%")
        else:
            self.telem_conf.set_value(0.0, "%")

        self.telem_fps.set_value(fps, "FPS")
