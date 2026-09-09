"""HORIZON Phase 11.2 Event Timeline Component
================================================
Bottom strip rendering timestamped real event records.
Event Types: SEARCH, CANDIDATE FOUND, ACQUIRE, TRACK, DEGRADED, REACQUIRE, TRACK RESTORED.
Visually quiet (12px General Sans type, hairline separators).
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import List
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QScrollArea, QVBoxLayout, QWidget

from simulator.ui.foundation.tokens import (
    COLOR_FIELD,
    COLOR_HAIRLINE_BORDER_HEX,
    COLOR_LOCK_CYAN,
    COLOR_TEXT_PRIMARY,
    COLOR_TEXT_SECONDARY,
    FONT_BODY,
    FONT_TELEMETRY,
    SPACING_4,
    SPACING_8,
    SPACING_12,
    SPACING_16,
    TYPE_SCALE_MICRO,
)
from simulator.ui.foundation.primitives import (
    PanelSurface,
    PanelVariant,
    SectionHeaderLabel,
    StateIndicatorPill,
    StatePillState,
)


@dataclass
class TimelineEventRecord:
    timestamp_s: float
    event_type: str
    description: str


class EventItemWidget(QWidget):
    """Individual event record entry item."""

    def __init__(self, record: TimelineEventRecord, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(SPACING_8, SPACING_4, SPACING_8, SPACING_4)
        layout.setSpacing(SPACING_8)

        # Monospace timestamp (e.g. "T+ 12.34s")
        lbl_time = QLabel(f"T+ {record.timestamp_s:05.2f}s", self)
        lbl_time.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-family: {FONT_TELEMETRY}; font-size: 11px;")
        layout.addWidget(lbl_time)

        # Short event tag
        pill_state = StatePillState.ACTIVE if "TRACK" in record.event_type else (
            StatePillState.DEGRADED if "DEGRADED" in record.event_type else (
                StatePillState.LOST if "REACQUIRE" in record.event_type else StatePillState.IDLE
            )
        )
        pill = StateIndicatorPill(pill_state, label_text=record.event_type, parent=self)
        layout.addWidget(pill)

        # Event description
        lbl_desc = QLabel(record.description, self)
        lbl_desc.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY}; font-family: {FONT_BODY}; font-size: 12px;")
        layout.addWidget(lbl_desc)

        # Hairline separator
        sep = QLabel("|", self)
        sep.setStyleSheet(f"color: {COLOR_HAIRLINE_BORDER_HEX}; font-size: 12px;")
        layout.addWidget(sep)


class EventTimelineWidget(PanelSurface):
    """Bottom Event Timeline Strip Widget."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(PanelVariant.FIELD, parent)
        self.setFixedHeight(48)

        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(SPACING_16, SPACING_4, SPACING_16, SPACING_4)
        main_layout.setSpacing(SPACING_12)

        # Header Title: "Event timeline" (sentence case)
        title = SectionHeaderLabel("Event timeline", self)
        title.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY}; font-family: {FONT_BODY}; font-size: 12px; font-weight: 600;")
        main_layout.addWidget(title)

        # Scrollable events area
        self.scroll_area = QScrollArea(self)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll_area.setStyleSheet("background: transparent;")
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.scroll_content = QWidget(self.scroll_area)
        self.scroll_content.setStyleSheet("background: transparent;")
        self.events_layout = QHBoxLayout(self.scroll_content)
        self.events_layout.setContentsMargins(0, 0, 0, 0)
        self.events_layout.setSpacing(SPACING_4)

        self.lbl_empty = QLabel("No timeline events logged yet — start simulation to record events", self.scroll_content)
        self.lbl_empty.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-family: {FONT_BODY}; font-size: 12px; font-style: italic;")
        self.events_layout.addWidget(self.lbl_empty)
        self.events_layout.addStretch()

        self.scroll_area.setWidget(self.scroll_content)
        main_layout.addWidget(self.scroll_area, stretch=1)

        self._records: List[TimelineEventRecord] = []

    def add_event(self, timestamp_s: float, event_type: str, description: str) -> None:
        """Append a real logged event record to the timeline."""
        record = TimelineEventRecord(timestamp_s, event_type, description)
        self._records.append(record)

        if len(self._records) == 1 and hasattr(self, "lbl_empty") and self.lbl_empty is not None:
            try:
                self.lbl_empty.setVisible(False)
            except RuntimeError:
                pass

        item = EventItemWidget(record, self.scroll_content)
        # Insert before stretch
        self.events_layout.insertWidget(self.events_layout.count() - 1, item)

        # Scroll to latest event
        self.scroll_area.horizontalScrollBar().setValue(self.scroll_area.horizontalScrollBar().maximum())

    def clear_events(self) -> None:
        """Clear all events (e.g. on simulation reset)."""
        self._records.clear()
        while self.events_layout.count() > 2:
            item = self.events_layout.takeAt(0)
            if item and item.widget():
                w = item.widget()
                w.setParent(None)
                w.deleteLater()
        if hasattr(self, "lbl_empty") and self.lbl_empty is not None:
            try:
                self.lbl_empty.setVisible(True)
            except RuntimeError:
                pass
