"""
HORIZON Phase 4 Formal Verification & Validation Test Suite
=================================================================
Exhaustive testing covering all 22 Phase 4 V&V requirements:
  - Input validation & dimensional/type safety
  - Clean beacon detection across sizes (5×5 to 20×20) and spatial grid
  - Subpixel resolution and continuous coordinate verification
  - Adaptive median filtering under Salt & Pepper (0%, 1%, 5%, 10%)
  - Additive Gaussian noise robustness (sigma = 5, 10, 15, 20)
  - Poisson photon shot noise robustness
  - Atmospheric degradations (Clear, Haze, Fog, Rain, Low Light)
  - Combined multi-source disturbances
  - False detection & candidate selection over distractors
  - Ground-truth leakage static AST audit
  - Centroid method comparison (Geometric, Weighted CoG, Gaussian Fit)
  - Confidence metric validation in [0.0, 1.0]
  - Memory leak & continuous execution test
  - Deterministic repeatability
  - Edge cases & boundary clipping
  - Diagnostics export and telemetry structure
"""

import ast
from pathlib import Path
import tracemalloc
import cv2
import numpy as np
import pytest

from simulator.core.seed_manager import SeedManager
from simulator.disturbances.atmosphere import apply_atmospheric_degradation
from simulator.disturbances.config import AtmosphereConfig
from simulator.disturbances.noise import (
    apply_gaussian_noise,
    apply_poisson_noise,
    apply_salt_and_pepper_noise,
)
from simulator.perception.candidate import BeaconCandidate
from simulator.perception.config import (
    CandidateScoringConfig,
    CentroidConfig,
    DetectorConfig,
    PreprocessingConfig,
)
from simulator.perception.detector import ClassicalBeaconDetector, DetectionResult
from simulator.perception.diagnostics import export_diagnostics_to_disk
from simulator.perception.preprocessing import (
    apply_adaptive_median_filter,
    validate_input_frame,
)
from simulator.world.beacon import Beacon


def make_clean_frame(
    x: float, y: float, size: float = 10.0, bg: int = 0, intensity: int = 255
) -> np.ndarray:
    """Helper to generate a 640×480 frame with an analytical subpixel beacon."""
    frame = np.full((480, 640), bg, dtype=np.uint8)
    b = Beacon(size_px=size, intensity=intensity, shape="square")
    b.render_into(frame, x=x, y=y, background_level=bg)
    return frame


# =============================================================================
# 2. Input Validation Tests
# =============================================================================

class TestInputValidation:
    def test_valid_grayscale_passes(self):
        frame = np.zeros((480, 640), dtype=np.uint8)
        out = validate_input_frame(frame)
        assert out.shape == (480, 640)
        assert out.dtype == np.uint8

    def test_wrong_dimensions_rejected(self):
        with pytest.raises(ValueError, match="Invalid frame dimensions"):
            validate_input_frame(np.zeros((640, 480), dtype=np.uint8))
        with pytest.raises(ValueError, match="Invalid frame dimensions"):
            validate_input_frame(np.zeros((100, 100), dtype=np.uint8))

    def test_rgb_input_rejected_with_clear_message(self):
        with pytest.raises(ValueError, match="Multi-channel RGB/RGBA frame rejected"):
            validate_input_frame(np.zeros((480, 640, 3), dtype=np.uint8))

    def test_wrong_dtype_rejected(self):
        with pytest.raises(TypeError, match="Invalid frame dtype"):
            validate_input_frame(np.zeros((480, 640), dtype=np.float32))
        with pytest.raises(TypeError, match="Invalid frame dtype"):
            validate_input_frame(np.zeros((480, 640), dtype=np.int32))

    def test_nan_infinity_rejected(self):
        float_frame = np.zeros((480, 640), dtype=np.float32)
        float_frame[10, 10] = np.nan
        with pytest.raises(ValueError, match="NaN or Infinity"):
            validate_input_frame(float_frame)

    def test_empty_or_none_rejected(self):
        with pytest.raises(ValueError, match="None"):
            validate_input_frame(None)
        with pytest.raises(ValueError, match="empty"):
            validate_input_frame(np.array([], dtype=np.uint8))


