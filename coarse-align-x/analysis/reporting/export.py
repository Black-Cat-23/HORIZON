"""
Data Exporter Module
====================
Exports JSON summary files (summary.json, comparison.json, robustness.json, etc.).
"""

from __future__ import annotations
import json
from pathlib import Path
from typing import Any, Dict


class DataExporter:
    """Exports machine-readable JSON data artifacts."""

    @staticmethod
    def export_json(data: Dict[str, Any], output_path: str) -> None:
        p = Path(output_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
