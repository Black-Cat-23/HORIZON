"""
Panel Surface Component Primitive
=================================
Luminance step surface container (void, field, field-raised variants) with 1px hairline border. No drop shadows.
"""

from __future__ import annotations
from enum import Enum
from PySide6.QtWidgets import QFrame, QVBoxLayout, QWidget
from simulator.ui.foundation.tokens import (
    COLOR_FIELD,
    COLOR_FIELD_RAISED,
    COLOR_HAIRLINE_BORDER_HEX,
    COLOR_VOID,
)


class PanelVariant(str, Enum):
    VOID = "VOID"
    FIELD = "FIELD"
    FIELD_RAISED = "FIELD_RAISED"


class PanelSurface(QFrame):
    """Panel container primitive supporting void/field/field-raised luminance steps."""

    def __init__(self, variant: PanelVariant = PanelVariant.FIELD, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.variant = variant
        self._setup_style()

    def set_variant(self, variant: PanelVariant) -> None:
        self.variant = variant
        self._setup_style()

    def _setup_style(self) -> None:
        bg_color = COLOR_FIELD
        if self.variant == PanelVariant.VOID:
            bg_color = COLOR_VOID
        elif self.variant == PanelVariant.FIELD_RAISED:
            bg_color = COLOR_FIELD_RAISED

        self.setStyleSheet(
            f"""
            QFrame {{
                background-color: {bg_color};
                border: 1px solid {COLOR_HAIRLINE_BORDER_HEX};
                border-radius: 4px;
            }}
            """
        )