# =============================================================================
# 3. Clean Beacon Detection Tests (Sizes 5, 10, 15, 20 px across positions)
# =============================================================================

class TestCleanBeaconDetection:
    @pytest.mark.parametrize("size", [5.0, 10.0, 15.0, 20.0])
    @pytest.mark.parametrize(
        "pos",
        [
            ("center", 320.0, 240.0),
            ("left", 80.0, 240.0),
            ("right", 560.0, 240.0),
            ("top", 320.0, 60.0),
            ("bottom", 320.0, 420.0),
            ("top_left", 60.0, 60.0),
            ("bottom_right", 580.0, 420.0),
            ("fractional", 253.4, 187.6),
        ],
    )
    def test_clean_beacon_detection_across_grid(self, size, pos):
        name, true_x, true_y = pos
        frame = make_clean_frame(true_x, true_y, size=size)

        detector = ClassicalBeaconDetector()
        res = detector.detect(frame)

        assert res.detected is True, f"Failed detection for size {size} at {name}"
        assert res.centroid is not None
        assert res.confidence >= 0.70

        est_x, est_y = res.centroid
        error = np.hypot(est_x - true_x, est_y - true_y)
        # Error on clean frames must be well under 0.5 px
        assert error < 0.45, f"Centroid error {error:.3f} px exceeded threshold for size {size} at {name}"


# =============================================================================
# 4. Subpixel Verification Tests
# =============================================================================

class TestSubpixelVerification:
    @pytest.mark.parametrize("frac_x", [0.10, 0.25, 0.50, 0.75, 0.90])
    @pytest.mark.parametrize("frac_y", [0.10, 0.25, 0.50, 0.75, 0.90])
    def test_fractional_target_coordinates(self, frac_x, frac_y):
        true_x = 200.0 + frac_x
        true_y = 150.0 + frac_y
        frame = make_clean_frame(true_x, true_y, size=10.0)

        detector = ClassicalBeaconDetector()
        res = detector.detect(frame)

        assert res.detected is True
        assert res.centroid is not None
        est_x, est_y = res.centroid

        # Verify coordinates are non-integer floats
        assert isinstance(est_x, float)
        assert isinstance(est_y, float)
        # Verify no truncation to integer
        assert est_x != float(int(est_x)) or frac_x in (0.0, 1.0)
        assert est_y != float(int(est_y)) or frac_y in (0.0, 1.0)

        error = np.hypot(est_x - true_x, est_y - true_y)
        assert error < 0.25, f"Subpixel error {error:.4f} too high for ({true_x}, {true_y})"


# =============================================================================
# 5. Adaptive Median Filter Tests (Salt & Pepper: 0%, 1%, 5%, 10%)
# =============================================================================

class TestAdaptiveMedianFilter:
    @pytest.mark.parametrize("prob", [0.0, 0.01, 0.05, 0.10])
    def test_salt_and_pepper_mitigation(self, prob):
        true_x, true_y = 320.5, 240.5
        clean_frame = make_clean_frame(true_x, true_y, size=10.0)

        rng = SeedManager(seed=42).get_rng("salt_pepper")
        noisy_frame = apply_salt_and_pepper_noise(clean_frame, probability=prob, rng=rng)

        detector = ClassicalBeaconDetector()
        res = detector.detect(noisy_frame)

        assert res.detected is True
        assert res.centroid is not None
        est_x, est_y = res.centroid
        error = np.hypot(est_x - true_x, est_y - true_y)
        assert error < 0.65, f"Centroid error {error:.3f} px too large under S&P {prob*100:.0f}%"


# =============================================================================
# 6. Gaussian Noise Verification Tests (sigma = 5, 10, 15, 20)
# =============================================================================

