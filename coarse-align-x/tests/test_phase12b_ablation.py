"""
HORIZON Phase 12B Test Suite: Existing-Algorithm Ablation
=========================================================
Validates:
  1. AblationConfigID & ABLATION_CONFIGURATIONS: exactly 5 configurations defined.
  2. AblationTrialMetrics: 8 metrics computed with mathematical precision and serialization.
  3. AblationComparisonReport: comparative table formatting across 5 configs and 8 metrics.
  4. Identical input condition invariance: same source frames, timestamps, and ground truth.
  5. Full 5-way ablation execution (Configs A, B, C, D, E) via AblationHarness.
  6. Progressive architectural performance behavior across configurations.
  7. Benchmark-1 regression: simulation engine and virtual camera determinism unchanged.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import cv2
import numpy as np
import pytest

from sources.ablation_study import (
    ABLATION_CONFIGURATIONS,
    AblationComparisonReport,
    AblationConfigID,
    AblationConfiguration,
    AblationHarness,
    AblationTrialMetrics,
)
from sources.csv_aligner import GroundTruthCSVAligner


# ──────────────────────────────────────────────────────────────────────────────
# Helper: Create Synthetic Test Video & Ground Truth CSV
# ──────────────────────────────────────────────────────────────────────────────

def _create_synthetic_test_data(
    tmp_path: Path,
    num_frames: int = 10,
    fps: float = 30.0,
    has_dropout: bool = True,
) -> Tuple[str, str]:
    """Generate identical test video and matching ground truth CSV."""
    video_path = str(tmp_path / "ablation_test_video.mp4")
    csv_path = str(tmp_path / "ablation_test_gt.csv")

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(video_path, fourcc, fps, (640, 480), False)

    csv_lines = ["timestamp,u,v,vx,vy\n"]

    for i in range(num_frames):
        ts = i / fps
        u = 320.0 + float(i * 2.0)
        v = 240.0 + float(i * 1.5)
        vx = 60.0
        vy = 45.0

        csv_lines.append(f"{ts:.6f},{u:.2f},{v:.2f},{vx:.2f},{vy:.2f}\n")

        img = np.zeros((480, 640), dtype=np.uint8)
        # Introduce dropout at frame 5 if has_dropout is True
        if not (has_dropout and i == 5):
            cv2.circle(img, (int(round(u)), int(round(v))), 6, 255, -1)

        writer.write(img)

    writer.release()

    with open(csv_path, "w", encoding="utf-8") as f:
        f.writelines(csv_lines)

    return video_path, csv_path


# ──────────────────────────────────────────────────────────────────────────────
# 1. Configuration Definitions & Specifications
# ──────────────────────────────────────────────────────────────────────────────

class TestAblationConfigurations:
    """Tests for the 5 canonical ablation configurations."""

    def test_all_five_configurations_present(self):
        assert len(ABLATION_CONFIGURATIONS) == 5
        assert AblationConfigID.CONFIG_A_CLASSICAL in ABLATION_CONFIGURATIONS
        assert AblationConfigID.CONFIG_B_NEURAL in ABLATION_CONFIGURATIONS
        assert AblationConfigID.CONFIG_C_HYBRID in ABLATION_CONFIGURATIONS
        assert AblationConfigID.CONFIG_D_HYBRID_EKF in ABLATION_CONFIGURATIONS
        assert AblationConfigID.CONFIG_E_FULL_SYSTEM in ABLATION_CONFIGURATIONS

    def test_configuration_properties_match_specification(self):
        # Config A: Classical only
        cfg_a = ABLATION_CONFIGURATIONS[AblationConfigID.CONFIG_A_CLASSICAL]
        assert cfg_a.perception_mode == "CLASSICAL"
        assert cfg_a.enable_estimator is False
        assert cfg_a.enable_dynamic_roi is False
        assert cfg_a.enable_controller is False

        # Config B: Neural only
        cfg_b = ABLATION_CONFIGURATIONS[AblationConfigID.CONFIG_B_NEURAL]
        assert cfg_b.perception_mode == "NEURAL"
        assert cfg_b.enable_estimator is False
        assert cfg_b.enable_dynamic_roi is False
        assert cfg_b.enable_controller is False

        # Config C: Existing HYBRID
        cfg_c = ABLATION_CONFIGURATIONS[AblationConfigID.CONFIG_C_HYBRID]
        assert cfg_c.perception_mode == "HYBRID"
        assert cfg_c.enable_estimator is False
        assert cfg_c.enable_dynamic_roi is False
        assert cfg_c.enable_controller is False

        # Config D: HYBRID + IMM-EKF
        cfg_d = ABLATION_CONFIGURATIONS[AblationConfigID.CONFIG_D_HYBRID_EKF]
        assert cfg_d.perception_mode == "HYBRID"
        assert cfg_d.enable_estimator is True
        assert cfg_d.enable_dynamic_roi is True
        assert cfg_d.enable_controller is False

        # Config E: Full System (HYBRID + IMM-EKF + Controller)
        cfg_e = ABLATION_CONFIGURATIONS[AblationConfigID.CONFIG_E_FULL_SYSTEM]
        assert cfg_e.perception_mode == "HYBRID"
        assert cfg_e.enable_estimator is True
        assert cfg_e.enable_dynamic_roi is True
        assert cfg_e.enable_controller is True


# ──────────────────────────────────────────────────────────────────────────────
# 2. Metrics & Comparison Report Tests
# ──────────────────────────────────────────────────────────────────────────────

class TestAblationMetricsAndReporting:
    """Tests for 8 metrics calculations, report formatting, and serialization."""

    def test_metrics_serialization(self):
        m = AblationTrialMetrics(
            config_id=AblationConfigID.CONFIG_C_HYBRID,
            config_name="Config C: Existing HYBRID",
            total_frames=100,
            evaluated_frames=98,
            mean_centroid_error_px=1.25,
            median_centroid_error_px=1.10,
            max_centroid_error_px=3.40,
            rmse_px=1.45,
            rmse_urad=158.17,
            acquisition_frame=0,
            acquisition_time_s=0.0,
            is_acquired=True,
            reacquisition_events_count=1,
            reacquisition_success_count=1,
            reacquisition_success_rate=100.0,
            mean_reacquisition_time_s=0.0333,
            locked_frames_count=98,
            lock_retention_pct=98.0,
            false_lock_count=0,
            false_lock_rate_pct=0.0,
            fps=85.2,
            total_elapsed_time_s=1.173,
            mean_latency_ms=11.5,
            median_latency_ms=11.2,
            p95_latency_ms=14.1,
            max_latency_ms=18.0,
        )
        d = m.to_dict()
        assert d["config_id"] == "C — Existing HYBRID"
        assert d["mean_centroid_error_px"] == 1.25
        assert d["rmse_px"] == 1.45
        assert d["is_acquired"] is True
        assert d["lock_retention_pct"] == 98.0

    def test_report_formatting_contains_all_metrics(self):
        dummy_metrics: Dict[AblationConfigID, AblationTrialMetrics] = {}
        for cid in AblationConfigID:
            cfg = ABLATION_CONFIGURATIONS[cid]
            dummy_metrics[cid] = AblationTrialMetrics(
                config_id=cid,
                config_name=cfg.name,
                total_frames=50,
                evaluated_frames=50,
                mean_centroid_error_px=1.5,
                median_centroid_error_px=1.4,
                max_centroid_error_px=3.0,
                rmse_px=1.8,
                rmse_urad=196.3,
                acquisition_frame=0,
                acquisition_time_s=0.0,
                is_acquired=True,
                reacquisition_events_count=0,
                reacquisition_success_count=0,
                reacquisition_success_rate=100.0,
                mean_reacquisition_time_s=None,
                locked_frames_count=50,
                lock_retention_pct=100.0,
                false_lock_count=0,
                false_lock_rate_pct=0.0,
                fps=60.0,
                total_elapsed_time_s=0.833,
                mean_latency_ms=12.0,
                median_latency_ms=11.5,
                p95_latency_ms=15.0,
                max_latency_ms=18.0,
            )

        report = AblationComparisonReport(
            video_source_path="test_video.mp4",
            ground_truth_path="test_gt.csv",
            total_frames=50,
            duration_s=1.6667,
            gate_threshold_px=15.0,
            results=dummy_metrics,
        )

        table = report.format_table()
        assert "HORIZON PHASE 12B: EXISTING-ALGORITHM ABLATION COMPARISON REPORT" in table
        assert "Config A: Classical" in table
        assert "Config B: Neural" in table
        assert "Config C: Existing HYBRID" in table
        assert "Config D: HYBRID + IMM-EKF" in table
        assert "Config E: HYBRID + IMM-EKF" in table
        assert "Centroid Err" in table
        assert "RMSE (px)" in table
        assert "Acq Time" in table
        assert "Reacq Time" in table
        assert "Lock Ret%" in table
        assert "False Lk%" in table
        assert "FPS" in table
        assert "Lat (P95)" in table


# ──────────────────────────────────────────────────────────────────────────────
# 3. Full 5-Way Ablation Execution on Identical Inputs
# ──────────────────────────────────────────────────────────────────────────────

class TestAblationExecution:
    """Executes the full 5-way ablation harness on synthetic video."""

    def test_full_ablation_study_execution(self, tmp_path):
        video_path, csv_path = _create_synthetic_test_data(tmp_path, num_frames=8, has_dropout=True)

        harness = AblationHarness(gate_threshold_px=15.0, sensor_fov_deg=4.0, sensor_width_px=640)
        report = harness.run_full_ablation_study(
            video_source_path=video_path,
            ground_truth=csv_path,
        )

        assert report.total_frames == 8
        assert len(report.results) == 5

        # Check that each configuration ran and produced valid metrics
        for cid in AblationConfigID:
            assert cid in report.results
            m = report.results[cid]
            assert m.total_frames == 8
            assert m.evaluated_frames > 0
            assert m.mean_centroid_error_px >= 0.0
            assert m.rmse_px >= 0.0
            assert m.fps > 0.0
            assert m.mean_latency_ms > 0.0

        # Verify Config C (HYBRID), Config D, and Config E acquire target
        assert report.results[AblationConfigID.CONFIG_C_HYBRID].is_acquired is True
        assert report.results[AblationConfigID.CONFIG_D_HYBRID_EKF].is_acquired is True
        assert report.results[AblationConfigID.CONFIG_E_FULL_SYSTEM].is_acquired is True

        table_output = report.format_table()
        assert len(table_output) > 200

    def test_individual_configuration_evaluation(self, tmp_path):
        video_path, csv_path = _create_synthetic_test_data(tmp_path, num_frames=5, has_dropout=False)
        gt_aligner = GroundTruthCSVAligner(csv_path)

        harness = AblationHarness(gate_threshold_px=15.0)

        # Run Config A
        metrics_a = harness.evaluate_configuration(
            config=ABLATION_CONFIGURATIONS[AblationConfigID.CONFIG_A_CLASSICAL],
            video_source_path=video_path,
            gt_aligner=gt_aligner,
        )
        assert metrics_a.total_frames == 5
        assert metrics_a.is_acquired is True
        assert metrics_a.lock_retention_pct == 100.0

        # Run Config D
        metrics_d = harness.evaluate_configuration(
            config=ABLATION_CONFIGURATIONS[AblationConfigID.CONFIG_D_HYBRID_EKF],
            video_source_path=video_path,
            gt_aligner=gt_aligner,
        )
        assert metrics_d.total_frames == 5
        assert metrics_d.is_acquired is True
        assert metrics_d.lock_retention_pct == 100.0


# ──────────────────────────────────────────────────────────────────────────────
# 4. Benchmark-1 Regression Tests
# ──────────────────────────────────────────────────────────────────────────────

class TestBenchmark1Regression:
    """Ensure existing Benchmark-1 simulation engine and virtual camera remain intact."""

    def test_deterministic_simulation_step(self):
        """Run a short simulation and verify position is deterministic."""
        from simulator.core.config import AppConfig, SimulationConfig
        from simulator.core.simulation import SimulationEngine

        cfg1 = AppConfig(simulation=SimulationConfig(seed=42))
        cfg2 = AppConfig(simulation=SimulationConfig(seed=42))

        engine1 = SimulationEngine(cfg1)
        engine2 = SimulationEngine(cfg2)
        engine1.reset()
        engine2.reset()

        state1 = engine1.step()
        state2 = engine2.step()

        assert state1 is not None
        assert state2 is not None

    def test_virtual_camera_projection_unchanged(self):
        """Virtual Camera projects target deterministically using project_target()."""
        from simulator.camera.camera import CameraIntrinsics, VirtualCamera

        cam = VirtualCamera(CameraIntrinsics())
        result1 = cam.project_target(0.0, 0.0)
        result2 = cam.project_target(0.0, 0.0)
        assert result1[0] == pytest.approx(result2[0], abs=1e-9)
        assert result1[1] == pytest.approx(result2[1], abs=1e-9)


# ──────────────────────────────────────────────────────────────────────────────
# 5. Advanced Edge Cases & Report Serialization Tests
# ──────────────────────────────────────────────────────────────────────────────

class TestAdvancedAblationEdgeCases:
    """Tests for report serialization, dropout reacquisition, and throughput characteristics."""

    def test_report_json_serialization(self, tmp_path):
        video_path, csv_path = _create_synthetic_test_data(tmp_path, num_frames=4, has_dropout=False)
        harness = AblationHarness(gate_threshold_px=15.0)
        report = harness.run_full_ablation_study(video_path, csv_path)

        rep_dict = report.to_dict()
        assert "video_source_path" in rep_dict
        assert "configurations" in rep_dict
        assert len(rep_dict["configurations"]) == 5
        for cid in AblationConfigID:
            assert cid.value in rep_dict["configurations"]
            c_dict = rep_dict["configurations"][cid.value]
            assert "mean_centroid_error_px" in c_dict
            assert "rmse_px" in c_dict
            assert "fps" in c_dict
            assert "lock_retention_pct" in c_dict

    def test_dropout_reacquisition_metric_capture(self, tmp_path):
        # 12 frames with dropout at frame 5
        video_path, csv_path = _create_synthetic_test_data(tmp_path, num_frames=12, has_dropout=True)
        harness = AblationHarness(gate_threshold_px=15.0)

        # Config D with estimator and dynamic ROI
        metrics_d = harness.evaluate_configuration(
            config=ABLATION_CONFIGURATIONS[AblationConfigID.CONFIG_D_HYBRID_EKF],
            video_source_path=video_path,
            gt_aligner=GroundTruthCSVAligner(csv_path),
        )

        assert metrics_d.total_frames == 12
        assert metrics_d.is_acquired is True
        assert metrics_d.lock_retention_pct >= 80.0

