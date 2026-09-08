"""HORIZON Phase 11.6 Ablation Comparison Component
=====================================================
Ablation study comparing: Classical, Neural, Basic fusion, Fusion + optical, Full hybrid.
Renders 5 side-by-side progress / metric bars with unified scale [0.0 - 300.0 px] tracking error.
"""

from __future__ import annotations
from typing import Dict, Any, List

from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QColor, QFont, QPainter, QPen, QBrush
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
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
    COLOR_VOID,
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
)


class AblationBarCanvas(QWidget):
    """Custom canvas for rendering unified-scale ablation comparison bars."""

    VARIANTS = [
        ("Classical", 300.0, QColor("#EF4444")),
        ("Neural", 94.8, QColor("#F59E0B")),
        ("Basic fusion", 87.1, QColor("#3B82F6")),
        ("Fusion + optical", 86.8, QColor("#10B981")),
        ("Full hybrid", 86.7, QColor("#00F0FF")),
    ]

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumHeight(160)
        self.setStyleSheet(f"background-color: {COLOR_VOID}; border: 1px solid {COLOR_HAIRLINE_BORDER_HEX}; border-radius: 4px;")

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()
        pad_l, pad_r, pad_t, pad_b = 120, 40, 20, 20

        plot_w = w - pad_l - pad_r
        plot_h = h - pad_t - pad_b

        num_vars = len(self.VARIANTS)
        bar_gap = plot_h / num_vars
        max_val_scale = 320.0  # Unified scale across all 5 variants

        for idx, (var_name, val_err, color) in enumerate(self.VARIANTS):
            y_top = pad_t + (idx * bar_gap) + 4
            bar_h = bar_gap - 8

            # Variant Label
            painter.setPen(QPen(QColor(COLOR_TEXT_PRIMARY), 1))
            painter.setFont(QFont(FONT_BODY, 11, QFont.Weight.Bold if var_name == "Full hybrid" else QFont.Weight.Normal))
            painter.drawText(10, int(y_top + bar_h/2 + 4), var_name)

            # Background slot bar
            painter.setPen(QPen(QColor(COLOR_HAIRLINE_BORDER_HEX), 1))
            painter.setBrush(QBrush(QColor(COLOR_FIELD_RAISED)))
            painter.drawRect(int(pad_l), int(y_top), int(plot_w), int(bar_h))

            # Value Bar fill
            fill_w = (val_err / max_val_scale) * plot_w
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(color))
            painter.drawRect(int(pad_l), int(y_top), int(fill_w), int(bar_h))

            # Numeric Value Text
            painter.setPen(QPen(QColor(COLOR_TEXT_PRIMARY), 1))
            painter.setFont(QFont(FONT_TELEMETRY, 10, QFont.Weight.Bold))
            painter.drawText(int(pad_l + fill_w + 8), int(y_top + bar_h/2 + 4), f"{val_err:.1f} px")


class AblationComparisonWidget(PanelSurface):
    """Ablation Study Architecture Comparison Component Widget."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(PanelVariant.FIELD, parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(SPACING_16, SPACING_12, SPACING_16, SPACING_12)
        layout.setSpacing(SPACING_12)

        # Header Title: "Architecture ablation study (unified scale 0-320px error)"
        header = SectionHeaderLabel("Architecture ablation study (unified scale 0-320px error)", self)
        layout.addWidget(header)

        # Unified Scale Bar Canvas
        self.canvas = AblationBarCanvas(self)
        layout.addWidget(self.canvas)
