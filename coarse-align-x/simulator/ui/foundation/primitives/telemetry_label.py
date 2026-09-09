"""
Monospace Telemetry Label Component Primitive
=============================================
Renders numeric telemetry values in tabular monospace figures with a text-secondary unit suffix.
Supports an explicit "N/A" state visually distinct from a real zero value.
"""

from __future__ import annotations
from PySide6.QtWidgets import QHBoxLayout, QLabel, QWidget
from simulator.ui.foundation.tokens import (
    COLOR_TEXT_PRIMARY,
    COLOR_TEXT_SECONDARY,
    TYPE_SCALE_BODY,
)


class MonospaceTelemetryLabel(QWidget):
    """Numeric telemetry readout primitive with tabular figures and explicit N/A state."""

    def __init__(
        self,
        value: float | int | str | None = None,
        unit: str = "",
        label_text: str = "",
        font_size_px: int = TYPE_SCALE_BODY,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.unit = unit
        self.font_size_px = font_size_px
        self.label_text = label_text

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        if label_text:
            self._desc_label = QLabel(f"{label_text}:", self)
            self._desc_label.setStyleSheet(
                f"""
                QLabel {{
                    color: {COLOR_TEXT_SECONDARY};
                    font-family: 'General Sans', sans-serif;
                    font-size: {max(11, font_size_px - 2)}px;
                }}
                """
            )
            layout.addWidget(self._desc_label)

        self._val_label = QLabel(self)
        self._unit_label = QLabel(unit, self)

        layout.addWidget(self._val_label)
        layout.addWidget(self._unit_label)
        layout.addStretch()

        self.set_value(value, unit)

    def set_value(self, value: float | int | str | None, unit: str | None = None) -> None:
        if unit is not None:
            self.unit = unit
            self._unit_label.setText(unit)

        if value is None or value == "N/A":
            self._val_label.setText("N/A")
            self._val_label.setStyleSheet(
                f"""
                QLabel {{
                    color: {COLOR_TEXT_SECONDARY};
                    font-family: 'JetBrains Mono', 'Space Mono', monospace;
                    font-size: {self.font_size_px}px;
                    font-weight: 400;
                    font-style: italic;
                }}
                """
            )
        else:
            text = f"{value:.2f}" if isinstance(value, float) else str(value)
            self._val_label.setText(text)
            self._val_label.setStyleSheet(
                f"""
                QLabel {{
                    color: {COLOR_TEXT_PRIMARY};
                    font-family: 'JetBrains Mono', 'Space Mono', monospace;
                    font-size: {self.font_size_px}px;
                    font-weight: 600;
                }}
                """
            )

        self._unit_label.setStyleSheet(
            f"""
            QLabel {{
                color: {COLOR_TEXT_SECONDARY};
                font-family: 'General Sans', sans-serif;
                font-size: {max(10, self.font_size_px - 2)}px;
            }}
            """
        )
