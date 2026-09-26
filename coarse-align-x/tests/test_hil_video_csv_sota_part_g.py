"""Unit tests for Phase G: Video Ingestion, CSV Alignment, Centroid Exporter & HIL Interface SOTA Upgrades."""

import math
import tempfile
from pathlib import Path
import numpy as np
import pytest

from control.hil_simulator import HILLatencySimulator
from control.hil_telemetry import UDPTelemetryAdapter
from data_exporters.centroid_exporter import CentroidCSVExporter
from sources.csv_aligner import GroundTruthCSVAligner, GroundTruthSample


def test_ground_truth_csv_aligner():
    """Verify GroundTruthCSVAligner parsing and spline interpolation."""
    with tempfile.NamedTemporaryFile("w", delete=False, suffix=".csv") as tmp:
        tmp.write("timestamp,true_x,true_y\n")
        tmp.write("0.0,100.0,200.0\n")
        tmp.write("0.1,110.0,205.0\n")
        tmp.write("0.2,120.0,210.0\n")
        tmp_path = tmp.name

    aligner = GroundTruthCSVAligner(tmp_path)
    assert aligner.is_loaded

    sample = aligner.get_aligned_sample(timestamp=0.05)
    assert isinstance(sample, GroundTruthSample)
    assert abs(sample.u - 105.0) < 0.5
    assert abs(sample.v - 202.5) < 0.5
    assert sample.vx > 0.0


def test_centroid_csv_exporter():
    """Verify CentroidCSVExporter file output formatting and thread safety."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        out_path = Path(tmp_dir) / "centroids.csv"

        with CentroidCSVExporter(out_path) as exporter:
            exporter.export_row(
                frame_idx=1,
                timestamp_s=0.033,
                est_u=320.5,
                est_v=240.2,
                est_vx=10.0,
                est_vy=-5.0,
                confidence=0.98,
                status="TRACKING",
            )

        assert out_path.exists()
        lines = out_path.read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) == 2
        assert "frame_idx,timestamp_s,est_u" in lines[0]
        assert "1,0.033000,320.5000,240.2000" in lines[1]


def test_udp_telemetry_adapter_binary_packing():
    """Verify UDPTelemetryAdapter binary packing and CRC32 checksum verification."""
    packet = UDPTelemetryAdapter.pack_rate_command(pan_rate_deg_s=12.5, tilt_rate_deg_s=-8.4)
    assert len(packet) == 22

    # Unpack valid packet (header 0xAA, msg_id 0x01)
    res = UDPTelemetryAdapter.unpack_telemetry_feedback(packet)
    assert res is not None
    pan, tilt, pan_rate, tilt_rate = res
    assert abs(pan - 12.5) < 1e-4
    assert abs(tilt - (-8.4)) < 1e-4

    # Corrupt packet payload
    corrupted_packet = bytearray(packet)
    corrupted_packet[5] ^= 0xFF
    assert UDPTelemetryAdapter.unpack_telemetry_feedback(bytes(corrupted_packet)) is None


def test_hil_latency_simulator():
    """Verify HILLatencySimulator stochastic transport latency and dropped packets."""
    sim = HILLatencySimulator(mean_latency_s=0.02, std_latency_s=0.001, packet_loss_prob=0.0, seed=123)

    sim.send_command(pan_rate=15.0, tilt_rate=-5.0, current_time_s=0.0)

    # Immediate retrieval before latency expires should return None
    cmd_early = sim.receive_command(current_time_s=0.005)
    assert cmd_early is None

    # Retrieval after latency expires should return command
    cmd_late = sim.receive_command(current_time_s=0.05)
    assert cmd_late is not None
    assert abs(cmd_late[0] - 15.0) < 1e-4
    assert abs(cmd_late[1] - (-5.0)) < 1e-4
