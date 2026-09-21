"""HORIZON Phase 11.2 Mission Status Control Strip
======================================================
Compact top strip in Live screen reusing foundation primitives.
Provides interactive simulation controls:
  - Play / Pause / Step / Reset
  - Disturbance preset selector (NOMINAL, DIFFICULT, SEVERE, RECOVERY, ADVERSARIAL)
  - Suppress detection toggle (Forced blackout test)
  - Automated Engineering Report export button
"""

from __future__ import annotations
from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QWidget,
)

from simulator.ui.foundation.tokens import (
    COLOR_FIELD,
    COLOR_FIELD_RAISED,
    COLOR_HAIRLINE_BORDER_HEX,
    COLOR_LOCK_CYAN,
    COLOR_LOST_RED,
    COLOR_TEXT_PRIMARY,
    COLOR_TEXT_SECONDARY,
    FONT_BODY,
    FONT_TELEMETRY,
    SPACING_8,
    SPACING_12,
    SPACING_16,
)
from simulator.ui.foundation.primitives import (
    MonospaceTelemetryLabel,
    PrimaryButton,
    SecondaryButton,
    StateIndicatorPill,
    StatePillState,
)


class MissionStatusStrip(QFrame):
    """Compact Mission Control Strip for Live Screen."""

    play_toggled = Signal(bool)          # True -> Start/Resume, False -> Pause
    step_clicked = Signal()
    reset_clicked = Signal()
    preset_changed = Signal(str)         # Disturbance preset name
    blackout_toggled = Signal(bool)      # Suppress detection test
    report_clicked = Signal()

    PRESETS = ["NOMINAL", "DIFFICULT", "SEVERE", "RECOVERY", "ADVERSARIAL"]

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedHeight(48)
        self.setStyleSheet(
            f"""
            QFrame {{
                background-color: {COLOR_FIELD};
                border-bottom: 1px solid {COLOR_HAIRLINE_BORDER_HEX};
                border-radius: 4px;
            }}
            """
        )

        layout = QHBoxLayout(self)
        layout.setContentsMargins(SPACING_16, 0, SPACING_16, 0)
        layout.setSpacing(SPACING_12)

        # 1. Controls: Play / Pause / Step / Reset
        self.btn_play = PrimaryButton("▶ Run Simulation", parent=self)
        self.btn_play.clicked.connect(self._on_play_click)
        layout.addWidget(self.btn_play)

        self.btn_step = SecondaryButton("Step", parent=self)
        self.btn_step.clicked.connect(lambda: self.step_clicked.emit())
        layout.addWidget(self.btn_step)

        self.btn_reset = SecondaryButton("Reset", parent=self)
        self.btn_reset.clicked.connect(lambda: self.reset_clicked.emit())
        layout.addWidget(self.btn_reset)

        # Separator
        sep1 = QLabel("|", self)
        sep1.setStyleSheet(f"color: {COLOR_HAIRLINE_BORDER_HEX}; font-size: 16px;")
        layout.addWidget(sep1)

        # 2. Disturbance Preset Selector
        lbl_preset = QLabel("Disturbance:", self)
        lbl_preset.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-size: 12px; font-family: {FONT_BODY};")
        layout.addWidget(lbl_preset)

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
            }}
            """
        )
        self.combo_preset.currentTextChanged.connect(lambda p: self.preset_changed.emit(p))
        layout.addWidget(self.combo_preset)

        # 3. Suppress Detection Toggle (Forced Blackout Test)
        self.btn_blackout = SecondaryButton("⚡ Suppress Detection (Test Loss)", parent=self)
        self.btn_blackout.setCheckable(True)
        self.btn_blackout.toggled.connect(self._on_blackout_toggle)
        layout.addWidget(self.btn_blackout)

        layout.addStretch()

        # 4. Generate Report Action
        self.btn_report = SecondaryButton("📄 Export Engineering Report", parent=self)
        self.btn_report.clicked.connect(lambda: self.report_clicked.emit())
        layout.addWidget(self.btn_report)

        self._is_playing = False

    def _on_play_click(self) -> None:
        self._is_playing = not self._is_playing
        if self._is_playing:
            self.btn_play.setText("⏸ Pause Simulation")
        else:
            self.btn_play.setText("▶ Resume Simulation")
        self.play_toggled.emit(self._is_playing)

    def _on_blackout_toggle(self, checked: bool) -> None:
        if checked:
            self.btn_blackout.setText("⚡ Detection SUPPRESSED")
            self.btn_blackout.setStyleSheet(
                f"background-color: rgba(232, 111, 127, 0.2); color: {COLOR_LOST_RED}; border: 1px solid {COLOR_LOST_RED}; font-weight: 700;"
            )
        else:
            self.btn_blackout.setText("⚡ Suppress Detection (Test Loss)")
            self.btn_blackout.setStyleSheet("")
        self.blackout_toggled.emit(checked)

    def set_playing_state(self, is_playing: bool) -> None:
        self._is_playing = is_playing
        if self._is_playing:
            self.btn_play.setText("⏸ Pause Simulation")
        else:
            self.btn_play.setText("▶ Run Simulation")
