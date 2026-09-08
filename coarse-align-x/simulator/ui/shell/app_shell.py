"""
HORIZON Main Application Shell Component
=======================================
Orchestrates global persistent header, 5-mode instrument bank switcher,
and stacked content container with 320ms cross-fade vertical settle animation (OutCubic).
"""

from __future__ import annotations
from typing import List
from PySide6.QtCore import QParallelAnimationGroup, QPoint, QPropertyAnimation
from PySide6.QtWidgets import QGraphicsOpacityEffect, QMainWindow, QStackedWidget, QVBoxLayout, QWidget
from simulator.ui.foundation.tokens import (
    COLOR_VOID,
    DURATION_SCREEN_MS,
    MOTION_EASING_CURVE,
)
from simulator.ui.shell.bank_switcher import ModeSelectorBank
from simulator.ui.shell.header import GlobalHeader
from simulator.ui.shell.placeholders import ModePlaceholderView
from simulator.ui.mission import MissionScreenView
from simulator.ui.live import LiveScreenView
from simulator.ui.track import TrackScreenView
from simulator.ui.stress import StressScreenView
from simulator.ui.benchmark import BenchmarkScreenView


class ApplicationShell(QMainWindow):
    """HORIZON Main Application Shell Window."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("HORIZON — AI Virtual Camera PAT Tracking Console")
        self.setMinimumSize(1280, 720)
        self.resize(1280, 800)
        self.setStyleSheet(f"QMainWindow {{ background-color: {COLOR_VOID}; }}")

        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 1. Persistent Global Header
        self.header = GlobalHeader(self)
        main_layout.addWidget(self.header)

        # 2. Mode Selector Bank Switcher Bar
        self.bank_switcher = ModeSelectorBank(self)
        self.bank_switcher.mode_changed.connect(self._on_mode_changed)
        main_layout.addWidget(self.bank_switcher)

        # 3. Stacked Content Area for the 5 Modes
        self.stack = QStackedWidget(self)
        main_layout.addWidget(self.stack)

        # Mode 0: Mission Control
        # Mode 1: Live Tracking
        # Mode 2: Track Diagnostics
        # Mode 3: Stress Testing
        # Mode 4: Benchmark Workstation

        self.mode_views: List[QWidget] = []
        for i in range(5):
            if i == 0:
                view = MissionScreenView(self)
                view.launch_requested.connect(self._on_mission_launched)
            elif i == 1:
                view = LiveScreenView(self)
            elif i == 2:
                view = TrackScreenView(self)
            elif i == 3:
                view = StressScreenView(self)
            elif i == 4:
                view = BenchmarkScreenView(self)
            else:
                view = ModePlaceholderView(i, self)
            self.stack.addWidget(view)
            self.mode_views.append(view)

        self._current_mode_index = 0
        self._anim_group: QParallelAnimationGroup | None = None

        # Select Live mode (index 1) by default as it is fully built in Phase 11.2
        self.bank_switcher.select_mode(1)

    def _on_mode_changed(self, new_index: int) -> None:
        if new_index == self._current_mode_index or new_index < 0 or new_index >= self.stack.count():
            return

        target_widget = self.stack.widget(new_index)
        self.stack.setCurrentIndex(new_index)
        self._current_mode_index = new_index

        # 320ms Cross-fade + 10px vertical settle animation
        opacity_effect = QGraphicsOpacityEffect(target_widget)
        target_widget.setGraphicsEffect(opacity_effect)

        fade_anim = QPropertyAnimation(opacity_effect, b"opacity")
        fade_anim.setDuration(DURATION_SCREEN_MS)
        fade_anim.setEasingCurve(MOTION_EASING_CURVE)
        fade_anim.setStartValue(0.0)
        fade_anim.setEndValue(1.0)

        pos_anim = QPropertyAnimation(target_widget, b"pos")
        pos_anim.setDuration(DURATION_SCREEN_MS)
        pos_anim.setEasingCurve(MOTION_EASING_CURVE)
        orig_pos = target_widget.pos()
        pos_anim.setStartValue(QPoint(orig_pos.x(), orig_pos.y() + 10))
        pos_anim.setEndValue(orig_pos)

        self._anim_group = QParallelAnimationGroup(self)
        self._anim_group.addAnimation(fade_anim)
        self._anim_group.addAnimation(pos_anim)
        self._anim_group.start()

    def _on_mission_launched(self, config) -> None:
        """Handle mission launch: configure Live screen with resolved AppConfig and switch to Live mode."""
        live_view = self.mode_views[1]
        if hasattr(live_view, "_config"):
            live_view._config = config
            live_view._on_reset_clicked()

        # Update header title
        self.header.set_experiment_info(f"EXP_{config.trajectory.type.upper()[:8]}", f"Scenario: {config.trajectory.type.capitalize()}")

        # Switch to Live mode (mode index 1)
        self.bank_switcher.select_mode(1)
