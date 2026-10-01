"""
HORIZON Universal Resource & Path Resolution Module
=====================================================
Provides universal path resolution for both standard Python development 
environments and PyInstaller frozen standalone executable builds.
"""

from __future__ import annotations

import sys
from pathlib import Path


def get_base_dir() -> Path:
    """Return the absolute root base directory for application assets.
    
    When running inside a PyInstaller frozen bundle, returns sys._MEIPASS.
    Otherwise, returns the repository root directory.
    """
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent.parent.parent


def get_resource_path(relative_path: str | Path) -> Path:
    """Resolve a relative resource path to an absolute Path."""
    rel_path = Path(relative_path)
    if rel_path.is_absolute():
        return rel_path
    return get_base_dir() / rel_path
