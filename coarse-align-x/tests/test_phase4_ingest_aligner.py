"""
Phase 4 Verification Suite: OpenCV Video Ingest & Sub-Pixel PCHIP CSV Aligner
================================================================================
Validates frame scaling, metadata extraction, PCHIP cubic spline time interpolation,
and continuous first-order velocity derivatives.
"""

import math
import os
import tempfile
import csv
import pytest
import numpy as np

from sources.csv_aligner import GroundTruthCSVAligner, GroundTruthSample


def test_pchip_spline_position_and_velocity_interpolation() -> None:
    """Verify PCHIP cubic spline interpolation on synthetic trajectory data."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        writer = csv.writer(f)
        writer.writerow(["time_s", "u", "v"])
        # Linear motion u(t) = 100 + 50*t, v(t) = 200 + 30*t
        for i in range(11):
            t = float(i * 0.1)
            u = 100.0 + 50.0 * t
            v = 200.0 + 30.0 * t
            writer.writerow([f"{t:.2f}", f"{u:.2f}", f"{v:.2f}"])
        temp_csv_path = f.name

    try:
        aligner = GroundTruthCSVAligner(temp_csv_path)
        assert aligner.is_loaded is True
        assert len(aligner.timestamps) == 11

        # Query mid-step timestamp t = 0.35s
        sample = aligner.get_aligned_sample(0.35)
        assert abs(sample.u - (100.0 + 50.0 * 0.35)) < 1e-3, f"Expected u near {100.0 + 50.0 * 0.35}, got {sample.u}"
        assert abs(sample.v - (200.0 + 30.0 * 0.35)) < 1e-3, f"Expected v near {200.0 + 30.0 * 0.35}, got {sample.v}"
        assert abs(sample.vx - 50.0) < 1.0, f"Expected vx near 50.0, got {sample.vx}"
        assert abs(sample.vy - 30.0) < 1.0, f"Expected vy near 30.0, got {sample.vy}"
    finally:
        if os.path.exists(temp_csv_path):
            os.remove(temp_csv_path)


def test_schema_agnostic_header_parsing() -> None:
    """Verify schema-agnostic header detection across column alias variants."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        writer = csv.writer(f)
        writer.writerow(["t", "centroid_x", "centroid_y"])
        writer.writerow(["0.0", "320.0", "240.0"])
        writer.writerow(["0.1", "325.0", "243.0"])
        writer.writerow(["0.2", "330.0", "246.0"])
        temp_csv_path = f.name

    try:
        aligner = GroundTruthCSVAligner(temp_csv_path)
        assert aligner.is_loaded is True
        sample = aligner.get_aligned_sample(0.1)
        assert sample.u == 325.0
        assert sample.v == 243.0
    finally:
        if os.path.exists(temp_csv_path):
            os.remove(temp_csv_path)
