"""
Table Formatter Module
======================
Generates programmatically formatted CSV summary tables.
"""

from __future__ import annotations
import csv
from pathlib import Path
from typing import Any, Dict, List


class TableFormatter:
    """Emits 9 report-ready CSV summary tables."""

    @staticmethod
    def export_csv_table(headers: List[str], rows: List[List[Any]], output_path: str) -> None:
        p = Path(output_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(headers)
            writer.writerows(rows)
