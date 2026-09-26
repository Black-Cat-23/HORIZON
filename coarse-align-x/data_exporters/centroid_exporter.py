"""
HORIZON High-Precision Streaming Centroid Data Exporter
======================================================
Thread-safe CSV exporter recording estimated optical centroid positions, pixel velocities,
perception confidence, state covariance, and tracking FSM status.
"""

from __future__ import annotations

import csv
from pathlib import Path
import threading
from typing import Optional, Union
import numpy as np


class CentroidCSVExporter:
    """Thread-safe CSV exporter for logging perception & estimator centroid tracking data."""

    def __init__(self, output_path: Optional[Union[str, Path]] = None) -> None:
        self.output_path: Optional[Path] = Path(output_path) if output_path else None
        self._file = None
        self._writer = None
        self._lock = threading.Lock()
        self._count = 0

        if self.output_path:
            self.open(self.output_path)

    def open(self, output_path: Union[str, Path]) -> None:
        """Open CSV output file and write standardized header."""
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self.output_path = path

        with self._lock:
            self._file = open(path, "w", newline="", encoding="utf-8")
            self._writer = csv.writer(self._file)
            self._writer.writerow([
                "frame_idx",
                "timestamp_s",
                "est_u",
                "est_v",
                "est_vx",
                "est_vy",
                "confidence",
                "cov_uu",
                "cov_vv",
                "status",
            ])
            self._file.flush()
            self._count = 0

    def export_row(
        self,
        frame_idx: int,
        timestamp_s: float,
        est_u: float,
        est_v: float,
        est_vx: float = 0.0,
        est_vy: float = 0.0,
        confidence: float = 1.0,
        cov_uu: float = 0.0,
        cov_vv: float = 0.0,
        status: str = "TRACKING",
    ) -> None:
        """Export single centroid tracking frame sample row."""
        if self._writer is None:
            return

        with self._lock:
            self._writer.writerow([
                frame_idx,
                f"{timestamp_s:.6f}",
                f"{est_u:.4f}",
                f"{est_v:.4f}",
                f"{est_vx:.4f}",
                f"{est_vy:.4f}",
                f"{confidence:.4f}",
                f"{cov_uu:.4f}",
                f"{cov_vv:.4f}",
                status,
            ])
            self._count += 1
            if self._count % 10 == 0 and self._file:
                self._file.flush()

    def close(self) -> None:
        """Flush and close output file handle."""
        with self._lock:
            if self._file:
                self._file.flush()
                self._file.close()
                self._file = None
                self._writer = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