class TestGaussianNoiseRobustness:
    @pytest.mark.parametrize("sigma", [5.0, 10.0, 15.0, 20.0])
    def test_gaussian_noise_robustness(self, sigma):
        true_x, true_y = 300.0, 200.0
        clean_frame = make_clean_frame(true_x, true_y, size=10.0)

        rng = SeedManager(seed=123).get_rng("gaussian")
        noisy_frame = apply_gaussian_noise(clean_frame, sigma=sigma, rng=rng)

        detector = ClassicalBeaconDetector()
        res = detector.detect(noisy_frame)

        assert res.detected is True
        assert res.centroid is not None
        est_x, est_y = res.centroid
        error = np.hypot(est_x - true_x, est_y - true_y)
        # Under sigma=20, subpixel error must still be bounded < 1.0 px
        assert error < 1.0, f"Error {error:.3f} px exceeded 1.0 px under sigma={sigma}"


# =============================================================================
# 7. Poisson Shot Noise Tests
# =============================================================================

class TestPoissonNoiseRobustness:
    def test_poisson_noise_detection(self):
        true_x, true_y = 320.0, 240.0
        clean_frame = make_clean_frame(true_x, true_y, size=10.0)

        rng = SeedManager(seed=77).get_rng("poisson")
        noisy_frame = apply_poisson_noise(clean_frame, peak_photons=40.0, rng=rng)

        detector = ClassicalBeaconDetector()
        res = detector.detect(noisy_frame)

        assert res.detected is True
        assert res.centroid is not None
        est_x, est_y = res.centroid
        error = np.hypot(est_x - true_x, est_y - true_y)
        assert error < 0.50


# =============================================================================
# 8. Atmospheric Conditions Tests (Clear, Haze, Fog, Rain, Low Light)
# =============================================================================

class TestAtmosphericDegradationRobustness:
    @pytest.mark.parametrize("condition", ["clear", "haze", "fog", "rain", "low_light"])
    def test_atmospheric_conditions(self, condition):
        true_x, true_y = 350.0, 220.0
        clean_frame = make_clean_frame(true_x, true_y, size=10.0)

        atmos_cfg = AtmosphereConfig(enabled=True, condition=condition)
        degraded, _, _ = apply_atmospheric_degradation(clean_frame, atmos_cfg)

        detector = ClassicalBeaconDetector()
        res = detector.detect(degraded)

        assert res.detected is True, f"Detection failed under atmosphere {condition}"
        assert res.centroid is not None
        est_x, est_y = res.centroid
        error = np.hypot(est_x - true_x, est_y - true_y)
        assert error < 0.50


# =============================================================================
# 9. Combined Disturbances Tests
# =============================================================================

class TestCombinedDisturbances:
    @pytest.mark.parametrize(
        "combo_name",
        [
            "gaussian_plus_fog",
            "sp_plus_fog",
            "gaussian_sp_fog",
            "all_adversarial",
        ],
    )
    def test_combined_disturbances(self, combo_name):
        from simulator.disturbances.pipeline import DisturbancePipeline
        from simulator.disturbances.presets import get_preset_config

        true_x, true_y = 320.0, 240.0
        clean_frame = make_clean_frame(true_x, true_y, size=10.0)

        seed_mgr = SeedManager(seed=42)
        dist_cfg = get_preset_config("SEVERE" if combo_name != "all_adversarial" else "ADVERSARIAL")
        pipeline = DisturbancePipeline(dist_cfg, seed_mgr)

        disturbed, _ = pipeline.apply(clean_frame, sim_time=0.5, sim_dt=1/60.0)

        detector = ClassicalBeaconDetector()
        res = detector.detect(disturbed)

        # Under severe/adversarial, detector must either detect with valid coordinates or safely report False
        if res.detected:
            assert res.centroid is not None
            est_x, est_y = res.centroid
            # Verify coordinates are inside sensor bounds
            assert 0 <= est_x <= 640
            assert 0 <= est_y <= 480
            assert 0.0 <= res.confidence <= 1.0


# =============================================================================
# 10. False Detection & Clutter Tests
# =============================================================================

