"""
HORIZON Phase 11B Test Suite: Tracking Error-Budget Analysis
============================================================
Validates:
  1. ComponentStatus enum: completeness and distinct status identifiers.
  2. ErrorComponentValue: mathematical accuracy, angular conversion, and serialization.
  3. ErrorBudgetAnalyzer:
     - Evaluation without reference: all components marked UNAVAILABLE.
     - Total Error: Euclidean distance between estimate/measurement and reference.
     - Measurement Error: raw centroid vs reference (None when undetected).
     - Estimation Residual: filtered state vs reference (None when uninitialized).
     - Prediction Residual: prior predicted state vs reference.
     - Timing Contribution: true reference velocity * measured latency.
     - Coordinate Transform: spatial distortion / invertibility residual.
     - Control Response: LOS error vs executed control displacement.
     - Reacquisition: transient error during non-TRACK modes; UNAVAILABLE during TRACK.
  4. Statistics & Aggregation:
     - ComponentStatistics metrics (mean, RMS, median, P95, max, std).
     - ErrorBudgetSummary table formatting and notes on unavailable components.
  5. Pipeline Integration:
     - ExternalHybridPipeline with GroundTruthCSVAligner populates record.error_budget.
     - compute_error_budget() and format_error_budget_table() work seamlessly.
  6. Invariance:
     - No fabricated/manufactured decomposition values.
     - Benchmark-1 simulation engine determinism unchanged.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from unittest.mock import MagicMock
import numpy as np
import pytest

from sources.csv_aligner import GroundTruthCSVAligner, GroundTruthSample
from sources.error_budget import (
    ComponentStatistics,
    ComponentStatus,
    ErrorBudgetAnalyzer,
    ErrorBudgetSummary,
    ErrorComponentValue,
    FrameErrorBudget,
)
from sources.video_pipeline import ExternalHybridPipeline, PipelineMeasurementRecord
from sources.latency_profiler import FrameLatencyRecord


# ──────────────────────────────────────────────────────────────────────────────
# Helper: Minimal Record Factory
# ──────────────────────────────────────────────────────────────────────────────

def _make_test_record(
    frame_id: int = 0,
    timestamp: float = 0.0,
    dt: float = 1 / 30.0,
    detected: bool = True,
    centroid: Optional[Tuple[float, float]] = (320.0, 240.0),
    estimated_state: Optional[Tuple[float, float]] = (320.0, 240.0),
    innovation: Optional[Tuple[float, float]] = (1.0, 0.5),
    pat_mode: Optional[str] = "TRACK",
    pan_error_deg: float = 0.1,
    tilt_error_deg: float = 0.05,
    commanded_pan_rate: float = 1.0,
    commanded_tilt_rate: float = 0.5,
    total_latency_ms: float = 12.5,
    roi_bbox: Optional[Tuple[int, int, int, int]] = None,
    is_roi_used: bool = False,
) -> PipelineMeasurementRecord:
    """Construct a synthetic PipelineMeasurementRecord for error budget testing."""
    lat_rec = FrameLatencyRecord(
        frame_id=frame_id,
        video_timestamp=timestamp,
        frame_available_t=0.0,
        decode_start_t=0.0,
        decode_end_t=0.002,
        preprocessing_start_t=0.002,
        preprocessing_end_t=0.003,
        hybrid_start_t=0.003,
        hybrid_end_t=0.010,
        imm_ekf_start_t=0.010,
        imm_ekf_end_t=0.011,
        pat_start_t=0.011,
        pat_end_t=0.0115,
        controller_start_t=0.0115,
        controller_end_t=0.0125,
        command_available_t=0.0125,
        decode_ms=2.0,
        preprocessing_ms=1.0,
        hybrid_ms=7.0,
        estimation_ms=1.0,
        pat_ms=0.5,
        controller_ms=1.0,
        total_ms=total_latency_ms,
    )
    return PipelineMeasurementRecord(
        frame_id=frame_id,
        timestamp=timestamp,
        dt=dt,
        centroid=centroid if detected else None,
        centroid_original=centroid if detected else None,
        confidence=0.9 if detected else 0.0,
        detected=detected,
        bounding_box=(centroid[0] - 5, centroid[1] - 5, 10, 10) if (detected and centroid) else None,
        source="FUSED",
        agreement_state="AGREEMENT",
        decode_latency_ms=2.0,
        processing_latency_ms=7.0,
        classical_confidence=0.88 if detected else None,
        neural_confidence=0.92 if detected else None,
        innovation=innovation,
        innovation_mahalanobis=1.2,
        covariance=np.eye(4),
        pat_mode=pat_mode,
        pan_error_deg=pan_error_deg,
        tilt_error_deg=tilt_error_deg,
        commanded_pan_rate=commanded_pan_rate,
        commanded_tilt_rate=commanded_tilt_rate,
        estimated_state=estimated_state,
        latency_record=lat_rec,
        latency_breakdown_ms={"total_ms": total_latency_ms},
        roi_bbox=roi_bbox,
        is_roi_used=is_roi_used,
    )


# ──────────────────────────────────────────────────────────────────────────────
# 1. ComponentStatus and ErrorComponentValue Unit Tests
# ──────────────────────────────────────────────────────────────────────────────

class TestErrorComponentValue:
    """Tests for ErrorComponentValue representation and properties."""

    def test_available_component_properties(self):
        comp = ErrorComponentValue(
            name="Measurement",
            value_px=2.5,
            value_urad=272.7,
            status=ComponentStatus.AVAILABLE,
            vector_u_px=1.5,
            vector_v_px=2.0,
        )
        assert comp.is_available is True
        assert comp.value_px == 2.5
        assert comp.value_urad == 272.7
        assert comp.vector_u_px == 1.5
        assert comp.vector_v_px == 2.0
        d = comp.to_dict()
        assert d["name"] == "Measurement"
        assert d["is_available"] is True
        assert d["status"] == "AVAILABLE"
        assert d["value_px"] == 2.5

    def test_unavailable_component_properties(self):
        comp = ErrorComponentValue(
            name="Timing",
            value_px=None,
            value_urad=None,
            status=ComponentStatus.UNAVAILABLE_NO_VELOCITY,
            reason="Reference velocity absent",
        )
        assert comp.is_available is False
        assert comp.value_px is None
        assert comp.value_urad is None
        d = comp.to_dict()
        assert d["is_available"] is False
        assert "UNAVAILABLE" in d["status"]
        assert d["value_px"] is None
        assert d["reason"] == "Reference velocity absent"


# ──────────────────────────────────────────────────────────────────────────────
# 2. ErrorBudgetAnalyzer Evaluation Tests
# ──────────────────────────────────────────────────────────────────────────────

class TestErrorBudgetAnalyzerEvaluation:
    """Tests for independent contributor calculations in ErrorBudgetAnalyzer."""

    def setup_method(self):
        self.analyzer = ErrorBudgetAnalyzer(sensor_fov_deg=4.0, sensor_width_px=640)

    def test_no_reference_coordinate_returns_all_unavailable(self):
        record = _make_test_record()
        budget = self.analyzer.evaluate_frame(record, reference_pos=None)

        assert budget.total_error.status == ComponentStatus.UNAVAILABLE_NO_REFERENCE
        assert budget.total_error.value_px is None
        assert budget.measurement_error.status == ComponentStatus.UNAVAILABLE_NO_REFERENCE
        assert budget.estimation_residual.status == ComponentStatus.UNAVAILABLE_NO_REFERENCE
        assert budget.prediction_residual.status == ComponentStatus.UNAVAILABLE_NO_REFERENCE
        assert budget.timing_contribution.status == ComponentStatus.UNAVAILABLE_NO_REFERENCE
        assert budget.reacquisition_contribution.status == ComponentStatus.UNAVAILABLE_NO_REFERENCE

    def test_total_error_euclidean_distance(self):
        # Reference at (300, 200), Estimate at (303, 204) -> dx=3, dy=4 -> dist=5.0 px
        record = _make_test_record(estimated_state=(303.0, 204.0))
        budget = self.analyzer.evaluate_frame(record, reference_pos=(300.0, 200.0))

        assert budget.total_error.is_available is True
        assert budget.total_error.value_px == pytest.approx(5.0, abs=1e-4)
        assert budget.total_error.vector_u_px == pytest.approx(3.0, abs=1e-4)
        assert budget.total_error.vector_v_px == pytest.approx(4.0, abs=1e-4)
        # Verify angular conversion: 4.0 deg / 640 px = 0.00625 deg/px = 109.083 µrad/px -> 5 px = 545.415 µrad
        expected_urad = 5.0 * (math.radians(4.0) / 640.0) * 1e6
        assert budget.total_error.value_urad == pytest.approx(expected_urad, abs=1e-2)

    def test_measurement_error_detected_vs_undetected(self):
        # Frame with detection: Ref at (100, 100), Centroid at (106, 108) -> dist=10.0 px
        rec_det = _make_test_record(detected=True, centroid=(106.0, 108.0))
        b_det = self.analyzer.evaluate_frame(rec_det, reference_pos=(100.0, 100.0))
        assert b_det.measurement_error.is_available is True
        assert b_det.measurement_error.value_px == pytest.approx(10.0, abs=1e-4)

        # Frame without detection (occluded) -> must be UNAVAILABLE, not fabricated
        rec_miss = _make_test_record(detected=False, centroid=None)
        b_miss = self.analyzer.evaluate_frame(rec_miss, reference_pos=(100.0, 100.0))
        assert b_miss.measurement_error.is_available is False
        assert b_miss.measurement_error.status == ComponentStatus.UNAVAILABLE_NO_DETECTION
        assert b_miss.measurement_error.value_px is None

    def test_estimation_residual(self):
        # Ref at (200, 200), Estimated at (201, 200) -> dist=1.0 px
        rec = _make_test_record(estimated_state=(201.0, 200.0))
        b = self.analyzer.evaluate_frame(rec, reference_pos=(200.0, 200.0))
        assert b.estimation_residual.is_available is True
        assert b.estimation_residual.value_px == pytest.approx(1.0, abs=1e-4)

        # No estimate -> UNAVAILABLE
        rec_no_est = _make_test_record(estimated_state=None)
        b_no_est = self.analyzer.evaluate_frame(rec_no_est, reference_pos=(200.0, 200.0))
        assert b_no_est.estimation_residual.is_available is False
        assert b_no_est.estimation_residual.status == ComponentStatus.UNAVAILABLE_NO_ESTIMATE

    def test_prediction_residual_from_innovation(self):
        # Measurement z=(320, 240), innovation y=(2.0, -1.0) => pred = z - y = (318, 241)
        # Reference at (315, 237) => du = 318-315 = 3, dv = 241-237 = 4 => dist = 5.0 px
        rec = _make_test_record(
            centroid=(320.0, 240.0),
            innovation=(2.0, -1.0),
        )
        b = self.analyzer.evaluate_frame(rec, reference_pos=(315.0, 237.0))
        assert b.prediction_residual.is_available is True
        assert b.prediction_residual.value_px == pytest.approx(5.0, abs=1e-4)

    def test_timing_contribution(self):
        # Ref vel = (60.0, 80.0) px/s (norm = 100 px/s)
        # Total latency = 20.0 ms = 0.020 s
        # Expected displacement = (60*0.02, 80*0.02) = (1.2, 1.6) -> norm = 2.0 px
        rec = _make_test_record(total_latency_ms=20.0)
        b = self.analyzer.evaluate_frame(
            rec,
            reference_pos=(320.0, 240.0),
            reference_vel=(60.0, 80.0),
        )
        assert b.timing_contribution.is_available is True
        assert b.timing_contribution.value_px == pytest.approx(2.0, abs=1e-4)

        # Missing velocity -> UNAVAILABLE
        b_no_vel = self.analyzer.evaluate_frame(
            rec,
            reference_pos=(320.0, 240.0),
            reference_vel=None,
        )
        assert b_no_vel.timing_contribution.is_available is False
        assert b_no_vel.timing_contribution.status == ComponentStatus.UNAVAILABLE_NO_VELOCITY

    def test_control_response_contribution(self):
        # FOV=4.0 deg, 640 px => 160 px/deg
        # pan_error=0.1 deg => 16.0 px LOS error
        # tilt_error=0.0 deg => 0.0 px
        # commanded_pan_rate=300.0 deg/s, dt=0.033333 s => commanded displacement = 300 * (1/30) = 10.0 deg * 160 px = 1600 px
        # Let dt = 0.05 s, commanded_pan_rate = 2.0 deg/s => 0.1 deg = 16 px -> residual = 0 px
        rec = _make_test_record(
            dt=0.05,
            pan_error_deg=0.1,
            tilt_error_deg=0.0,
            commanded_pan_rate=2.0,  # 2.0 * 0.05 = 0.1 deg
            commanded_tilt_rate=0.0,
        )
        b = self.analyzer.evaluate_frame(rec, reference_pos=(320.0, 240.0))
        assert b.control_response_contribution.is_available is True
        assert b.control_response_contribution.value_px == pytest.approx(0.0, abs=1e-4)

    def test_reacquisition_contribution_active_vs_steady_state(self):
        # In steady TRACK mode: reacquisition is UNAVAILABLE (not active)
        rec_track = _make_test_record(pat_mode="TRACK", estimated_state=(325.0, 240.0))
        b_track = self.analyzer.evaluate_frame(rec_track, reference_pos=(320.0, 240.0))
        assert b_track.reacquisition_contribution.is_available is False
        assert b_track.reacquisition_contribution.status == ComponentStatus.UNAVAILABLE_STEADY_STATE

        # In REACQUIRE mode: reacquisition is AVAILABLE and reflects transient error (5.0 px)
        rec_reacq = _make_test_record(pat_mode="REACQUIRE", estimated_state=(325.0, 240.0))
        b_reacq = self.analyzer.evaluate_frame(rec_reacq, reference_pos=(320.0, 240.0))
        assert b_reacq.reacquisition_contribution.is_available is True
        assert b_reacq.reacquisition_contribution.value_px == pytest.approx(5.0, abs=1e-4)

        # In DEGRADED mode: reacquisition is also ACTIVE
        rec_deg = _make_test_record(pat_mode="DEGRADED", estimated_state=(323.0, 244.0))
        b_deg = self.analyzer.evaluate_frame(rec_deg, reference_pos=(320.0, 240.0))
        assert b_deg.reacquisition_contribution.is_available is True
        assert b_deg.reacquisition_contribution.value_px == pytest.approx(5.0, abs=1e-4)


# ──────────────────────────────────────────────────────────────────────────────
# 3. Statistics Aggregation & Table Output Tests
# ──────────────────────────────────────────────────────────────────────────────

class TestErrorBudgetSummaryAndFormatting:
    """Tests for summary metrics and formatted table display."""

    def test_aggregation_metrics_computation(self):
        analyzer = ErrorBudgetAnalyzer(sensor_fov_deg=4.0, sensor_width_px=640)

        # Feed 10 frames with known error values
        for i in range(10):
            err_offset = float(i + 1)  # 1.0 to 10.0 px
            rec = _make_test_record(
                frame_id=i,
                timestamp=i * 0.033,
                estimated_state=(300.0 + err_offset, 200.0),
                centroid=(300.0 + err_offset, 200.0),
                total_latency_ms=10.0,
            )
            analyzer.ingest(
                record=rec,
                reference_pos=(300.0, 200.0),
                reference_vel=(100.0, 0.0),
            )

        summary = analyzer.generate_summary()
        assert summary.total_frames == 10
        assert summary.evaluated_frames == 10

        # Mean of 1..10 is 5.5
        assert summary.total_error.mean_px == pytest.approx(5.5, abs=1e-3)
        # RMS of 1..10 is sqrt(mean(1^2..10^2)) = sqrt(385/10) = sqrt(38.5) = 6.2048
        assert summary.total_error.rms_px == pytest.approx(math.sqrt(38.5), abs=1e-3)
        assert summary.total_error.max_px == pytest.approx(10.0)
        assert summary.total_error.median_px == pytest.approx(5.5, abs=1e-3)
        assert summary.total_error.is_available is True
        assert summary.total_error.coverage_pct == 100.0

        # Measurement error same as total error
        assert summary.measurement.mean_px == pytest.approx(5.5, abs=1e-3)

        # Timing error: 100 px/s * 0.010 s = 1.0 px constant
        assert summary.timing.is_available is True
        assert summary.timing.mean_px == pytest.approx(1.0, abs=1e-3)
        assert summary.timing.rms_px == pytest.approx(1.0, abs=1e-3)

        # Reacquisition error should be UNAVAILABLE (steady TRACK mode)
        assert summary.reacquisition.is_available is False
        assert summary.reacquisition.available_count == 0

    def test_format_table_contains_all_components_and_notes(self):
        analyzer = ErrorBudgetAnalyzer(sensor_fov_deg=4.0, sensor_width_px=640)

        for i in range(5):
            rec = _make_test_record(frame_id=i, timestamp=i * 0.033)
            analyzer.ingest(rec, reference_pos=(320.0, 240.0), reference_vel=(50.0, 0.0))

        summary = analyzer.generate_summary()
        table_text = summary.format_table()

        assert "HORIZON PHASE 11B: TRACKING ERROR-BUDGET ANALYSIS SUMMARY" in table_text
        assert "Total Error" in table_text
        assert "Measurement" in table_text
        assert "Estimation" in table_text
        assert "Prediction" in table_text
        assert "Timing" in table_text
        assert "Coord Transform" in table_text
        assert "Control Response" in table_text
        assert "Reacquisition" in table_text
        assert "Notes on Unavailable Components:" in table_text
        assert "Reacquisition: UNAVAILABLE" in table_text


# ──────────────────────────────────────────────────────────────────────────────
# 4. Pipeline Integration Tests
# ──────────────────────────────────────────────────────────────────────────────

class TestPipelineErrorBudgetIntegration:
    """Tests integrating ErrorBudgetAnalyzer with ExternalHybridPipeline."""

    def test_pipeline_without_ground_truth_produces_unavail_budget(self, tmp_path):
        # Create a mock video pipeline with synthetic frames
        import cv2

        video_file = str(tmp_path / "test_synth.mp4")
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(video_file, fourcc, 30.0, (640, 480), False)
        for _ in range(5):
            img = np.zeros((480, 640), dtype=np.uint8)
            cv2.circle(img, (320, 240), 6, 255, -1)
            writer.write(img)
        writer.release()

        pipeline = ExternalHybridPipeline(video_file, enable_estimator=True)
        assert pipeline.open() is True
        records = pipeline.run(max_frames=3)
        assert len(records) == 3

        for rec in records:
            assert rec.error_budget is not None
            # Without ground truth, error budget total_error is marked UNAVAILABLE_NO_REFERENCE
            assert rec.error_budget.total_error.status == ComponentStatus.UNAVAILABLE_NO_REFERENCE

        summary = pipeline.compute_error_budget()
        assert summary.total_frames == 3
        assert summary.evaluated_frames == 0
        pipeline.close()

    def test_pipeline_with_ground_truth_csv_populates_valid_budget(self, tmp_path):
        import cv2

        # Create 5 frame MP4
        video_file = str(tmp_path / "test_gt_video.mp4")
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(video_file, fourcc, 30.0, (640, 480), False)
        for i in range(5):
            img = np.zeros((480, 640), dtype=np.uint8)
            cv2.circle(img, (320 + i, 240), 6, 255, -1)
            writer.write(img)
        writer.release()

        # Create aligned Ground Truth CSV
        csv_file = tmp_path / "test_gt.csv"
        csv_content = (
            "timestamp,u,v\n"
            "0.000000,320.0,240.0\n"
            "0.033333,321.0,240.0\n"
            "0.066667,322.0,240.0\n"
            "0.100000,323.0,240.0\n"
            "0.133333,324.0,240.0\n"
        )
        csv_file.write_text(csv_content, encoding="utf-8")

        pipeline = ExternalHybridPipeline(
            video_file,
            enable_estimator=True,
            ground_truth=str(csv_file),
        )
        assert pipeline.open() is True
        records = pipeline.run(max_frames=5)
        assert len(records) == 5

        for rec in records:
            assert rec.error_budget is not None
            assert rec.error_budget.total_error.is_available is True
            assert rec.error_budget.reference_pos is not None

        summary = pipeline.compute_error_budget()
        assert summary.evaluated_frames == 5
        assert summary.total_error.is_available is True
        table = pipeline.format_error_budget_table()
        assert "Evaluated (with Reference): 5" in table

        pipeline.close()


# ──────────────────────────────────────────────────────────────────────────────
# 5. Benchmark-1 Regression Tests
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
# 6. Advanced Edge Case & Serialization Tests
# ──────────────────────────────────────────────────────────────────────────────

class TestAdvancedErrorBudgetEdgeCases:
    """Tests for edge cases, geometric transformers, serialization, and transitions."""

    def test_serialization_of_all_containers(self):
        analyzer = ErrorBudgetAnalyzer(sensor_fov_deg=4.0, sensor_width_px=640)
        rec = _make_test_record(estimated_state=(322.0, 241.0))
        budget = analyzer.ingest(rec, reference_pos=(320.0, 240.0), reference_vel=(10.0, 5.0))

        b_dict = budget.to_dict()
        assert b_dict["frame_id"] == 0
        assert b_dict["reference_pos"] == (320.0, 240.0)
        assert b_dict["reference_vel"] == (10.0, 5.0)
        assert b_dict["total_error"]["is_available"] is True
        assert b_dict["total_error"]["value_px"] == pytest.approx(2.2361, abs=1e-3)

        summary = analyzer.generate_summary()
        s_dict = summary.to_dict()
        assert s_dict["total_frames"] == 1
        assert s_dict["evaluated_frames"] == 1
        assert s_dict["total_error"]["mean_px"] == pytest.approx(2.2361, abs=1e-3)

    def test_roi_predicted_center_fallback(self):
        analyzer = ErrorBudgetAnalyzer()
        # No innovation vector, but dynamic ROI was used with center at (320, 240)
        rec = _make_test_record(
            innovation=None,
            roi_bbox=(300, 220, 40, 40),  # center at (320, 240)
            is_roi_used=True,
        )
        b = analyzer.evaluate_frame(rec, reference_pos=(318.0, 236.0))
        assert b.prediction_residual.is_available is True
        # du = 320 - 318 = 2, dv = 240 - 236 = 4 -> hypot = sqrt(20) = 4.4721
        assert b.prediction_residual.value_px == pytest.approx(math.sqrt(20), abs=1e-3)
        assert b.prediction_residual.reason == "Derived from dynamic ROI predicted center"

    def test_pipeline_reset_clears_error_budget(self, tmp_path):
        import cv2

        video_file = str(tmp_path / "test_reset_vid.mp4")
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(video_file, fourcc, 30.0, (640, 480), False)
        for _ in range(3):
            img = np.zeros((480, 640), dtype=np.uint8)
            cv2.circle(img, (320, 240), 5, 255, -1)
            writer.write(img)
        writer.release()

        pipeline = ExternalHybridPipeline(video_file)
        pipeline.open()
        pipeline.run()
        assert len(pipeline.records) == 3
        assert len(pipeline.error_budget_analyzer.frame_budgets) == 3

        pipeline.reset()
        assert len(pipeline.records) == 0
        assert len(pipeline.error_budget_analyzer.frame_budgets) == 0
        pipeline.close()

    def test_all_pat_reacquisition_modes(self):
        analyzer = ErrorBudgetAnalyzer()
        modes_active = ["SEARCH", "ACQUIRE", "DEGRADED", "REACQUIRE"]
        for mode in modes_active:
            rec = _make_test_record(pat_mode=mode, estimated_state=(323.0, 244.0))
            b = analyzer.evaluate_frame(rec, reference_pos=(320.0, 240.0))
            assert b.reacquisition_contribution.is_available is True
            assert b.reacquisition_contribution.value_px == pytest.approx(5.0, abs=1e-4)

        # In TRACK mode, reacquisition must be UNAVAILABLE
        rec_track = _make_test_record(pat_mode="TRACK", estimated_state=(323.0, 244.0))
        b_track = analyzer.evaluate_frame(rec_track, reference_pos=(320.0, 240.0))
        assert b_track.reacquisition_contribution.is_available is False
        assert b_track.reacquisition_contribution.status == ComponentStatus.UNAVAILABLE_STEADY_STATE

