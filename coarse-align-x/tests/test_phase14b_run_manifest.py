"""
HORIZON Phase 14B Test Suite: Benchmark-2 Run Manifest & Reproducibility
========================================================================
Validates:
  1. Metadata extraction (SHA-256 hash, hardware info, software info, model info, timing policy).
  2. Manifest serialization (JSON and dict serialization with numpy handling).
  3. Artifact generation:
     - run_manifest.json
     - frame_log.csv
     - summary.json
  4. Non-destructive storage:
     - Silent overwrite is prohibited when historical artifacts exist.
     - Explicit overwrite allowed when allow_overwrite=True.
  5. Execution via Benchmark2RunManager:
     - Complete pipeline run on external MP4 video.
     - Accurate results calculation and metric harvesting.
  6. Numerical reproducibility:
     - Re-running identical source & configuration yields identical/within-tolerance metrics.
     - Detects discrepancies on tampered configs or hashes.
  7. Benchmark-1 regression invariance:
     - Deterministic simulation step.
     - Virtual camera projection untouched.
"""

from __future__ import annotations

import csv
import json
import math
import os
from pathlib import Path
import tempfile
import cv2
import numpy as np
import pytest

from simulator.perception.config import DetectorConfig
from sources.external_video_source import ExternalVideoSource
from sources.run_manifest import (
    HORIZON_VERSION,
    Benchmark2RunManifest,
    Benchmark2RunManager,
    compute_file_sha256,
    generate_benchmark2_artifacts,
    get_hardware_runtime_info,
    get_model_version_info,
    get_software_version_info,
    get_timing_policy_info,
    verify_run_reproducibility,
)
from sources.video_pipeline import PipelineMeasurementRecord
from simulator.core.config import AppConfig, SimulationConfig
from simulator.core.simulation import SimulationEngine
from simulator.camera.camera import VirtualCamera




# ──────────────────────────────────────────────────────────────────────────────
# Fixture: Temporary Test MP4 Video
# ──────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def test_video(tmp_path: Path) -> Path:
    """Create a 15-frame deterministic MP4 video for benchmark testing."""
    video_path = tmp_path / "test_benchmark_video.mp4"
    width, height, fps = 640, 480, 30.0
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(video_path), fourcc, fps, (width, height), False)

    for i in range(15):
        frame = np.zeros((height, width), dtype=np.uint8)
        # Smooth motion across center
        cx = int(320 + i * 5)
        cy = int(240 + i * 3)
        cv2.circle(frame, (cx, cy), 10, 255, -1)
        writer.write(frame)

    writer.release()
    return video_path


def _make_dummy_record(frame_id: int = 0, timestamp: float = 0.0) -> PipelineMeasurementRecord:
    """Create a minimal PipelineMeasurementRecord for serialization testing."""
    return PipelineMeasurementRecord(
        frame_id=frame_id,
        timestamp=timestamp,
        dt=1.0 / 30.0,
        centroid=(320.0 + frame_id, 240.0 + frame_id),
        centroid_original=(320.0 + frame_id, 240.0 + frame_id),
        confidence=0.95,
        detected=True,
        bounding_box=(310, 230, 20, 20),
        source="HYBRID",
        agreement_state="AGREED",
        decode_latency_ms=1.5,
        processing_latency_ms=12.5,
        is_dropped=False,
        candidate_quality={"snr_db": 25.0},
        candidate_geometry={"area": 100.0},
        classical_confidence=0.92,
        neural_confidence=0.96,
        detector_agreement={"spatial_iou": 0.88},
        validity=True,
        uncertainty=(0.25, 0.25),
        innovation=(0.05, -0.05),
        innovation_mahalanobis=0.15,
        jump_classification="NONE",
        roi_bbox=(280, 200, 80, 80),
        is_roi_used=True,
        estimated_state=(320.0 + frame_id, 240.0 + frame_id),
        estimated_velocity=(5.0, 3.0),
        covariance=np.eye(4),
        model_probabilities=[0.9, 0.05, 0.05],
        pat_mode="FINE_TRACK",
        pat_state={"mode": "FINE_TRACK"},
        pan_error_deg=0.01,
        tilt_error_deg=-0.01,
        commanded_pan_rate=0.05,
        commanded_tilt_rate=-0.05,
        is_saturated=False,
        latency_breakdown_ms={"decode_ms": 1.5, "hybrid_ms": 9.0, "total_ms": 12.5},
    )


# ──────────────────────────────────────────────────────────────────────────────
# Test Suite 1: Metadata Harvesting & SHA-256 Hashing
# ──────────────────────────────────────────────────────────────────────────────

