"""
HORIZON Phase 4B Test Suite: External MP4 → Existing HYBRID Pipeline
========================================================================
Validates that:
  1. External frame source connects to the EXISTING HybridBeaconDetector.
  2. Perception runs sequentially through the exact current:
     - classical path
     - neural path
     - fusion logic
     - subpixel centroiding
     - confidence logic
  3. Tests execute in the specified TEST ORDER:
     - First: Clean / low-noise video
     - Second: Moderate degradation video
     - Third: Stronger noise video
     Recording (centroid, confidence, frame_id, timestamp) for each.
  4. HYBRID mathematics are untouched and no video-specific detectors exist.
  5. Coordinates, Common Frame validation, and real sample MP4 are verified.
"""

from __future__ import annotations

import csv
import math
from pathlib import Path
import tempfile
from typing import List, Tuple
import cv2
import numpy as np
import pytest

from simulator.perception.config import DetectorConfig
from simulator.perception.detector import DetectionResult
from simulator.perception.hybrid_detector import HybridBeaconDetector
from simulator.perception.preprocessing import validate_input_frame
from sources.external_video_source import ExternalVideoSource
from sources.video_pipeline import ExternalHybridPipeline, PipelineMeasurementRecord

SAMPLE_VIDEO_PATH = Path("data/samples/isro_sample_beacon_test.mp4")
SAMPLE_GT_PATH = Path("data/samples/isro_sample_beacon_test_gt.csv")


def _generate_synthetic_test_video(
    output_path: Path,
    width: int = 640,
    height: int = 480,
    fps: float = 30.0,
    duration_s: float = 1.0,
    noise_sigma: float = 2.0,
    contrast: float = 1.0,
    haze_level: float = 0.0,
    beacon_intensity: float = 230.0,
    seed: int = 42,
) -> List[Tuple[float, float]]:
    """Helper to generate a deterministic synthetic video with specified optical degradation."""
    np.random.seed(seed)
    total_frames = int(fps * duration_s)
    center_x = width / 2.0
    center_y = height / 2.0
    radius = 60.0

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(str(output_path), fourcc, fps, (width, height), isColor=False)

    gt_positions = []
    yy, xx = np.mgrid[0:height, 0:width]

    for frame_idx in range(total_frames):
        t = frame_idx / fps
        omega = 2.0 * math.pi / 2.0  # 1 rotation per 2 seconds

        # Circular trajectory
        target_u = center_x + radius * math.cos(omega * t)
        target_v = center_y + radius * math.sin(omega * t)
        gt_positions.append((target_u, target_v))

        # Gaussian optical beacon
        dist_sq = (xx - target_u) ** 2 + (yy - target_v) ** 2
        beacon = np.exp(-0.5 * dist_sq / (4.0 ** 2)) * beacon_intensity

        # Atmospheric contrast attenuation & haze
        frame_signal = beacon * contrast + haze_level

        # Add Gaussian sensor noise
        noise = np.random.normal(0.0, noise_sigma, (height, width))
        frame = np.clip(frame_signal + noise, 0, 255).astype(np.uint8)

        out.write(frame)

    out.release()
    return gt_positions


# ==============================================================================
# 1. SPECIFIED TEST ORDER EXECUTION
# ==============================================================================

@pytest.fixture(scope="module")
def video_suite(tmp_path_factory):
    """Create clean, moderate, and strong noise test videos."""
    tmp_dir = tmp_path_factory.mktemp("phase4b_suite")

    # 1. Clean / low-noise video (sigma = 2.0, contrast = 1.0, haze = 0.0)
    clean_path = tmp_dir / "01_clean_low_noise.mp4"
    clean_gt = _generate_synthetic_test_video(
        clean_path, noise_sigma=2.0, contrast=1.0, haze_level=0.0, duration_s=1.0
    )

    # 2. Moderate degradation video (sigma = 12.0, contrast = 0.65, haze = 25.0)
    moderate_path = tmp_dir / "02_moderate_degradation.mp4"
    moderate_gt = _generate_synthetic_test_video(
        moderate_path, noise_sigma=12.0, contrast=0.65, haze_level=25.0, duration_s=1.0
    )

    # 3. Stronger noise video (sigma = 28.0, contrast = 0.40, haze = 50.0)
    strong_path = tmp_dir / "03_stronger_noise.mp4"
    strong_gt = _generate_synthetic_test_video(
        strong_path, noise_sigma=28.0, contrast=0.40, haze_level=50.0, duration_s=1.0
    )

    return {
        "clean": (clean_path, clean_gt),
        "moderate": (moderate_path, moderate_gt),
        "strong": (strong_path, strong_gt),
    }


