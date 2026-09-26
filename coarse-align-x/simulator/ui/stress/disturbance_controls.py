"""HORIZON Phase 11.5 Disturbance Controls Component
======================================================
Interactive disturbance parameter controls:
  - Preset Selector Bank & Explicit CUSTOM mode
  - Run Status Pill indicating idle/staged/running
  - Controls locked during active run
"""

from __future__ import annotations
from typing import Optional
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from simulator.ui.foundation.tokens import (
    COLOR_FIELD_RAISED,
    COLOR_HAIRLINE_BORDER_HEX,
    COLOR_TEXT_PRIMARY,
    COLOR_TEXT_SECONDARY,
    FONT_BODY,
    SPACING_8,
    SPACING_12,
)
from simulator.ui.foundation.primitives import (
    PrimaryButton,
    SectionHeaderLabel,
    StateIndicatorPill,
    StatePillState
)
from simulator.disturbances.config import (
    AtmosphereConfig,
    CameraJitterConfig,
    DisturbanceConfig,
    GaussianNoiseConfig,
    PlatformMotionConfig,
    PoissonNoiseConfig,
    SaltPepperConfig,
)
from simulator.disturbances.presets import get_preset_config

class DisturbanceControlsWidget(QWidget):
    """Interactive Disturbance Controls Panel Widget."""

    disturbance_changed = Signal(object)  # Emits DisturbanceConfig
    run_test_requested = Signal()        # Emits on "Run stress test" click

    PRESETS = [
        "NOMINAL", "DIFFICULT", "SEVERE", "RECOVERY", "ADVERSARIAL", 
        "DISTRACTOR_BURST", "OCCLUSION_EVENT", "BRIGHTNESS_FADE", 
        "JITTER_BURST", "PLATFORM_SWING", "COMBINED_TURBULENCE", "CUSTOM"
    ]
    ATMOSPHERES = ["clear", "haze", "fog", "rain", "low_light"]
    PLATFORM_MODELS = ["linear", "circular", "random", "spiral", "figure8"]

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._updating_preset = False
        self._custom_config_data = {} # Preserves custom values

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(SPACING_8)

        # Header Title
        header = SectionHeaderLabel("Disturbance controls", self)
        header.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY}; font-family: {FONT_BODY}; font-size: 14px; font-weight: 600;")
        layout.addWidget(header)

        # Status Pill for Run State
        self.pill_status = StateIndicatorPill(StatePillState.IDLE, label_text="IDLE", parent=self)
        layout.addWidget(self.pill_status)

        # 1. Preset Selector Combo Box
        preset_layout = QHBoxLayout()
        preset_layout.setSpacing(SPACING_8)

        lbl_preset = QLabel("Preset Profile:", self)
        lbl_preset.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-family: {FONT_BODY}; font-size: 12px;")
        preset_layout.addWidget(lbl_preset)

        self.combo_preset = QComboBox(self)
        self.combo_preset.addItems(self.PRESETS)
        self.combo_preset.setStyleSheet(
            f"""
            QComboBox {{
                background-color: {COLOR_FIELD_RAISED};
                color: {COLOR_TEXT_PRIMARY};
                border: 1px solid {COLOR_HAIRLINE_BORDER_HEX};
                border-radius: 3px;
                padding: 4px 8px;
                font-family: {FONT_BODY};
                font-size: 12px;
                font-weight: 600;
            }}
            """
        )
        self.combo_preset.currentTextChanged.connect(self._on_preset_selected)
        preset_layout.addWidget(self.combo_preset, stretch=1)
        layout.addLayout(preset_layout)

        # 2. Scrollable Sliders & Form
        self.scroll_area = QScrollArea(self)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll_area.setStyleSheet("background: transparent;")
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.scroll_content = QWidget(self.scroll_area)
        self.scroll_content.setStyleSheet("background: transparent;")
        form_layout = QFormLayout(self.scroll_content)
        form_layout.setHorizontalSpacing(SPACING_12)
        form_layout.setVerticalSpacing(SPACING_12)

        # A. Gaussian Noise Sigma
        self.spin_gaussian = QDoubleSpinBox(self.scroll_content)
        self.spin_gaussian.setRange(0.0, 20.0)
        self.spin_gaussian.setSingleStep(0.5)
        self.spin_gaussian.setSuffix(" σ")
        self.spin_gaussian.valueChanged.connect(self._on_user_field_change)
        form_layout.addRow("Gaussian Noise:", self.spin_gaussian)

        # B. Salt & Pepper Probability
        self.spin_sp = QDoubleSpinBox(self.scroll_content)
        self.spin_sp.setRange(0.00, 1.0)
        self.spin_sp.setSingleStep(0.01)
        self.spin_sp.setDecimals(2)
        self.spin_sp.setSuffix(" p")
        self.spin_sp.valueChanged.connect(self._on_user_field_change)
        form_layout.addRow("Salt & Pepper Noise:", self.spin_sp)

        # C. Poisson Shot Noise
        self.spin_poisson = QDoubleSpinBox(self.scroll_content)
        self.spin_poisson.setRange(10.0, 100.0)
        self.spin_poisson.setSingleStep(5.0)
        self.spin_poisson.setSuffix(" photons")
        self.spin_poisson.valueChanged.connect(self._on_user_field_change)
        form_layout.addRow("Poisson Peak Flux:", self.spin_poisson)

        # D. Camera Jitter Max
        self.spin_jitter = QDoubleSpinBox(self.scroll_content)
        self.spin_jitter.setRange(0.0, 100.0)
        self.spin_jitter.setSingleStep(1.0)
        self.spin_jitter.setSuffix(" px")
        self.spin_jitter.valueChanged.connect(self._on_user_field_change)
        form_layout.addRow("Camera Jitter Max:", self.spin_jitter)

        # E. Platform Motion Velocity & Model
        self.spin_platform = QDoubleSpinBox(self.scroll_content)
        self.spin_platform.setRange(0.0, 200.0)
        self.spin_platform.setSingleStep(5.0)
        self.spin_platform.setSuffix(" px/s")
        self.spin_platform.valueChanged.connect(self._on_user_field_change)
        form_layout.addRow("Platform Velocity:", self.spin_platform)

        self.combo_platform_model = QComboBox(self.scroll_content)
        self.combo_platform_model.addItems(self.PLATFORM_MODELS)
        self.combo_platform_model.currentTextChanged.connect(self._on_user_field_change)
        form_layout.addRow("Platform Model:", self.combo_platform_model)

        # F. Atmosphere Condition
        self.combo_atmo = QComboBox(self.scroll_content)
        self.combo_atmo.addItems(self.ATMOSPHERES)
        self.combo_atmo.currentTextChanged.connect(self._on_user_field_change)
        form_layout.addRow("Atmosphere Condition:", self.combo_atmo)

        self.spin_atmo_severity = QDoubleSpinBox(self.scroll_content)
        self.spin_atmo_severity.setRange(0.0, 1.0)
        self.spin_atmo_severity.setSingleStep(0.1)
        self.spin_atmo_severity.valueChanged.connect(self._on_user_field_change)
        form_layout.addRow("Atmosphere Severity:", self.spin_atmo_severity)

        self.scroll_area.setWidget(self.scroll_content)
        layout.addWidget(self.scroll_area, stretch=1)

        # 3. Action Button
        self.btn_run_test = PrimaryButton("Run stress test", parent=self)
        self.btn_run_test.clicked.connect(lambda: self.run_test_requested.emit())
        layout.addWidget(self.btn_run_test)

        self._on_preset_selected("NOMINAL")

    def set_run_state(self, state: str, current_frame: int, total_frames: int):
        """Called by StressScreenView to lock UI and update progress pill."""
        if state == "running":
            self.pill_status.set_state(StatePillState.ACTIVE, f"RUNNING ({current_frame}/{total_frames})")
            self.scroll_content.setEnabled(False)
            self.combo_preset.setEnabled(False)
            self.btn_run_test.setText("Stop stress test")
        elif state == "completed":
            self.pill_status.set_state(StatePillState.CONFIRMED, "COMPLETED")
            self.scroll_content.setEnabled(True)
            self.combo_preset.setEnabled(True)
            self.btn_run_test.setText("Run stress test")
        else: # idle, configuring
            self.pill_status.set_state(StatePillState.IDLE, "IDLE - CONFIGURING")
            self.scroll_content.setEnabled(True)
            self.combo_preset.setEnabled(True)
            self.btn_run_test.setText("Run stress test")

    def _on_preset_selected(self, preset_name: str) -> None:
        self._updating_preset = True
        try:
            if preset_name == "CUSTOM":
                if "gaussian" in self._custom_config_data:
                    self.spin_gaussian.setValue(self._custom_config_data["gaussian"])
                    self.spin_sp.setValue(self._custom_config_data["sp"])
                    self.spin_poisson.setValue(self._custom_config_data["poisson"])
                    self.spin_jitter.setValue(self._custom_config_data["jitter"])
                    self.spin_platform.setValue(self._custom_config_data["platform"])
                    self.combo_platform_model.setCurrentText(self._custom_config_data["model"])
                    self.combo_atmo.setCurrentText(self._custom_config_data["atmo"])
                    self.spin_atmo_severity.setValue(self._custom_config_data["atmo_sev"])
            else:
                cfg = get_preset_config(preset_name)
                if not cfg.enabled:
                    self.spin_gaussian.setValue(0.0)
                    self.spin_sp.setValue(0.0)
                    self.spin_poisson.setValue(100.0)
                    self.spin_jitter.setValue(0.0)
                    self.spin_platform.setValue(0.0)
                    self.combo_platform_model.setCurrentText("linear")
                    self.combo_atmo.setCurrentText("clear")
                    self.spin_atmo_severity.setValue(0.5)
                else:
                    self.spin_gaussian.setValue(cfg.gaussian.sigma if cfg.gaussian.enabled else 0.0)
                    self.spin_sp.setValue(cfg.salt_pepper.probability if cfg.salt_pepper.enabled else 0.0)
                    self.spin_poisson.setValue(cfg.poisson.peak_photons if cfg.poisson.enabled else 100.0)
                    self.spin_jitter.setValue(cfg.camera_jitter.max_x_px if cfg.camera_jitter.enabled else 0.0)
                    self.spin_platform.setValue(cfg.platform_motion.velocity_x if cfg.platform_motion.enabled else 0.0)
                    self.combo_platform_model.setCurrentText(cfg.platform_motion.model if cfg.platform_motion.enabled else "linear")
                    self.combo_atmo.setCurrentText(cfg.atmosphere.condition if cfg.atmosphere.enabled else "clear")
                    self.spin_atmo_severity.setValue(cfg.atmosphere.severity if cfg.atmosphere.enabled else 0.5)

            self._emit_config()
        finally:
            self._updating_preset = False

    def _on_user_field_change(self) -> None:
        if not self._updating_preset:
            # Save custom config
            self._custom_config_data = {
                "gaussian": self.spin_gaussian.value(),
                "sp": self.spin_sp.value(),
                "poisson": self.spin_poisson.value(),
                "jitter": self.spin_jitter.value(),
                "platform": self.spin_platform.value(),
                "model": self.combo_platform_model.currentText(),
                "atmo": self.combo_atmo.currentText(),
                "atmo_sev": self.spin_atmo_severity.value()
            }
            self.combo_preset.blockSignals(True)
            self.combo_preset.setCurrentText("CUSTOM")
            self.combo_preset.blockSignals(False)
            self._emit_config()

    def _emit_config(self) -> None:
        g_sig = self.spin_gaussian.value()
        sp_prob = self.spin_sp.value()
        p_photons = self.spin_poisson.value()
        j_max = self.spin_jitter.value()
        p_vel = self.spin_platform.value()
        p_model = self.combo_platform_model.currentText()
        atmo = self.combo_atmo.currentText()
        atmo_sev = self.spin_atmo_severity.value()

        enabled = (g_sig > 0 or sp_prob > 0 or p_photons < 100 or j_max > 0 or p_vel > 0 or atmo != "clear")

        config = DisturbanceConfig(
            enabled=enabled,
            salt_pepper=SaltPepperConfig(enabled=(sp_prob > 0), probability=sp_prob),
            gaussian=GaussianNoiseConfig(enabled=(g_sig > 0), sigma=g_sig),
            poisson=PoissonNoiseConfig(enabled=(p_photons < 100), peak_photons=p_photons),
            camera_jitter=CameraJitterConfig(enabled=(j_max > 0), max_x_px=j_max, max_y_px=j_max),
            platform_motion=PlatformMotionConfig(enabled=(p_vel > 0), model=p_model, velocity_x=p_vel, velocity_y=p_vel*0.5),
            atmosphere=AtmosphereConfig(enabled=(atmo != "clear"), condition=atmo, severity=atmo_sev),
        )
        self.disturbance_changed.emit(config)