class TestManifestMetadataExtraction:
    def test_compute_file_sha256(self, tmp_path: Path) -> None:
        test_file = tmp_path / "hash_test.bin"
        test_file.write_bytes(b"HORIZON_PHASE_14B_TEST_DATA")
        h = compute_file_sha256(test_file)
        assert isinstance(h, str)
        assert len(h) == 64  # SHA-256 produces 64 hex characters

        # Non-existent file handling
        non_existent = tmp_path / "missing.bin"
        h_missing = compute_file_sha256(non_existent)
        assert "FILE_NOT_FOUND" in h_missing

    def test_get_hardware_runtime_info(self) -> None:
        hw = get_hardware_runtime_info()
        assert "platform" in hw
        assert "system" in hw
        assert "cpu_count_logical" in hw
        assert hw["cpu_count_logical"] >= 1
        assert "execution_provider" in hw

    def test_get_software_version_info(self) -> None:
        sw = get_software_version_info()
        assert sw["horizon_version"] == HORIZON_VERSION
        assert "python_version" in sw
        assert "opencv_version" in sw
        assert "numpy_version" in sw

    def test_get_model_version_info(self) -> None:
        m = get_model_version_info()
        assert m["classical_detector_version"] == "v2.0-spatial-moments"
        assert m["hybrid_fusion_version"] == "v2.0-adaptive-bayesian"
        assert m["yolo_model_architecture"] == "YOLOv8n-beacon"

    def test_get_timing_policy_info(self) -> None:
        tp = get_timing_policy_info()
        assert tp["timebase_source"] == "AUTHORITATIVE_VIDEO_TIMESTAMP"
        assert tp["timestamp_clock"] == "CONTAINER_PTS"


# ──────────────────────────────────────────────────────────────────────────────
# Test Suite 2: Artifact Generation & Non-Destructive Protection
# ──────────────────────────────────────────────────────────────────────────────

class TestArtifactGenerationAndStorage:
    def test_manifest_serialization(self) -> None:
        manifest = Benchmark2RunManifest(
            run_id="run_test_001",
            timestamp="2026-09-24T00:00:00",
            video_metadata={"video_filename": "test.mp4", "video_hash": "a" * 64, "total_frames": 10},
            processing_resolution=[640, 480],
            coordinate_transform={"scale_x": 1.0, "scale_y": 1.0},
            perception_configuration={"mode": "HYBRID"},
            estimator_configuration={"filter_type": "IMM_ADAPTIVE_EKF"},
            controller_configuration={"controller_type": "PATCameraController"},
            pat_configuration={"manager_type": "PATModeManager"},
            software_version={"horizon_version": HORIZON_VERSION},
            model_version_info={"classical_detector_version": "v2.0"},
            hardware_runtime_info={"cpu_count_logical": 8},
            timing_policy={"timebase_source": "AUTHORITATIVE_VIDEO_TIMESTAMP"},
            results={"total_frames": 10, "lock_retention_pct": 100.0, "fps": 45.0},
        )

        d = manifest.to_dict()
        assert d["run_id"] == "run_test_001"
        assert d["results"]["lock_retention_pct"] == 100.0

        j = manifest.to_json()
        parsed = json.loads(j)
        assert parsed["run_id"] == "run_test_001"

    def test_generate_artifacts_creates_all_three_files(self, tmp_path: Path) -> None:
        out_dir = tmp_path / "run_output"
        manifest = Benchmark2RunManifest(
            run_id="run_gen_test",
            timestamp="2026-09-24T00:00:00",
            video_metadata={"video_filename": "test.mp4", "video_hash": "b" * 64, "total_frames": 2},
            processing_resolution=[640, 480],
            coordinate_transform={"scale_x": 1.0, "scale_y": 1.0},
            perception_configuration={"mode": "HYBRID"},
            estimator_configuration={"filter_type": "IMM_ADAPTIVE_EKF"},
            controller_configuration={"controller_type": "PATCameraController"},
            pat_configuration={"manager_type": "PATModeManager"},
            software_version={"horizon_version": HORIZON_VERSION},
            model_version_info={"classical_detector_version": "v2.0"},
            hardware_runtime_info={"cpu_count_logical": 8},
            timing_policy={"timebase_source": "AUTHORITATIVE_VIDEO_TIMESTAMP"},
            results={"total_frames": 2, "lock_retention_pct": 100.0, "fps": 30.0},
        )

        records = [_make_dummy_record(0, 0.0), _make_dummy_record(1, 1 / 30.0)]

        paths = generate_benchmark2_artifacts(manifest, records, out_dir)
        assert paths["manifest"].is_file()
        assert paths["frame_log"].is_file()
        assert paths["summary"].is_file()

        # Check CSV content
        with open(paths["frame_log"], "r", encoding="utf-8") as f:
            reader = list(csv.DictReader(f))
            assert len(reader) == 2
            assert reader[0]["frame_id"] == "0"
            assert reader[1]["frame_id"] == "1"

        # Check summary content
        with open(paths["summary"], "r", encoding="utf-8") as f:
            summary_json = json.load(f)
            assert summary_json["run_id"] == "run_gen_test"
            assert summary_json["processed_frames"] == 2

    def test_prevent_silent_overwrite_invariant(self, tmp_path: Path) -> None:
        """Verify that attempting to overwrite existing benchmark run raises FileExistsError."""
        out_dir = tmp_path / "protected_run"
        out_dir.mkdir()
        (out_dir / "run_manifest.json").write_text("existing_manifest")

        manifest = Benchmark2RunManifest(
            run_id="run_overwrite_test",
            timestamp="2026-09-24T00:00:00",
            video_metadata={},
            processing_resolution=[640, 480],
            coordinate_transform={},
            perception_configuration={},
            estimator_configuration={},
            controller_configuration={},
            pat_configuration={},
            software_version={},
            model_version_info={},
            hardware_runtime_info={},
            timing_policy={},
            results={},
        )

        with pytest.raises(FileExistsError, match="Silent overwrite is prohibited"):
            generate_benchmark2_artifacts(manifest, [], out_dir, allow_overwrite=False)

        # But allow_overwrite=True succeeds
        paths = generate_benchmark2_artifacts(manifest, [], out_dir, allow_overwrite=True)
        assert paths["manifest"].is_file()