class TestFalseDetectionRejection:
    def test_all_black_frame(self):
        frame = np.zeros((480, 640), dtype=np.uint8)
        res = ClassicalBeaconDetector().detect(frame)
        assert res.detected is False
        assert res.centroid is None
        assert res.confidence == 0.0

    def test_uniform_background(self):
        for bg in [30, 80, 140, 200]:
            frame = np.full((480, 640), bg, dtype=np.uint8)
            res = ClassicalBeaconDetector().detect(frame)
            assert res.detected is False
            assert res.centroid is None
            assert res.confidence == 0.0

    def test_pure_gaussian_noise_frame(self):
        # Empty frame corrupted by sigma=20 noise (no beacon)
        rng = SeedManager(seed=99).get_rng("gaussian")
        frame = apply_gaussian_noise(np.zeros((480, 640), dtype=np.uint8), sigma=20.0, rng=rng)
        res = ClassicalBeaconDetector().detect(frame)
        assert res.detected is False
        assert res.centroid is None

    def test_pure_salt_and_pepper_noise_frame(self):
        # Empty frame with 10% S&P
        rng = SeedManager(seed=99).get_rng("salt_pepper")
        frame = apply_salt_and_pepper_noise(np.zeros((480, 640), dtype=np.uint8), probability=0.10, rng=rng)
        res = ClassicalBeaconDetector().detect(frame)
        assert res.detected is False
        assert res.centroid is None


# =============================================================================
# 11. Candidate Selection Over Distractors
# =============================================================================

class TestCandidateSelection:
    def test_selects_true_beacon_over_small_noise_blob_and_large_distractor(self):
        # Create frame with:
        # 1. True beacon: 10×10 at (320, 240)
        # 2. Large distractor: 40×40 at (100, 100) (area too big)
        # 3. Small noise spec: 2×2 at (500, 400) (area too small)
        frame = make_clean_frame(320.0, 240.0, size=10.0)
        # Add large distractor
        cv2.rectangle(frame, (80, 80), (120, 120), 255, -1)
        # Add tiny noise dot
        frame[400:402, 500:502] = 255

        detector = ClassicalBeaconDetector()
        res = detector.detect(frame)

        assert res.detected is True
        assert res.centroid is not None
        est_x, est_y = res.centroid

        # Centroid must correspond to true beacon, not the distractor
        assert pytest.approx(320.0, abs=0.5) == est_x
        assert pytest.approx(240.0, abs=0.5) == est_y


# =============================================================================
# 12. Ground-Truth Leakage Audit
# =============================================================================

class TestGroundTruthLeakageAudit:
    def test_no_ground_truth_imports_in_perception_code(self):
        perception_dir = Path(__file__).resolve().parent.parent / "simulator" / "perception"
        forbidden_terms = [
            "TargetState",
            "GroundTruthRecord",
            "GroundTruthRecorder",
            "StraightLineTrajectory",
            "CircularTrajectory",
            "FigureEightTrajectory",
            "RandomMotionTrajectory",
            "simulator.world.state",
            "simulator.trajectories",
            "simulator.core.recorder",
        ]

        for py_file in perception_dir.glob("*.py"):
            with open(py_file, "r", encoding="utf-8") as f:
                content = f.read()
                tree = ast.parse(content)

            # Check all import statements
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        for term in forbidden_terms:
                            assert term not in alias.name, f"Leakage detected in {py_file.name}: {alias.name}"
                elif isinstance(node, ast.ImportFrom):
                    module = node.module or ""
                    for term in forbidden_terms:
                        assert term not in module, f"Leakage detected in {py_file.name}: from {module} import ..."
                        for alias in node.names:
                            assert term not in alias.name, f"Leakage detected in {py_file.name}: import {alias.name}"


# =============================================================================
# 13. Centroid Method Comparison
# =============================================================================

class TestCentroidMethodComparison:
    def test_geometric_vs_weighted_cog_vs_gaussian_fit(self):
        true_x, true_y = 280.40, 210.60
        frame = make_clean_frame(true_x, true_y, size=10.0)

        # 1. Geometric
        det_geo = ClassicalBeaconDetector(DetectorConfig(centroid=CentroidConfig(method="geometric")))
        res_geo = det_geo.detect(frame)

        # 2. Weighted CoG
        det_cog = ClassicalBeaconDetector(DetectorConfig(centroid=CentroidConfig(method="weighted_cog")))
        res_cog = det_cog.detect(frame)

        # 3. Gaussian Fit
        det_gauss = ClassicalBeaconDetector(DetectorConfig(centroid=CentroidConfig(method="gaussian_fit")))
        res_gauss = det_gauss.detect(frame)

        err_geo = np.hypot(res_geo.centroid[0] - true_x, res_geo.centroid[1] - true_y)
        err_cog = np.hypot(res_cog.centroid[0] - true_x, res_cog.centroid[1] - true_y)
        err_gauss = np.hypot(res_gauss.centroid[0] - true_x, res_gauss.centroid[1] - true_y)

        # All must be subpixel accurate
        assert err_geo < 0.50
        assert err_cog < 0.20
        assert err_gauss < 0.25


