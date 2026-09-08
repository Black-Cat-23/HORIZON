"""
HORIZON Global Header Component
===============================
Persistent top navigation bar (64px fixed height multiple of 8).
Left to Right: Wordmark, Experiment ID, Scenario Name, Runtime Status, PAT State, Live FPS.
Truthful Idle State: READY / READY / N/A before simulation launch.
"""

from __future__ import annotations
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QWidget
from simulator.ui.foundation.tokens import (
    COLOR_FIELD,
    COLOR_HAIRLINE_BORDER_HEX,
    COLOR_TEXT_PRIMARY,
    COLOR_TEXT_SECONDARY,
    FONT_HEADLINE,
    FONT_BODY,
    SPACING_16,
    SPACING_24,
    TYPE_SCALE_SECTION,
)
from simulator.ui.foundation.primitives import (
    MonospaceTelemetryLabel,
    StateIndicatorPill,
    StatePillState,
)


class GlobalHeader(QFrame):
    """Persistent 64px global telemetry header bar."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedHeight(64)
        self.setStyleSheet(
            f"""
            QFrame {{
                background-color: {COLOR_FIELD};
                border-bottom: 1px solid {COLOR_HAIRLINE_BORDER_HEX};
            }}
            """
        )

        layout = QHBoxLayout(self)
        layout.setContentsMargins(SPACING_24, 0, SPACING_24, 0)
        layout.setSpacing(SPACING_16)

        # 1. HORIZON Wordmark (Headline font, 20px, bold)
        self.wordmark = QLabel("HORIZON", self)
        self.wordmark.setStyleSheet(
            f"color: {COLOR_TEXT_PRIMARY}; font-family: {FONT_HEADLINE}; font-size: {TYPE_SCALE_SECTION}px; font-weight: 700; letter-spacing: 2px;"
        )
        layout.addWidget(self.wordmark)

        # Separator Line
        sep1 = QLabel("|", self)
        sep1.setStyleSheet(f"color: {COLOR_HAIRLINE_BORDER_HEX}; font-size: 18px;")
        layout.addWidget(sep1)

        # 2. Experiment ID (Body font, text-secondary until loaded)
        self.lbl_experiment = QLabel("NO EXPERIMENT LOADED", self)
        self.lbl_experiment.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-family: {FONT_BODY}; font-size: 13px;")
        layout.addWidget(self.lbl_experiment)

        # 3. Scenario Name (Body font, text-secondary until selected)
        self.lbl_scenario = QLabel("•  NO SCENARIO", self)
        self.lbl_scenario.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-family: {FONT_BODY}; font-size: 13px;")
        layout.addWidget(self.lbl_scenario)

        layout.addStretch()

        # 4. Runtime Status Pill (Truthful default: READY)
        self.lbl_runtime_title = QLabel("Runtime:", self)
        self.lbl_runtime_title.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-size: 12px;")
        layout.addWidget(self.lbl_runtime_title)
        self.pill_runtime = StateIndicatorPill(StatePillState.IDLE, label_text="READY", parent=self)
        layout.addWidget(self.pill_runtime)

        # 5. PAT State Pill (Truthful default: READY)
        self.lbl_pat_title = QLabel("PAT:", self)
        self.lbl_pat_title.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-size: 12px;")
        layout.addWidget(self.lbl_pat_title)
        self.pill_pat = StateIndicatorPill(StatePillState.IDLE, label_text="READY", parent=self)
        layout.addWidget(self.pill_pat)

        # 6. Live FPS Readout (Monospace live value, default N/A)
        self.lbl_fps_title = QLabel("FPS:", self)
        self.lbl_fps_title.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-size: 12px;")
        layout.addWidget(self.lbl_fps_title)
        self.telem_fps = MonospaceTelemetryLabel(value=None, unit="", font_size_px=14, parent=self)
        layout.addWidget(self.telem_fps)

    def set_experiment_info(self, exp_id: str, scenario_name: str) -> None:
        self.lbl_experiment.setText(exp_id)
        self.lbl_scenario.setText(f"•  {scenario_name}")
        self.lbl_experiment.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY}; font-family: {FONT_BODY}; font-size: 13px; font-weight: 600;")
        self.lbl_scenario.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY}; font-family: {FONT_BODY}; font-size: 13px;")

    def set_runtime_status(self, state: StatePillState, text: str | None = None) -> None:
        self.pill_runtime.set_state(state, text)

    def set_pat_status(self, state: StatePillState, text: str | None = None) -> None:
        self.pill_pat.set_state(state, text)

    def set_fps(self, fps_val: float | None) -> None:
        self.telem_fps.set_value(fps_val)
