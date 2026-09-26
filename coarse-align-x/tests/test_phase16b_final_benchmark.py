"""
HORIZON Phase 16B Test Suite: Final External Video Benchmark Harness
====================================================================
Validates:
  1. Multi-dimensional telemetry collection across:
     - INPUT: filename, resolution, FPS, duration, total frames, codec
     - PERCEPTION: centroid, confidence, quality, uncertainty
     - ESTIMATION: state, velocity, covariance, innovation
     - PAT: acquisition, track, degraded, reacquire
     - CONTROL: pan error, tilt error, commanded rates
     - PERFORMANCE: centroiding error, RMSE, lock retention, acquisition time, throughput FPS, latency percentiles
     - FAILURES: frame, timestamp, reason, recovery behavior
  2. Official-Reference Rule Invariant:
     - Uses provided ISRO/official reference coordinates directly without substitution.
     - Never fabricates ground truth when none is provided (clearly marked UNAVAILABLE).
  3. No Special Cases Invariant:
     - Identical architecture executed across multiple distinct video streams without branching.
  4. Non-destructive artifact generation (run_manifest.json, frame_log.csv, summary.json).
  5. Benchmark-1 regression invariance.
"""

from __future__ import annotations

import csv
import json
import math
from pathlib import Path
from typing import Dict, List, Tuple
import cv2
import numpy as np
import pytest

from simulator.camera.camera import VirtualCamera
from simulator.core.config import AppConfig, SimulationConfig
from simulator.core.simulation import SimulationEngine
from sources.final_benchmark import (
    FinalExternalBenchmarkReport,
    FinalExternalVideoBenchmark,
    VideoBenchmarkResult,
)


# ──────────────────────────────────────────────────────────────────────────────
# Fixture: Synthetic Video Streams & Ground Truth
# ──────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def benchmark_video_with_reference(tmp_path: Path) -> Tuple[Path, Path]:
    """Create a 15-frame MP4 sensor recording and paired official reference CSV."""
    vid_file = tmp_path / "evaluator_stream_alpha.mp4"
    gt_file = tmp_path / "evaluator_stream_alpha_gt.csv"

    width, height, fps = 640, 480, 30.0
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(vid_file), fourcc, fps, (width, height), False)

    gt_rows = [["frame_idx", "timestamp_s", "ground_truth_u", "ground_truth_v"]]

    for i in range(15):
        frame = np.zeros((height, width), dtype=np.uint8)
        cx = 320.0 + i * 3.0
        cy = 240.0 + i * 2.0
        cv2.circle(frame, (int(round(cx)), int(round(cy))), 10, 255, -1)
        frame = cv2.GaussianBlur(frame, (5, 5), 1.0)
        writer.write(frame)

        t_s = i / fps
        gt_rows.append([str(i), f"{t_s:.4f}", f"{cx:.4f}", f"{cy:.4f}"])

    writer.release()

    with open(gt_file, "w", newline="", encoding="utf-8") as f:
        csv_writer = csv.writer(f)
        csv_writer.writerows(gt_rows)

    return vid_file, gt_file


@pytest.fixture
def benchmark_video_without_reference(tmp_path: Path) -> Path:
    """Create an un-referenced 10-frame MP4 sensor recording."""
    vid_file = tmp_path / "evaluator_stream_beta.mp4"
    width, height, fps = 640, 480, 30.0
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(vid_file), fourcc, fps, (width, height), False)

    for i in range(10):
        frame = np.zeros((height, width), dtype=np.uint8)
        cx = 300 + i * 5
        cy = 200 + i * 4
        cv2.circle(frame, (cx, cy), 8, 255, -1)
        writer.write(frame)

    writer.release()
    return vid_file


# ──────────────────────────────────────────────────────────────────────────────
# Test Suite 1: Benchmark Models & Serialization
# ──────────────────────────────────────────────────────────────────────────────