# ──────────────────────────────────────────────────────────────────────────────
# Test Suite 3: Benchmark2RunManager End-to-End Execution
# ──────────────────────────────────────────────────────────────────────────────

class TestBenchmark2RunManagerExecution:
    def test_execute_benchmark_run(self, test_video: Path, tmp_path: Path) -> None:
        manager = Benchmark2RunManager(runs_root=tmp_path / "benchmark_runs")
        manifest, records, paths = manager.execute_benchmark_run(
            video_path=test_video,
            max_frames=10,
        )

        assert manifest is not None
        assert len(records) == 10
        assert manifest.video_metadata["video_filename"] == "test_benchmark_video.mp4"
        assert len(manifest.video_metadata["video_hash"]) == 64
        assert manifest.results["total_frames"] == 10
        assert manifest.results["lock_retention_pct"] > 0.0
        assert manifest.results["fps"] > 0.0

        # Verify files on disk
        assert paths["manifest"].exists()
        assert paths["frame_log"].exists()
        assert paths["summary"].exists()


# ──────────────────────────────────────────────────────────────────────────────
# Test Suite 4: Numerical Reproducibility
# ──────────────────────────────────────────────────────────────────────────────

class TestRunReproducibility:
    def test_reproducible_identical_runs(self, test_video: Path, tmp_path: Path) -> None:
        manager = Benchmark2RunManager(runs_root=tmp_path / "repro_runs")

        manifest_1, _, _ = manager.execute_benchmark_run(
            video_path=test_video,
            run_id="run_trial_1",
            max_frames=8,
        )

        manifest_2, _, _ = manager.execute_benchmark_run(
            video_path=test_video,
            run_id="run_trial_2",
            max_frames=8,
        )

        is_repro, discrepancies = verify_run_reproducibility(manifest_1, manifest_2, numerical_tolerance=1e-4)
        assert is_repro, f"Runs should be reproducible, got discrepancies: {discrepancies}"
        assert len(discrepancies) == 0

    def test_discrepancy_detected_on_tampered_metadata(self, test_video: Path, tmp_path: Path) -> None:
        manager = Benchmark2RunManager(runs_root=tmp_path / "tamper_runs")
        manifest_1, _, _ = manager.execute_benchmark_run(
            video_path=test_video,
            run_id="run_orig",
            max_frames=5,
        )

        # Create tampered copy
        manifest_tampered = Benchmark2RunManifest(
            run_id="run_tampered",
            timestamp=manifest_1.timestamp,
            video_metadata=dict(manifest_1.video_metadata, video_hash="tampered_hash_123"),
            processing_resolution=manifest_1.processing_resolution,
            coordinate_transform=manifest_1.coordinate_transform,
            perception_configuration=manifest_1.perception_configuration,
            estimator_configuration=manifest_1.estimator_configuration,
            controller_configuration=manifest_1.controller_configuration,
            pat_configuration=manifest_1.pat_configuration,
            software_version=manifest_1.software_version,
            model_version_info=manifest_1.model_version_info,
            hardware_runtime_info=manifest_1.hardware_runtime_info,
            timing_policy=manifest_1.timing_policy,
            results=dict(manifest_1.results, lock_retention_pct=12.5),
        )

        is_repro, discrepancies = verify_run_reproducibility(manifest_1, manifest_tampered)
        assert not is_repro
        assert any("Video hash mismatch" in d for d in discrepancies)
        assert any("lock_retention_pct" in d for d in discrepancies)


# ──────────────────────────────────────────────────────────────────────────────
# Test Suite 5: Benchmark-1 Regression
# ──────────────────────────────────────────────────────────────────────────────

class TestBenchmark1Regression:
    def test_deterministic_simulation_step(self) -> None:
        cfg = AppConfig(simulation=SimulationConfig(seed=42))
        engine = SimulationEngine(config=cfg)
        engine.initialize()
        frame_1 = engine.step()
        frame_2 = engine.step()
        assert frame_1 is not None
        assert frame_2 is not None
        assert engine.clock.current_frame == 2


    def test_virtual_camera_projection_unchanged(self) -> None:
        cam = VirtualCamera()
        # World center is at (1000.0, 1000.0) for default world_width=2000, world_height=2000
        theta_x, theta_y, u, v, visible = cam.project_target(1000.0, 1000.0)
        assert visible is True
        assert math.isclose(u, 320.0, abs_tol=1e-3)
        assert math.isclose(v, 240.0, abs_tol=1e-3)

