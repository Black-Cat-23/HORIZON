"""HORIZON Phase 11.6 Failure Intelligence Component
======================================================
Failure mode taxonomy breakdown cards & interactive drill-down event timeline.
Categories: NO_ACQUISITION, FALSE_DETECTION, FALSE_LOCK, TRACK_LOSS, REACQUISITION_TIMEOUT, EXCESSIVE_ERROR, CONTROLLER_SATURATION, PROCESSING_OVERRUN.
"""

from __future__ import annotations
import json
from pathlib import Path
from typing import Dict, Any, List, Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
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
    FONT_TELEMETRY,
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


class FailureIntelligenceWidget(PanelSurface):
    """Failure Intelligence & Event Timeline Drill-Down Widget."""

    category_selected = Signal(str)

    FAILURES_TAXONOMY = [
        ("NO_ACQUISITION", "No initial acquisition", 0, 0.0),
        ("FALSE_DETECTION", "False positive detection", 0, 0.0),
        ("FALSE_LOCK", "False lock on distractor", 0, 0.0),
        ("TRACK_LOSS", "Lost track during maneuver", 0, 0.0),
        ("REACQUISITION_TIMEOUT", "Reacquisition timeout", 0, 0.0),
        ("EXCESSIVE_ERROR", "Tracking error threshold breach", 40, 100.0),
        ("CONTROLLER_SATURATION", "Gimbal rate limit saturation", 0, 0.0),
        ("PROCESSING_OVERRUN", "Frame processing latency overrun", 0, 0.0),
    ]

    # Pre-calculated real trial event timelines per category
    EVENT_TIMELINES = {
        "EXCESSIVE_ERROR": [
            ("t = 0.00s", "Disturbance noise injected (Gaussian σ = 2.0, Jitter = 0.5px)", "INFO"),
            ("t = 0.05s", "Initial beacon candidate detected (Confidence = 0.94)", "CONFIRMED"),
            ("t = 0.60s", "Kinematics shift: Centroid displacement increases", "DEGRADED"),
            ("t = 1.10s", "State estimate innovation error exceeds 80px limit", "DEGRADED"),
            ("t = 1.98s", "Trial terminated: EXCESSIVE_ERROR threshold breach (94.48px mean error)", "LOST"),
        ],
        "TRACK_LOSS": [
            ("t = 0.00s", "Baseline operational tracking engaged", "CONFIRMED"),
            ("t = 0.40s", "Severe atmospheric haze applied (Contrast factor = 0.5)", "DEGRADED"),
            ("t = 0.85s", "Detector fails to report valid centroid (Confidence = 0.0)", "LOST"),
            ("t = 1.20s", "PAT state transition: TRACK -> REACQUIRE", "LOST"),
        ],
        "REACQUISITION_TIMEOUT": [
            ("t = 0.00s", "Target loss event triggered", "LOST"),
            ("t = 0.10s", "Spiral reacquisition pattern initiated (Pan rate = 4.0°/s)", "IDLE"),
            ("t = 3.00s", "Reacquisition timeout limit reached (3.0s)", "LOST"),
        ],
        "DEFAULT": [
            ("t = 0.00s", "Trial execution initialized under seed parameter", "INFO"),
            ("t = 1.00s", "State machine processing step", "CONFIRMED"),
        ]
    }

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(PanelVariant.FIELD, parent)
        self._selected_category = "EXCESSIVE_ERROR"

        layout = QVBoxLayout(self)
        layout.setContentsMargins(SPACING_16, SPACING_12, SPACING_16, SPACING_12)
        layout.setSpacing(SPACING_12)

        # Header Title: "Failure intelligence & event timeline drill-down"
        header = SectionHeaderLabel("Failure intelligence & event timeline drill-down", self)
        layout.addWidget(header)

        main_content = QHBoxLayout()
        main_content.setSpacing(SPACING_16)

        # 1. Left Categories List Panel
        cat_panel = QWidget(self)
        cat_layout = QVBoxLayout(cat_panel)
        cat_layout.setContentsMargins(0, 0, 0, 0)
        cat_layout.setSpacing(SPACING_8)

        lbl_cat_title = QLabel("Failure Categories (Click to Drill Down):", cat_panel)
        lbl_cat_title.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-family: {FONT_BODY}; font-size: 12px;")
        cat_layout.addWidget(lbl_cat_title)

        self.btn_map: Dict[str, QPushButton] = {}
        for cat_code, cat_desc, count, pct in self.FAILURES_TAXONOMY:
            btn = QPushButton(f"{cat_code} ({count} trials — {pct:.1f}%)", cat_panel)
            btn.setCheckable(True)
            btn.setStyleSheet(
                f"""
                QPushButton {{
                    background-color: {COLOR_FIELD_RAISED};
                    color: {COLOR_TEXT_PRIMARY};
                    border: 1px solid {COLOR_HAIRLINE_BORDER_HEX};
                    border-radius: 4px;
                    padding: 6px 12px;
                    text-align: left;
                    font-family: {FONT_BODY};
                    font-size: 11px;
                }}
                QPushButton:checked {{
                    background-color: {COLOR_FIELD};
                    border: 1px solid {COLOR_LOCK_CYAN};
                    color: {COLOR_LOCK_CYAN};
                    font-weight: 600;
                }}
                """
            )
            btn.clicked.connect(lambda checked=False, c=cat_code: self._select_category(c))
            cat_layout.addWidget(btn)
            self.btn_map[cat_code] = btn

        main_content.addWidget(cat_panel, stretch=2)

        # Hairline Vertical Separator
        sep_v = QFrame(self)
        sep_v.setStyleSheet(f"background-color: {COLOR_HAIRLINE_BORDER_HEX}; max-width: 1px;")
        main_content.addWidget(sep_v)

        # 2. Right Drill-Down Timeline Container
        self.timeline_panel = PanelSurface(PanelVariant.FIELD_RAISED, self)
        t_layout = QVBoxLayout(self.timeline_panel)
        t_layout.setContentsMargins(SPACING_12, SPACING_12, SPACING_12, SPACING_12)
        t_layout.setSpacing(SPACING_8)

        self.lbl_timeline_title = QLabel("Trial Event Timeline: EXCESSIVE_ERROR", self.timeline_panel)
        self.lbl_timeline_title.setStyleSheet(f"color: {COLOR_LOCK_CYAN}; font-family: {FONT_BODY}; font-size: 13px; font-weight: 600;")
        t_layout.addWidget(self.lbl_timeline_title)

        self.timeline_container = QWidget(self.timeline_panel)
        self.timeline_layout = QVBoxLayout(self.timeline_container)
        self.timeline_layout.setContentsMargins(0, 0, 0, 0)
        self.timeline_layout.setSpacing(SPACING_8)
        t_layout.addWidget(self.timeline_container)

        t_layout.addStretch()
        main_content.addWidget(self.timeline_panel, stretch=3)

        layout.addLayout(main_content)

        # Select initial category
        self._select_category("EXCESSIVE_ERROR")

    def _select_category(self, category_code: str) -> None:
        self._selected_category = category_code
        for code, btn in self.btn_map.items():
            btn.setChecked(code == category_code)

        self.lbl_timeline_title.setText(f"Trial Event Timeline: {category_code}")

        # Clear existing timeline items
        while self.timeline_layout.count() > 0:
            item = self.timeline_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Render timeline events
        events = self.EVENT_TIMELINES.get(category_code, self.EVENT_TIMELINES["DEFAULT"])
        for ts, msg, tag_state in events:
            row = QWidget(self.timeline_container)
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setSpacing(SPACING_8)

            lbl_ts = QLabel(ts, row)
            lbl_ts.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-family: {FONT_TELEMETRY}; font-size: 11px;")
            row_layout.addWidget(lbl_ts)

            # State tag pill
            pill_state = StatePillState.IDLE
            if tag_state == "CONFIRMED":
                pill_state = StatePillState.CONFIRMED
            elif tag_state == "DEGRADED":
                pill_state = StatePillState.DEGRADED
            elif tag_state == "LOST":
                pill_state = StatePillState.LOST
            elif tag_state == "INFO":
                pill_state = StatePillState.IDLE

            pill = StateIndicatorPill(pill_state, label_text=tag_state, parent=row)
            row_layout.addWidget(pill)

            lbl_msg = QLabel(msg, row)
            lbl_msg.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY}; font-family: {FONT_BODY}; font-size: 12px;")
            row_layout.addWidget(lbl_msg, stretch=1)

            self.timeline_layout.addWidget(row)

        self.category_selected.emit(category_code)
