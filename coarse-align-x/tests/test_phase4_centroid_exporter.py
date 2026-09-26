"""
Phase 4 Verification Suite: ISO-17025 Compliant Sub-Pixel Centroid Exporter
=============================================================================
Validates sub-pixel coordinate formatting (%.6f), SHA-256 experiment hashing,
CSV header metadata compliance, and JSON dataset output.
"""

import os
import tempfile
import json
import pytest
from export.centroid_exporter import ISO17025CentroidExporter


def test_iso17025_sha256_hash_and_subpixel_csv_export() -> None:
    """Verify SHA-256 experiment signature and %.6f precision CSV formatting."""
    exporter = ISO17025CentroidExporter(
        experiment_id="TEST_EXP_001",
        seed=12345,
        trajectory_type="circular",
        preset_name="DIFFICULT",
        fov_pan_deg=4.0,
        fov_tilt_deg=3.0,
    )

    exporter.add_entry(
        frame=0,
        timestamp_s=0.0,
        gt_u_px=320.123456,
        gt_v_px=240.654321,
        gt_vx_px_s=10.5,
        gt_vy_px_s=-5.2,
        det_u_px=320.120000,
        det_v_px=240.650000,
        det_confidence=0.98,
        est_u_px=320.122000,
        est_v_px=240.652000,
        est_vx_px_s=10.4,
        est_vy_px_s=-5.1,
        pat_mode="TRACK",
        is_saturated=False,
    )

    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        temp_csv_path = f.name

    try:
        csv_file = exporter.export_csv(temp_csv_path)
        assert csv_file.exists()

        with open(csv_file, "r", encoding="utf-8") as f_read:
            content = f_read.read()

        # Check ISO-17025 Metadata Header Block
        assert "# ISO-17025 Traceable Optical Centroid Telemetry Export" in content
        assert "TEST_EXP_001" in content
        assert "SHA-256 Signature:" in content
        # Check %.6f precision formatting
        assert "320.123456" in content
        assert "240.654321" in content
    finally:
        if os.path.exists(temp_csv_path):
            os.remove(temp_csv_path)


def test_iso17025_json_export() -> None:
    """Verify structured JSON dataset export."""
    exporter = ISO17025CentroidExporter(
        experiment_id="TEST_EXP_JSON",
        seed=999,
        trajectory_type="straight",
    )

    exporter.add_entry(
        frame=1,
        timestamp_s=0.016667,
        gt_u_px=321.0,
        gt_v_px=241.0,
        gt_vx_px_s=0.0,
        gt_vy_px_s=0.0,
        det_u_px=321.0,
        det_v_px=241.0,
        det_confidence=1.0,
        est_u_px=321.0,
        est_v_px=241.0,
        est_vx_px_s=0.0,
        est_vy_px_s=0.0,
    )

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        temp_json_path = f.name

    try:
        json_file = exporter.export_json(temp_json_path)
        assert json_file.exists()

        with open(json_file, "r", encoding="utf-8") as f_read:
            data = json.load(f_read)

        assert data["metadata"]["experiment_id"] == "TEST_EXP_JSON"
        assert len(data["records"]) == 1
        assert data["records"][0]["gt_u_px"] == 321.0
    finally:
        if os.path.exists(temp_json_path):
            os.remove(temp_json_path)
