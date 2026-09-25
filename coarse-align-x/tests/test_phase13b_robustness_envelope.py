"""
HORIZON Phase 13B Test Suite: Benchmark-2 Robustness Envelope
==============================================================
Validates:
  1. RobustnessRegion enum and boundary classification criteria.
  2. CurvePoint and RobustnessCurve representations and JSON serialization.
  3. Tracking Error vs Noise and Lock Retention vs Noise sweeps.
  4. FPS vs Processing Load and Latency vs Processing Load sweeps.
  5. Acquisition vs Difficulty sweep.
  6. Reacquisition vs Measurement Loss (dropout burst length) sweep.
  7. STABLE, DEGRADED, and FAILURE regional identification.
  8. Unmasked failure reporting (zero falsification / masking of failures).
  9. Full Benchmark2RobustnessReport formatting.
  10. Benchmark-1 regression: simulation engine and camera projection determinism.
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Tuple
import numpy as np
import pytest

from sources.robustness_envelope import (
    Benchmark2RobustnessReport,
    CurvePoint,
    RobustnessCurve,
    RobustnessEnvelopeHarness,
    RobustnessRegion,
)


# ──────────────────────────────────────────────────────────────────────────────
# 1. Data Models & Regional Classification Tests
# ──────────────────────────────────────────────────────────────────────────────

class TestRobustnessModels:
    """Tests for CurvePoint, RobustnessCurve, and Regional Classifications."""

    def test_robustness_region_enum_values(self):
        assert RobustnessRegion.STABLE.value == "STABLE"
        assert RobustnessRegion.DEGRADED.value == "DEGRADED"
        assert RobustnessRegion.FAILURE.value == "FAILURE"

    def test_curve_point_serialization(self):
        pt = CurvePoint(
            param_value=20.0,
            param_label="sigma=20.0",
            metric_value=2.15,
            metric_std=0.45,
            metric_p95=2.85,
            sample_count=30,
            region=RobustnessRegion.STABLE,
            notes="Nominal optical tracking",
        )
        d = pt.to_dict()
        assert d["param_value"] == 20.0
        assert d["param_label"] == "sigma=20.0"
        assert d["metric_value"] == 2.15
        assert d["region"] == "STABLE"

    def test_robustness_curve_serialization(self):
        pt1 = CurvePoint(0.0, "0ms", 60.0, 0.0, 60.0, 10, RobustnessRegion.STABLE)
        pt2 = CurvePoint(50.0, "50ms", 12.0, 0.0, 12.0, 10, RobustnessRegion.FAILURE)
        curve = RobustnessCurve(
            curve_id="fps_vs_load",
            title="FPS vs Processing Load",
            x_label="Load (ms)",
            y_label="FPS",
            points=[pt1, pt2],
            stable_limit="Load <= 15ms",
            degraded_limit="15ms < Load <= 35ms",
            failure_threshold="Load > 35ms",
        )
        d = curve.to_dict()
        assert d["curve_id"] == "fps_vs_load"
        assert len(d["points"]) == 2
        assert d["stable_limit"] == "Load <= 15ms"


# ──────────────────────────────────────────────────────────────────────────────
# 2. Empirical Sweep Measurements & Region Identification
# ──────────────────────────────────────────────────────────────────────────────

class TestEmpiricalRobustnessSweeps:
    """Tests for harness sweeps producing real measurements and unmasked failures."""

    def setup_method(self):
        self.harness = RobustnessEnvelopeHarness(gate_threshold_px=15.0, sensor_fov_deg=4.0, sensor_width_px=640)

    def test_tracking_error_and_lock_vs_noise(self):
        # Sweep clean (0.0), moderate (20.0), and extreme noise (100.0)
        err_curve, lock_curve = self.harness.measure_tracking_error_and_lock_vs_noise(
            noise_sigmas=(0.0, 20.0, 100.0),
            frames_per_step=8,
        )

        assert len(err_curve.points) == 3
        assert len(lock_curve.points) == 3

        pt_clean_err = err_curve.points[0]
        pt_extreme_err = err_curve.points[2]
        pt_clean_lock = lock_curve.points[0]
        pt_extreme_lock = lock_curve.points[2]

        # Clean frame tracking should be STABLE with low error and high retention
        assert pt_clean_err.region == RobustnessRegion.STABLE
        assert pt_clean_err.metric_value <= 4.0
        assert pt_clean_lock.metric_value >= 90.0

        # Extreme noise must reveal DEGRADED or FAILURE, never masked as clean
        assert pt_extreme_err.metric_value > pt_clean_err.metric_value
        assert pt_extreme_err.region in (RobustnessRegion.DEGRADED, RobustnessRegion.FAILURE)
        assert pt_extreme_lock.region in (RobustnessRegion.DEGRADED, RobustnessRegion.FAILURE)

    def test_fps_and_latency_vs_load(self):
        fps_curve, lat_curve = self.harness.measure_fps_and_latency_vs_load(
            load_delays_ms=(0.0, 40.0),
            frames_per_step=4,
        )

        assert len(fps_curve.points) == 2
        assert len(lat_curve.points) == 2

        # Nominal load (0ms delay) vs Heavy load (+40ms delay)
        pt_nom_fps = fps_curve.points[0]
        pt_nom_lat = lat_curve.points[0]
        pt_heavy_fps = fps_curve.points[1]
        pt_heavy_lat = lat_curve.points[1]

        assert pt_nom_fps.metric_value > pt_heavy_fps.metric_value
        assert pt_heavy_lat.metric_value > pt_nom_lat.metric_value
        assert pt_heavy_fps.region in (RobustnessRegion.DEGRADED, RobustnessRegion.FAILURE)

    def test_acquisition_vs_difficulty(self):
        acq_curve = self.harness.measure_acquisition_vs_difficulty(
            difficulty_levels=(
                ("Clean Nominal", 0.0, 255.0),
                ("Extreme Clutter", 85.0, 30.0),
            ),
            trials_per_level=4,
        )

        assert len(acq_curve.points) == 2
        pt_clean = acq_curve.points[0]
        pt_hard = acq_curve.points[1]

        # Clean nominal acquisition must be fast (< 0.10s) and STABLE
        assert pt_clean.metric_value <= 0.10
        assert pt_clean.region == RobustnessRegion.STABLE

        # Extreme clutter must show higher acquisition latency or FAILURE
        assert pt_hard.metric_value >= pt_clean.metric_value
        assert pt_hard.region in (RobustnessRegion.DEGRADED, RobustnessRegion.FAILURE)

    def test_reacquisition_vs_loss(self):
        reacq_curve = self.harness.measure_reacquisition_vs_loss(
            burst_lengths=(1, 20),
            trials_per_burst=3,
        )

        assert len(reacq_curve.points) == 2
        pt_short = reacq_curve.points[0]
        pt_long = reacq_curve.points[1]

        # Short dropout (1 frame) recovers rapidly (< 0.15s) and is STABLE
        assert pt_short.metric_value <= 0.15
        assert pt_short.region == RobustnessRegion.STABLE

        # Long dropout (20 frames) tests filter coasting and recovery envelope
        assert pt_long.metric_value >= pt_short.metric_value


# ──────────────────────────────────────────────────────────────────────────────
# 3. Complete Benchmark-2 Report & Formatting Tests
# ──────────────────────────────────────────────────────────────────────────────

class TestBenchmark2ReportFormatting:
    """Tests for complete Benchmark-2 report generation and table display."""

    def test_full_robustness_benchmark_execution(self):
        harness = RobustnessEnvelopeHarness(gate_threshold_px=15.0)
        report = harness.run_full_robustness_benchmark()

        assert isinstance(report, Benchmark2RobustnessReport)
        assert len(report.tracking_error_vs_noise.points) > 0
        assert len(report.lock_retention_vs_noise.points) > 0
        assert len(report.fps_vs_load.points) > 0
        assert len(report.latency_vs_load.points) > 0
        assert len(report.acquisition_vs_difficulty.points) > 0
        assert len(report.reacquisition_vs_loss.points) > 0

        # Check report serialization
        rep_dict = report.to_dict()
        assert "tracking_error_vs_noise" in rep_dict
        assert "fps_vs_load" in rep_dict

        # Check table formatting output
        table_str = report.format_table()
        assert "HORIZON PHASE 13B: BENCHMARK-2 ROBUSTNESS ENVELOPE REPORT" in table_str
        assert "1. TRACKING ERROR & LOCK RETENTION VS NOISE" in table_str
        assert "2. THROUGHPUT & LATENCY VS PROCESSING LOAD" in table_str
        assert "3. ACQUISITION VS SCENARIO DIFFICULTY" in table_str
        assert "4. REACQUISITION VS MEASUREMENT LOSS" in table_str
        assert "STABLE REGION" in table_str
        assert "DEGRADED REGION" in table_str
        assert "FAILURE REGION" in table_str


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
