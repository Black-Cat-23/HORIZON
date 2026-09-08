"""HORIZON Phase 11.1 — Standalone Application Shell Showcase Window.

Launcher script to verify the Phase 11.1 persistent GlobalHeader, 5-mode ModeSelectorBank,
and smooth 320ms cross-fade vertical settle screen transitions.
"""

import sys
from PySide6.QtWidgets import QApplication
from simulator.ui.shell.app_shell import ApplicationShell


def main():
    app = QApplication(sys.argv)
    window = ApplicationShell()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