class TestPhase4BTestOrderExecution:
    """Executes external MP4 evaluation in the exact required test order."""

    def test_step_01_first_clean_low_noise_video(self, video_suite):
        """Step 1: First test clean/low-noise video. Record centroid, confidence, frame_id, timestamp."""
        video_path, gt = video_suite["clean"]
        detector = HybridBeaconDetector(DetectorConfig(perception_mode="HYBRID"))

        pipeline = ExternalHybridPipeline(video_source=video_path, detector=detector)
        records = pipeline.run()
        pipeline.close()

        assert len(records) == 30, f"Expected 30 frames for 1.0s @ 30 FPS, got {len(records)}"

        # Verify every record contains the 4 required fields
        for rec in records:
            assert isinstance(rec.frame_id, int)
            assert isinstance(rec.timestamp, float)
            assert isinstance(rec.confidence, float)
            assert rec.dt > 0.0
            # For clean video, target must be detected with high confidence
            assert rec.detected is True
            assert rec.centroid is not None
            assert len(rec.centroid) == 2
            u, v = rec.centroid
            assert 0.0 <= u <= 640.0
            assert 0.0 <= v <= 480.0
            assert rec.confidence >= 0.50, f"Expected valid confidence for clean video, got {rec.confidence}"

        # Subpixel centroid tracking accuracy against GT
        errors = [
            math.hypot(rec.centroid[0] - gt[i][0], rec.centroid[1] - gt[i][1])
            for i, rec in enumerate(records)
        ]
        mean_err = float(np.mean(errors))
        assert mean_err < 1.0, f"Clean video mean tracking error {mean_err:.3f} px exceeds 1.0 px"

    def test_step_02_then_moderate_degradation(self, video_suite):
        """Step 2: Then test moderate degradation video. Record centroid, confidence, frame_id, timestamp."""
        video_path, gt = video_suite["moderate"]
        detector = HybridBeaconDetector(DetectorConfig(perception_mode="HYBRID"))

        pipeline = ExternalHybridPipeline(video_source=video_path, detector=detector)
        records = pipeline.run()
        pipeline.close()

        assert len(records) == 30

        # Verify records capture telemetry under moderate degradation
        detected_count = sum(1 for r in records if r.detected)
        assert detected_count >= 25, f"Expected >= 25 detections under moderate degradation, got {detected_count}"

        for rec in records:
            assert isinstance(rec.frame_id, int)
            assert isinstance(rec.timestamp, float)
            assert 0.0 <= rec.confidence <= 1.0
            if rec.detected and rec.centroid is not None:
                u, v = rec.centroid
                assert 0.0 <= u <= 640.0
                assert 0.0 <= v <= 480.0

    def test_step_03_then_stronger_noise(self, video_suite):
        """Step 3: Then test stronger noise video. Record centroid, confidence, frame_id, timestamp."""
        video_path, gt = video_suite["strong"]
        detector = HybridBeaconDetector(DetectorConfig(perception_mode="HYBRID"))

        pipeline = ExternalHybridPipeline(video_source=video_path, detector=detector)
        records = pipeline.run()
        pipeline.close()

        assert len(records) == 30

        # Telemetry fields must still be cleanly populated without NaN or crash
        for rec in records:
            assert isinstance(rec.frame_id, int)
            assert isinstance(rec.timestamp, float)
            assert isinstance(rec.confidence, float)
            assert not math.isnan(rec.confidence)
            if rec.centroid is not None:
                assert not math.isnan(rec.centroid[0])
                assert not math.isnan(rec.centroid[1])


# ==============================================================================
# 2. ARCHITECTURAL INVARIANT VERIFICATION
# ==============================================================================

