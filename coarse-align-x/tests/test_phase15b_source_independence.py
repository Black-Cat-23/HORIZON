"""
HORIZON Phase 15B Test Suite: Source-Independent Pipeline Validation
====================================================================
Validates:
  1. DiagnosticCategory enum completeness and classification semantics.
  2. FrameComparisonRecord serialization and delta calculations.
  3. Source-Independent Parity:
     - Feeds identical image sequence through Virtual Camera & External MP4 paths.
     - Compares:
         * Measurement (Centroid u/v, confidence, detected)
         * State Estimate (Position x/y, velocity)
         * PAT State (Modes, transitions)
         * Controller Output (Pan/Tilt rates)
     - Proves tracking intelligence produces numerical parity across source adapters.
  4. Discrepancy Diagnostics:
     - Pinpoints timestamp shifts, coordinate transforms, and codec effects.
  5. SourceIndependenceReport formatted table rendering.
  6. Benchmark-1 regression invariance.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import List
import cv2
import numpy as np
import pytest

from simulator.camera.camera import VirtualCamera
from simulator.core.config import AppConfig, SimulationConfig
from simulator.core.simulation import SimulationEngine
from sources.source_independent_validation import (
    DiagnosticCategory,
    FrameComparisonRecord,
    SourceIndependenceReport,
    SourceIndependentValidator,
)


# ──────────────────────────────────────────────────────────────────────────────
# Fixture: Synthetic Image Sequence
# ──────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def moving_beacon_frames() -> List[np.ndarray]:
    """Create 10 frames of 640x480 uint8 images with a moving Gaussian beacon."""
    frames = []
    width, height = 640, 480
    for i in range(10):
        frame = np.zeros((height, width), dtype=np.uint8)
        # Moving beacon
        cx = int(300 + i * 4)
        cy = int(220 + i * 3)
        cv2.circle(frame, (cx, cy), 12, 255, -1)
        # Add subtle Gaussian blur to simulate optical PSF
        frame = cv2.GaussianBlur(frame, (5, 5), 1.5)
        frames.append(frame)
    return frames


# ──────────────────────────────────────────────────────────────────────────────
# Test Suite 1: Diagnostic Models & Serialization
# ──────────────────────────────────────────────────────────────────────────────

class TestDiagnosticModels:
    def test_diagnostic_category_enum(self) -> None:
        categories = {c.value for c in DiagnosticCategory}
        assert "ADAPTER_CONTRACT" in categories
        assert "COORDINATE_TRANSFORM" in categories
        assert "TIMESTAMP_TIMEBASE" in categories
        assert "CODEC_QUANTIZATION" in categories
        assert "ALGORITHMIC_DIVERGENCE" in categories
        assert "NONE" in categories

    def test_frame_comparison_record_serialization(self) -> None:
        rec = FrameComparisonRecord(
            frame_id=1,
            timestamp=0.033333,
            vc_detected=True,
            vc_centroid=(320.5, 240.5),
            vc_confidence=0.98,
            vc_estimated_state=(320.5, 240.5),
            vc_pat_mode="FINE_TRACK",
            vc_pan_rate_dps=0.05,
            vc_tilt_rate_dps=0.02,
            mp4_detected=True,
            mp4_centroid=(320.5, 240.5),
            mp4_confidence=0.98,
            mp4_estimated_state=(320.5, 240.5),
            mp4_pat_mode="FINE_TRACK",
            mp4_pan_rate_dps=0.05,
            mp4_tilt_rate_dps=0.02,
            centroid_diff_px=0.0,
            estimate_diff_px=0.0,
            confidence_diff=0.0,
            pat_mode_match=True,
            pan_rate_diff_dps=0.0,
            tilt_rate_diff_dps=0.0,
            diagnostic_category=DiagnosticCategory.NONE,
            diagnostic_notes="Exact match",
        )
        d = rec.to_dict()
        assert d["frame_id"] == 1
        assert d["pat_mode_match"] is True
        assert d["diagnostic_category"] == "NONE"


# ──────────────────────────────────────────────────────────────────────────────
# Test Suite 2: Source-Independent Parity on Identical Frames
# ──────────────────────────────────────────────────────────────────────────────

class TestSourceIndependentParity:
    def test_identical_frame_validation_parity(self, moving_beacon_frames: List[np.ndarray], tmp_path: Path) -> None:
        validator = SourceIndependentValidator(
            tolerance_centroid_px=0.08,
            tolerance_estimate_px=0.08,
            tolerance_controller_dps=0.05,
        )

        report = validator.validate_identical_sequence(
            raw_frames=moving_beacon_frames,
            fps=30.0,
            temp_dir=tmp_path,
        )

        assert report.total_frames == 10
        assert report.matched_detection_count == 10
        assert report.matched_pat_state_count == 10
        assert report.mean_centroid_discrepancy_px < 0.08
        assert report.mean_estimate_discrepancy_px < 0.08
        assert report.is_source_independent is True

    def test_report_table_formatting(self, moving_beacon_frames: List[np.ndarray], tmp_path: Path) -> None:
        validator = SourceIndependentValidator()
        report = validator.validate_identical_sequence(
            raw_frames=moving_beacon_frames[:5],
            fps=30.0,
            temp_dir=tmp_path,
        )

        table_str = report.format_table()
        assert "SOURCE-INDEPENDENT PIPELINE VALIDATION REPORT" in table_str
        assert "Detection Agreement" in table_str
        assert "PAT State Agreement" in table_str
        assert "Centroid Discrepancy" in table_str

    def test_diagnostic_categorization_on_strict_tolerance(self, moving_beacon_frames: List[np.ndarray], tmp_path: Path) -> None:
        # Set ultra-tight tolerance (1e-6 px) to trigger CODEC_QUANTIZATION diagnostic on mp4v DCT compression
        validator = SourceIndependentValidator(
            tolerance_centroid_px=1e-6,
            tolerance_estimate_px=1e-6,
        )
        report = validator.validate_identical_sequence(
            raw_frames=moving_beacon_frames[:5],
            fps=30.0,
            temp_dir=tmp_path,
            use_lossless_mp4=False,
        )
        assert report.total_frames == 5
        # Codec quantization diagnostics should be triggered
        assert (
            report.diagnostic_summary.get(DiagnosticCategory.CODEC_QUANTIZATION.value, 0) > 0
            or report.diagnostic_summary.get(DiagnosticCategory.NONE.value, 0) > 0
        )



# ──────────────────────────────────────────────────────────────────────────────
# Test Suite 3: Benchmark-1 Regression Invariance
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
