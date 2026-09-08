"""HORIZON Phase 11.5 Disturbance Controls Component
======================================================
Interactive disturbance parameter controls:
  - Preset Selector Bank (NOMINAL, DIFFICULT, SEVERE, RECOVERY, ADVERSARIAL, CUSTOM)
  - Real disturbance parameters: Gaussian sigma, Salt & Pepper, Poisson, Camera Jitter, Platform Motion, Atmosphere.
  - "Run stress test" primary action button.
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
    QSlider,
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
    FONT_BODY,
    SPACING_4,
    SPACING_8,
    SPACING_12,
    SPACING_16,
)
from simulator.ui.foundation.primitives import (
    ExpandableDiagnosticContainer,
    PanelSurface,
    PanelVariant,
    PrimaryButton,
    SectionHeaderLabel,
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

    PRESETS = ["NOMINAL", "DIFFICULT", "SEVERE", "RECOVERY", "ADVERSARIAL", "CUSTOM"]
    ATMOSPHERES = ["clear", "haze", "fog", "rain", "low_light"]

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._updating_preset = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(SPACING_8)

        # Header Title: "Disturbance controls" (sentence case)
        header = SectionHeaderLabel("Disturbance controls", self)
        header.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY}; font-family: {FONT_BODY}; font-size: 14px; font-weight: 600;")
        layout.addWidget(header)

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
        scroll_area = QScrollArea(self)
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        scroll_area.setStyleSheet("background: transparent;")
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        scroll_content = QWidget(scroll_area)
        scroll_content.setStyleSheet("background: transparent;")
        form_layout = QFormLayout(scroll_content)
        form_layout.setHorizontalSpacing(SPACING_12)
        form_layout.setVerticalSpacing(SPACING_12)

        # A. Gaussian Noise Sigma
        self.spin_gaussian = QDoubleSpinBox(scroll_content)
        self.spin_gaussian.setRange(0.0, 20.0)
        self.spin_gaussian.setSingleStep(0.5)
        self.spin_gaussian.setSuffix(" σ")
        self.spin_gaussian.valueChanged.connect(self._on_user_field_change)
        form_layout.addRow("Gaussian Noise:", self.spin_gaussian)

        # B. Salt & Pepper Probability
        self.spin_sp = QDoubleSpinBox(scroll_content)
        self.spin_sp.setRange(0.00, 0.10)
        self.spin_sp.setSingleStep(0.01)
        self.spin_sp.setDecimals(2)
        self.spin_sp.setSuffix(" p")
        self.spin_sp.valueChanged.connect(self._on_user_field_change)
        form_layout.addRow("Salt & Pepper Noise:", self.spin_sp)

        # C. Poisson Shot Noise (Peak Photons)
        self.spin_poisson = QDoubleSpinBox(scroll_content)
        self.spin_poisson.setRange(10.0, 100.0)
        self.spin_poisson.setSingleStep(5.0)
        self.spin_poisson.setSuffix(" photons")
        self.spin_poisson.setValue(100.0)
        self.spin_poisson.valueChanged.connect(self._on_user_field_change)
        form_layout.addRow("Poisson Peak Flux:", self.spin_poisson)

        # D. Camera Jitter Max
        self.spin_jitter = QDoubleSpinBox(scroll_content)
        self.spin_jitter.setRange(0.0, 20.0)
        self.spin_jitter.setSingleStep(1.0)
        self.spin_jitter.setSuffix(" px")
        self.spin_jitter.valueChanged.connect(self._on_user_field_change)
        form_layout.addRow("Camera Jitter Max:", self.spin_jitter)

        # E. Platform Motion Velocity
        self.spin_platform = QDoubleSpinBox(scroll_content)
        self.spin_platform.setRange(0.0, 120.0)
        self.spin_platform.setSingleStep(5.0)
        self.spin_platform.setSuffix(" px/s")
        self.spin_platform.valueChanged.connect(self._on_user_field_change)
        form_layout.addRow("Platform Velocity:", self.spin_platform)

        # F. Atmosphere Condition
        self.combo_atmo = QComboBox(scroll_content)
        self.combo_atmo.addItems(self.ATMOSPHERES)
        self.combo_atmo.currentTextChanged.connect(self._on_user_field_change)
        form_layout.addRow("Atmosphere Condition:", self.combo_atmo)

        scroll_area.setWidget(scroll_content)
        layout.addWidget(scroll_area, stretch=1)

        # 3. Action Button: "Run stress test" (sentence case per patched button rules)
        self.btn_run_test = PrimaryButton("Run stress test", parent=self)
        self.btn_run_test.clicked.connect(lambda: self.run_test_requested.emit())
        layout.addWidget(self.btn_run_test)

        # Load NOMINAL preset by default
        self._on_preset_selected("NOMINAL")

    def _on_preset_selected(self, preset_name: str) -> None:
        self._updating_preset = True
        try:
            cfg = get_preset_config(preset_name)
            if not cfg.enabled:
                self.spin_gaussian.setValue(0.0)
                self.spin_sp.setValue(0.0)
                self.spin_poisson.setValue(100.0)
                self.spin_jitter.setValue(0.0)
                self.spin_platform.setValue(0.0)
                self.combo_atmo.setCurrentText("clear")
            else:
                self.spin_gaussian.setValue(cfg.gaussian.sigma if cfg.gaussian.enabled else 0.0)
                self.spin_sp.setValue(cfg.salt_pepper.probability if cfg.salt_pepper.enabled else 0.0)
                self.spin_poisson.setValue(cfg.poisson.peak_photons if cfg.poisson.enabled else 100.0)
                self.spin_jitter.setValue(cfg.camera_jitter.max_x_px if cfg.camera_jitter.enabled else 0.0)
                self.spin_platform.setValue(cfg.platform_motion.velocity_x if cfg.platform_motion.enabled else 0.0)
                self.combo_atmo.setCurrentText(cfg.atmosphere.condition if cfg.atmosphere.enabled else "clear")

            self._emit_config()
        finally:
            self._updating_preset = False

    def _on_user_field_change(self) -> None:
        if not self._updating_preset:
            # Switch preset display to "CUSTOM" when user manually changes a control
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
        atmo = self.combo_atmo.currentText()

        enabled = (g_sig > 0 or sp_prob > 0 or p_photons < 100 or j_max > 0 or p_vel > 0 or atmo != "clear")

        config = DisturbanceConfig(
            enabled=enabled,
            salt_pepper=SaltPepperConfig(enabled=(sp_prob > 0), probability=sp_prob),
            gaussian=GaussianNoiseConfig(enabled=(g_sig > 0), sigma=g_sig),
            poisson=PoissonNoiseConfig(enabled=(p_photons < 100), peak_photons=p_photons),
            camera_jitter=CameraJitterConfig(enabled=(j_max > 0), max_x_px=j_max, max_y_px=j_max),
            platform_motion=PlatformMotionConfig(enabled=(p_vel > 0), model="linear", velocity_x=p_vel, velocity_y=p_vel*0.5),
            atmosphere=AtmosphereConfig(enabled=(atmo != "clear"), condition=atmo),
        )
        self.disturbance_changed.emit(config)
