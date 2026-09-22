"""
HORIZON Phase 11.0 Motion Utilities
===================================
Standardized PySide6 animation factories enforcing strict 120ms/200ms/320ms duration tiers
and single decelerating OutCubic curve. Zero spring/bounce overshoot allowed.
"""

from __future__ import annotations
from typing import Optional
from PySide6.QtCore import QObject, QPropertyAnimation, QByteArray
from simulator.ui.foundation.tokens import (
    DURATION_COMPONENT_MS,
    DURATION_MICRO_MS,
    DURATION_SCREEN_MS,
    MOTION_EASING_CURVE,
)


def create_micro_animation(
    target: QObject, property_name: bytes | QByteArray, start_val: any, end_val: any
) -> QPropertyAnimation:
    """Create 120ms micro-animation (value/label updates)."""
    anim = QPropertyAnimation(target, property_name)
    anim.setDuration(DURATION_MICRO_MS)
    anim.setEasingCurve(MOTION_EASING_CURVE)
    anim.setStartValue(start_val)
    anim.setEndValue(end_val)
    return anim


def create_component_animation(
    target: QObject, property_name: bytes | QByteArray, start_val: any, end_val: any
) -> QPropertyAnimation:
    """Create 200ms component state transition animation."""
    anim = QPropertyAnimation(target, property_name)
    anim.setDuration(DURATION_COMPONENT_MS)
    anim.setEasingCurve(MOTION_EASING_CURVE)
    anim.setStartValue(start_val)
    anim.setEndValue(end_val)
    return anim


def create_screen_animation(
    target: QObject, property_name: bytes | QByteArray, start_val: any, end_val: any
) -> QPropertyAnimation:
    """Create 320ms screen transition animation."""
    anim = QPropertyAnimation(target, property_name)
    anim.setDuration(DURATION_SCREEN_MS)
    anim.setEasingCurve(MOTION_EASING_CURVE)
    anim.setStartValue(start_val)
    anim.setEndValue(end_val)
    return anim
