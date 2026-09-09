"""
HORIZON Phase 11.0 Design Tokens (Patched Neutral Surface & Typography)
======================================================================
Single source of truth for color, typography, spacing, and motion.
All UI components MUST consume these tokens exclusively.
"""

from __future__ import annotations
from PySide6.QtCore import QEasingCurve

# ==============================================================================
# REVISED COLOR PALETTE (True Neutral, Extreme Dark Instrument Domain)
# ==============================================================================
COLOR_VOID = "#0A0A0B"           # Base background — near-black, neutral
COLOR_FIELD = "#16161A"          # Panel/surface — one neutral step up
COLOR_FIELD_RAISED = "#202024"   # Second neutral step up — reserved use only

# Fixed Semantic State Colors (Domain Convention: ONLY for state indicators)
COLOR_LOCK_CYAN = "#7FD4E8"      # Active / selected / engineering focus ONLY
COLOR_CONFIRM_GREEN = "#6FE8A8"  # Confirmed healthy state ONLY
COLOR_DISTURBANCE_AMBER = "#E8A15C"# Active degradation ONLY
COLOR_LOST_RED = "#E86F7F"       # Actual loss / error ONLY

# Revised Neutral Text Colors
COLOR_TEXT_PRIMARY = "#F2F2F4"   # Primary reading text (soft neutral white)
COLOR_TEXT_SECONDARY = "#8E8E96" # Labels, secondary text (neutral cool-gray)

# Hairline Borders
COLOR_HAIRLINE_BORDER = "rgba(255, 255, 255, 0.08)"
COLOR_HAIRLINE_BORDER_HEX = "#26262B"

# ==============================================================================
# TYPOGRAPHY & RESTRICTED SCOPING
# ==============================================================================
FONT_HEADLINE = "'Space Grotesk', 'Bricolage Grotesque', sans-serif"
FONT_TELEMETRY = "'JetBrains Mono', 'Space Mono', 'Courier New', monospace"
FONT_BODY = "'General Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif"

# Type Scale (px)
TYPE_SCALE_MICRO = 12       # Micro-label / section header
TYPE_SCALE_BODY = 14        # Body / UI default
TYPE_SCALE_EMPHASIZED = 16  # Emphasized body / button
TYPE_SCALE_SECTION = 20     # Section header
TYPE_SCALE_TITLE = 28       # Screen title
TYPE_SCALE_HERO = 40        # Hero numeral (rare, Live screen only)

# ==============================================================================
# SPACING SCALE (Strict 8px multiples)
# ==============================================================================
SPACING_4 = 4
SPACING_8 = 8
SPACING_12 = 12
SPACING_16 = 16
SPACING_24 = 24
SPACING_32 = 32
SPACING_48 = 48
SPACING_64 = 64

VALID_SPACING_VALUES = {4, 8, 12, 16, 24, 32, 48, 64}

# ==============================================================================
# MOTION
# ==============================================================================
DURATION_MICRO_MS = 120      # Value / label change
DURATION_COMPONENT_MS = 200  # Panel / state transition
DURATION_SCREEN_MS = 320     # Screen transition

# Single decelerating cubic-bezier curve (cubic-bezier(0.4, 0.0, 0.2, 1))
MOTION_EASING_CURVE = QEasingCurve.OutCubic
