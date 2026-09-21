"""HORIZON Phase 11.1 — Application Shell Package.

Exports:
    GlobalHeader: Persistent 64px top bar showing telemetry and status.
    ModeSelectorBank: 5-mode tab switcher.
    ModePlaceholderView: Placeholder content pane for unbuilt modes.
    ApplicationShell: Main application window coordinating header, switcher, and views.
"""

from simulator.ui.shell.header import GlobalHeader
from simulator.ui.shell.bank_switcher import ModeSelectorBank
from simulator.ui.shell.placeholders import ModePlaceholderView
from simulator.ui.shell.app_shell import ApplicationShell

__all__ = [
    "GlobalHeader",
    "ModeSelectorBank",
    "ModePlaceholderView",
    "ApplicationShell",
]