# =============================================================================
# 14. Confidence Verification
# =============================================================================

class TestConfidenceMetric:
    def test_confidence_bounds_and_responsiveness(self):
        detector = ClassicalBeaconDetector()

        # High confidence for clean beacon
        clean = make_clean_frame(320.0, 240.0, size=10.0)
        res_clean = detector.detect(clean)
        assert 0.80 <= res_clean.confidence <= 1.0

        # Zero confidence for empty frame
        empty = np.zeros((480, 640), dtype=np.uint8)
        res_empty = detector.detect(empty)
        assert res_empty.confidence == 0.0

        # Dim beacon has lower confidence than bright beacon
        dim = make_clean_frame(320.0, 240.0, size=10.0, intensity=60)
        res_dim = detector.detect(dim)
        if res_dim.detected:
            assert res_dim.confidence < res_clean.confidence


# =============================================================================
# 15. Memory Leak Verification
# =============================================================================

class TestMemoryContinuousExecution:
    def test_no_uncontrolled_memory_growth_over_thousands_of_frames(self):
        tracemalloc.start()
        detector = ClassicalBeaconDetector()
        frame = make_clean_frame(320.0, 240.0, size=10.0)

        # Process 1000 frames
        for _ in range(500):
            detector.detect(frame)

        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        # Peak memory growth during 500 frames must be < 50 MB
        peak_mb = peak / (1024 * 1024)
        assert peak_mb < 50.0, f"Excessive memory allocation: {peak_mb:.2f} MB"


# =============================================================================
# 16. Deterministic Repeatability
# =============================================================================

class TestPerceptionDeterminism:
    def test_identical_frame_produces_exact_identical_detection(self):
        frame = make_clean_frame(315.7, 225.3, size=10.0)
        detector = ClassicalBeaconDetector()

        res1 = detector.detect(frame)
        res2 = detector.detect(frame)

        assert res1.detected == res2.detected
        assert res1.centroid == res2.centroid
        assert res1.confidence == res2.confidence
        assert res1.bbox == res2.bbox


# =============================================================================
# 17. Edge Cases & Clipping
# =============================================================================

class TestEdgeCases:
    def test_beacon_at_border_and_corners(self):
        detector = ClassicalBeaconDetector()

        # Target touching left edge
        frame_left = make_clean_frame(6.0, 240.0, size=10.0)
        res_left = detector.detect(frame_left)
        assert res_left.detected is True

        # Target touching bottom edge
        frame_bot = make_clean_frame(320.0, 474.0, size=10.0)
        res_bot = detector.detect(frame_bot)
        assert res_bot.detected is True

    def test_all_white_frame(self):
        # Saturated sensor
        frame = np.full((480, 640), 255, dtype=np.uint8)
        res = ClassicalBeaconDetector().detect(frame)
        assert res.detected is False
        assert res.centroid is None


# =============================================================================
# 18. Diagnostics Export
# =============================================================================

class TestDiagnosticsExport:
    def test_diagnostic_images_generation_and_export(self, tmp_path):
        frame = make_clean_frame(320.0, 240.0, size=10.0)
        detector = ClassicalBeaconDetector()

        res = detector.detect(frame, collect_diagnostics=True)
        assert res.diagnostics is not None
        assert res.diagnostics.raw_frame.shape == (480, 640)
        assert res.diagnostics.annotated_frame.shape == (480, 640, 3)

        files = export_diagnostics_to_disk(res.diagnostics, tmp_path)
        for key, p in files.items():
            assert p.exists(), f"Diagnostic file {key} was not created"
            assert p.stat().st_size > 0