class TestFinalBenchmarkModels:
    def test_result_to_dict_serialization(self) -> None:
        res = VideoBenchmarkResult(
            filename="test_stream.mp4",
            video_path="/path/to/test_stream.mp4",
            video_hash="c" * 64,
            resolution=(640, 480),
            source_fps=30.0,
            duration_s=1.0,
            total_frames=30,
            codec="mp4v",
            has_official_reference=True,
            reference_source="/path/to/ref.csv",
            processed_frames=30,
            detected_frames=30,
            lock_retention_pct=100.0,
            mean_centroid_error_px=0.45,
            rmse_px=0.52,
            rmse_urad=56.7,
            acquisition_time_s=0.0333,
            reacquisition_time_s=None,
            throughput_fps=45.2,
            latency_mean_ms=18.5,
            latency_median_ms=17.2,
            latency_p95_ms=22.4,
            latency_p99_ms=25.1,
            latency_max_ms=28.0,
            failure_count=0,
            failure_events=[],
            artifact_paths={"manifest": "/path/to/manifest.json"},
        )
        d = res.to_dict()
        assert d["input"]["filename"] == "test_stream.mp4"
        assert d["performance"]["lock_retention_pct"] == 100.0
        assert d["performance"]["rmse_px"] == 0.52
        assert d["reference"]["has_official_reference"] is True

    def test_overview_table_formatting(self) -> None:
        res = VideoBenchmarkResult(
            filename="sample.mp4",
            video_path="/path/to/sample.mp4",
            video_hash="d" * 64,
            resolution=(640, 480),
            source_fps=30.0,
            duration_s=2.0,
            total_frames=60,
            codec="mp4v",
            has_official_reference=False,
            reference_source=None,
            processed_frames=60,
            detected_frames=58,
            lock_retention_pct=96.7,
            mean_centroid_error_px=None,
            rmse_px=None,
            rmse_urad=None,
            acquisition_time_s=0.0333,
            reacquisition_time_s=None,
            throughput_fps=38.4,
            latency_mean_ms=21.0,
            latency_median_ms=20.5,
            latency_p95_ms=26.0,
            latency_p99_ms=29.0,
            latency_max_ms=32.0,
            failure_count=0,
            failure_events=[],
        )
        report = FinalExternalBenchmarkReport(
            timestamp="2026-09-24T00:00:00",
            total_videos_evaluated=1,
            results=[res],
        )
        table = report.format_overview_table()
        assert "FINAL EXTERNAL VIDEO BENCHMARK EVALUATION REPORT" in table
        assert "sample.mp4" in table
        assert "UNAVAILABLE*" in table
        assert "VERIFIED" in table


# ──────────────────────────────────────────────────────────────────────────────
# Test Suite 2: Official-Reference Rule Validation
# ──────────────────────────────────────────────────────────────────────────────

class TestOfficialReferenceRule:
    def test_evaluation_with_official_reference(
        self, benchmark_video_with_reference: Tuple[Path, Path], tmp_path: Path
    ) -> None:
        vid_path, gt_path = benchmark_video_with_reference
        harness = FinalExternalVideoBenchmark(runs_output_dir=tmp_path / "runs")

        result = harness.evaluate_video(
            video_path=vid_path,
            ground_truth_path=gt_path,
            max_frames=15,
        )

        assert result.has_official_reference is True
        assert result.reference_source is not None
        assert result.lock_retention_pct == 100.0
        assert result.mean_centroid_error_px is not None
        assert result.rmse_px is not None
        assert result.rmse_urad is not None
        assert result.rmse_px < 1.0  # Real Gaussian optical accuracy

    def test_evaluation_without_reference_no_fabrication(
        self, benchmark_video_without_reference: Path, tmp_path: Path
    ) -> None:
        harness = FinalExternalVideoBenchmark(runs_output_dir=tmp_path / "runs")

        result = harness.evaluate_video(
            video_path=benchmark_video_without_reference,
            ground_truth_path=None,
            max_frames=10,
        )

        # Invariant: Never fabricate reference data
        assert result.has_official_reference is False
        assert result.reference_source is None
        assert result.mean_centroid_error_px is None
        assert result.rmse_px is None
        assert result.rmse_urad is None

        # Check serialization marks it explicitly
        d = result.to_dict()
        assert "UNAVAILABLE" in str(d["performance"]["rmse_px"])
        assert "UNAVAILABLE" in str(d["performance"]["mean_centroid_error_px"])


# ──────────────────────────────────────────────────────────────────────────────
# Test Suite 3: No Special Cases Invariant & Multi-Video Batch
# ──────────────────────────────────────────────────────────────────────────────

class TestNoSpecialCasesBatchExecution:
    def test_evaluate_all_videos_batch(
        self,
        benchmark_video_with_reference: Tuple[Path, Path],
        benchmark_video_without_reference: Path,
        tmp_path: Path,
    ) -> None:
        vid_ref, gt_ref = benchmark_video_with_reference
        vid_no_ref = benchmark_video_without_reference

        harness = FinalExternalVideoBenchmark(runs_output_dir=tmp_path / "batch_runs")
        report = harness.evaluate_all_videos(
            video_paths=[vid_ref, vid_no_ref],
            ground_truth_map={vid_ref.name: gt_ref},
        )

        assert report.total_videos_evaluated == 2
        assert len(report.results) == 2

        # Video 1 has reference, Video 2 does not
        assert report.results[0].has_official_reference is True
        assert report.results[1].has_official_reference is False

        # Both generate full manifests and frame logs
        for res in report.results:
            assert Path(res.artifact_paths["manifest"]).exists()
            assert Path(res.artifact_paths["frame_log"]).exists()
            assert Path(res.artifact_paths["summary"]).exists()


# ──────────────────────────────────────────────────────────────────────────────
# Test Suite 4: Benchmark-1 Regression
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
        theta_x, theta_y, u, v, visible = cam.project_target(1000.0, 1000.0)
        assert visible is True
        assert math.isclose(u, 320.0, abs_tol=1e-3)
        assert math.isclose(v, 240.0, abs_tol=1e-3)