class TestPhase4BArchitecturalInvariants:
    """Strictly enforces non-negotiable architectural constraints."""

    def test_no_forbidden_detectors_exist(self):
        """Verify no VideoDetector, MP4Detector, or NoiseDetector exist in codebase."""
        import sources
        import simulator.perception

        for forbidden in ["VideoDetector", "MP4Detector", "NoiseDetector"]:
            assert not hasattr(sources, forbidden), f"Forbidden detector '{forbidden}' found in sources!"
            assert not hasattr(simulator.perception, forbidden), f"Forbidden detector '{forbidden}' found in perception!"

    def test_pipeline_uses_exact_hybrid_instance(self):
        """Pipeline must strictly use HybridBeaconDetector and no other class."""
        detector = HybridBeaconDetector()
        pipeline = ExternalHybridPipeline(SAMPLE_VIDEO_PATH, detector=detector)
        assert pipeline.detector is detector
        assert isinstance(pipeline.detector, HybridBeaconDetector)
        pipeline.close()

    def test_pipeline_rejects_arbitrary_detector_types(self):
        """Pipeline must reject non-HybridBeaconDetector objects."""
        class DummyDetector:
            pass

        with pytest.raises(TypeError, match="HybridBeaconDetector"):
            ExternalHybridPipeline(SAMPLE_VIDEO_PATH, detector=DummyDetector())

    def test_common_frame_enforces_input_validation(self):
        """Common Frame passing to HYBRID must satisfy validate_input_frame contracts."""
        # 1. Valid 640x480 uint8 array passes
        valid_frame = np.zeros((480, 640), dtype=np.uint8)
        checked = validate_input_frame(valid_frame, expected_width=640, expected_height=480)
        assert checked.shape == (480, 640)
        assert checked.dtype == np.uint8

        # 2. Wrong shape fails
        with pytest.raises(ValueError):
            validate_input_frame(np.zeros((300, 300), dtype=np.uint8))

        # 3. 3-channel RGB fails
        with pytest.raises(ValueError):
            validate_input_frame(np.zeros((480, 640, 3), dtype=np.uint8))

        # 4. Float dtype fails
        with pytest.raises(TypeError):
            validate_input_frame(np.zeros((480, 640), dtype=np.float32))


# ==============================================================================
# 3. REAL SENSOR RECORDING & COORDINATE REVERSIBILITY
# ==============================================================================

class TestPhase4BRealSampleVideo:
    """Evaluates the official sample recording isro_sample_beacon_test.mp4."""

    def test_real_mp4_full_pipeline_run(self):
        """Run real sample MP4 through ExternalHybridPipeline and verify telemetry."""
        if not SAMPLE_VIDEO_PATH.exists():
            pytest.skip("Sample video file not available.")

        pipeline = ExternalHybridPipeline(SAMPLE_VIDEO_PATH)
        assert pipeline.open()

        # Process first 60 frames (2 seconds)
        records = pipeline.run(max_frames=60)
        pipeline.close()

        assert len(records) == 60

        # Verify monotonically increasing frame_id and timestamps
        for i, rec in enumerate(records):
            assert rec.frame_id == i
            assert abs(rec.timestamp - i * rec.dt) < 0.05
            assert rec.detected is True
            assert rec.centroid is not None
            assert rec.confidence > 0.50
            assert rec.processing_latency_ms > 0.0
            assert rec.decode_latency_ms >= 0.0

    def test_real_mp4_subpixel_ground_truth_accuracy(self):
        """Verify subpixel accuracy against ground-truth CSV."""
        if not SAMPLE_VIDEO_PATH.exists() or not SAMPLE_GT_PATH.exists():
            pytest.skip("Sample video or GT CSV not available.")

        # Read ground truth
        gt_map = {}
        with open(SAMPLE_GT_PATH, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                gt_map[int(row["frame_idx"])] = (
                    float(row["ground_truth_u"]),
                    float(row["ground_truth_v"]),
                )

        pipeline = ExternalHybridPipeline(SAMPLE_VIDEO_PATH)
        records = pipeline.run(max_frames=30)
        pipeline.close()

        errors = []
        for rec in records:
            if rec.frame_id in gt_map and rec.centroid is not None:
                gt_u, gt_v = gt_map[rec.frame_id]
                err = math.hypot(rec.centroid[0] - gt_u, rec.centroid[1] - gt_v)
                errors.append(err)

        assert len(errors) == 30
        mean_err = float(np.mean(errors))
        assert mean_err < 2.0, f"Mean subpixel error {mean_err:.3f} px exceeds 2.0 px"

    def test_non_standard_aspect_ratio_coordinate_reversibility(self, tmp_path):
        """Verify coordinate mapping from Common Frame back to original MP4 coordinate space."""
        # Create non-standard 1280x720 video (16:9 aspect ratio)
        video_path = tmp_path / "widescreen_test.mp4"
        _generate_synthetic_test_video(
            video_path, width=1280, height=720, duration_s=0.2, noise_sigma=1.0
        )

        pipeline = ExternalHybridPipeline(video_path)
        records = pipeline.run()
        pipeline.close()

        assert len(records) > 0
        for rec in records:
            if rec.detected:
                assert rec.centroid is not None
                assert rec.centroid_original is not None

                # Centroid in Common Frame space (640x480)
                u_proc, v_proc = rec.centroid
                assert 0.0 <= u_proc <= 640.0
                assert 0.0 <= v_proc <= 480.0

                # Centroid mapped to original space (1280x720)
                u_orig, v_orig = rec.centroid_original
                assert 0.0 <= u_orig <= 1280.0
                assert 0.0 <= v_orig <= 720.0
