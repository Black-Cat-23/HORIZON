"""
HORIZON Phase 5B Test Suite: Measurement Quality & Uncertainty
========================================================================
Validates that:
  1. The measurement interface exposes:
     - centroid
     - confidence
     - candidate quality
     - candidate geometry
     - classical confidence
     - neural confidence
     - detector agreement
     - validity
     - uncertainty (sigma_u, sigma_v)
     - innovation (y_u, y_v) and innovation Mahalanobis distance
  2. Uncertainty is derived strictly from measurable physical quantities:
     - Photon-noise astrometric model: sigma proportional to FWHM / (SNR * sqrt(N))
     - Multi-detector spatial discrepancy: sigma expanded in quadrature
     - Edge clipping: sigma expanded under boundary occlusion
     - Zero fabricated uncertainty
  3. The estimator receives observation trustworthiness (R covariance scaling).
  4. Temporal consistency analyzer diagnoses measurement jumps across (k-1, k, k+1):
     - HYBRID_HANDOFF
     - CANDIDATE_AMBIGUITY
     - NOISE
     - EDGE_EFFECT
     - TRUE_MOTION
     Without hiding physical motion with artificial excessive smoothing.
  5. Evaluates real external MP4 sensor recording.
"""

from __future__ import annotations

import math
from pathlib import Path
import numpy as np
import pytest

from simulator.perception.config import DetectorConfig
from simulator.perception.detector import DetectionQuality, DetectionResult
from simulator.perception.hybrid_detector import HybridBeaconDetector
from sources.external_video_source import ExternalVideoSource
from sources.temporal_consistency import JumpCause, JumpDiagnosis, TemporalConsistencyAnalyzer
from sources.video_pipeline import ExternalHybridPipeline, PipelineMeasurementRecord
from tracking.estimation.kalman import TargetKalmanFilter
from tracking.estimation.model import build_measurement_noise_matrix

SAMPLE_VIDEO_PATH = Path("data/samples/isro_sample_beacon_test.mp4")


# ==============================================================================
# 1. MEASUREMENT INTERFACE & INFORMATION EXPOSURE
# ==============================================================================

class TestMeasurementInterfaceExposure:
    """Verifies all required information fields flow out of HYBRID and pipeline."""

    def test_detection_result_exposes_quality_and_uncertainty(self):
        """DetectionResult must expose sigma_u_px, sigma_v_px, and DetectionQuality."""
        detector = HybridBeaconDetector(DetectorConfig(perception_mode="HYBRID"))

        # Generate synthetic spot frame
        frame = np.full((480, 640), 20, dtype=np.uint8)
        yy, xx = np.mgrid[0:480, 0:640]
        spot = np.exp(-0.5 * (((xx - 320.0) ** 2 + (yy - 240.0) ** 2) / (5.0 ** 2))) * 220.0
        frame = np.clip(frame + spot, 0, 255).astype(np.uint8)

        res = detector.detect(frame, timestamp=1.0, collect_diagnostics=True)

        assert res.detected is True
        assert res.centroid is not None
        assert abs(res.centroid[0] - 320.0) < 1.0
        assert abs(res.centroid[1] - 240.0) < 1.0

        # Physical uncertainty exposed
        assert hasattr(res, "sigma_u_px")
        assert hasattr(res, "sigma_v_px")
        assert 0.01 <= res.sigma_u_px <= 5.0
        assert 0.01 <= res.sigma_v_px <= 5.0

        # Quality dimensions exposed
        assert res.quality is not None
        assert isinstance(res.quality, DetectionQuality)
        assert res.quality.snr > 5.0
        assert res.quality.local_contrast > 50.0
        assert 0.0 <= res.quality.circularity <= 1.0
        assert 0.0 <= res.quality.compactness <= 1.0

    def test_pipeline_record_exposes_all_phase5b_fields(self):
        """PipelineMeasurementRecord must expose complete Phase 5B measurement fields."""
        if not SAMPLE_VIDEO_PATH.exists():
            pytest.skip("Sample video file not available.")

        pipeline = ExternalHybridPipeline(SAMPLE_VIDEO_PATH, enable_estimator=True)
        pipeline.open()

        res0 = pipeline.process_frame()
        res1 = pipeline.process_frame()
        pipeline.close()

        assert res0 is not None and res1 is not None
        rec0, _ = res0
        rec1, _ = res1

        # Core measurements
        assert rec1.centroid is not None
        assert 0.0 <= rec1.confidence <= 1.0
        assert rec1.validity is True

        # Candidate quality & geometry
        assert rec1.candidate_quality is not None
        assert "snr" in rec1.candidate_quality
        assert "local_contrast" in rec1.candidate_quality
        assert "bg_mean" in rec1.candidate_quality

        assert rec1.candidate_geometry is not None
        assert "bbox" in rec1.candidate_geometry
        assert "area_px" in rec1.candidate_geometry
        assert "clipped_by_edge" in rec1.candidate_geometry

        # Physical uncertainty
        assert rec1.uncertainty is not None
        assert len(rec1.uncertainty) == 2
        assert rec1.uncertainty[0] > 0.0
        assert rec1.uncertainty[1] > 0.0

        # Innovation when estimator engaged (computed after initialization frame)
        assert rec0.innovation is None  # Initial frame has no prior estimate
        assert rec1.innovation is not None
        assert len(rec1.innovation) == 2
        assert rec1.innovation_mahalanobis is not None

        # Jump classification
        assert rec1.jump_classification is not None


# ==============================================================================
# 2. PHYSICAL UNCERTAINTY DERIVATION (NO FABRICATION)
# ==============================================================================

class TestPhysicalUncertaintyDerivation:
    """Verifies that uncertainty is derived strictly from measurable optical quantities."""

    def test_uncertainty_scales_with_snr(self):
        """Lower SNR must naturally produce larger physical uncertainty sigma."""
        detector = HybridBeaconDetector(DetectorConfig(perception_mode="HYBRID"))
        yy, xx = np.mgrid[0:480, 0:640]

        # 1. High SNR Spot
        frame_clean = np.full((480, 640), 20, dtype=np.uint8)
        spot_bright = np.exp(-0.5 * (((xx - 320.0) ** 2 + (yy - 240.0) ** 2) / (5.0 ** 2))) * 230.0
        frame_clean = np.clip(frame_clean + spot_bright, 0, 255).astype(np.uint8)
        res_clean = detector.detect(frame_clean, timestamp=0.0)

        # 2. Low SNR Spot (faint beacon + heavy noise)
        np.random.seed(42)
        noise = np.random.normal(0, 18.0, (480, 640))
        spot_faint = np.exp(-0.5 * (((xx - 320.0) ** 2 + (yy - 240.0) ** 2) / (5.0 ** 2))) * 70.0
        frame_noisy = np.clip(30.0 + spot_faint + noise, 0, 255).astype(np.uint8)
        res_noisy = detector.detect(frame_noisy, timestamp=0.1)

        assert res_clean.detected is True
        if res_noisy.detected:
            # Physical astrometry: sigma_clean < sigma_noisy
            assert res_clean.sigma_u_px < res_noisy.sigma_u_px
            assert res_clean.quality.snr > res_noisy.quality.snr

    def test_edge_clipping_expands_uncertainty(self):
        """Spots clipped by frame boundary must reflect expanded spatial uncertainty."""
        detector = HybridBeaconDetector(DetectorConfig(perception_mode="HYBRID"))
        yy, xx = np.mgrid[0:480, 0:640]

        # Center spot (unclipped)
        frame_center = np.full((480, 640), 15, dtype=np.uint8)
        spot_c = np.exp(-0.5 * (((xx - 320.0) ** 2 + (yy - 240.0) ** 2) / (6.0 ** 2))) * 220.0
        frame_center = np.clip(frame_center + spot_c, 0, 255).astype(np.uint8)
        res_c = detector.detect(frame_center, timestamp=0.0)

        # Edge spot (center at u=3 px, severely clipped by left boundary)
        frame_edge = np.full((480, 640), 15, dtype=np.uint8)
        spot_e = np.exp(-0.5 * (((xx - 3.0) ** 2 + (yy - 240.0) ** 2) / (6.0 ** 2))) * 220.0
        frame_edge = np.clip(frame_edge + spot_e, 0, 255).astype(np.uint8)
        res_e = detector.detect(frame_edge, timestamp=0.1)

        if res_e.detected and res_e.quality:
            assert res_e.quality.clipped_by_edge is True
            assert res_e.sigma_u_px > res_c.sigma_u_px


# ==============================================================================
# 3. ESTIMATOR TRUSTWORTHINESS INTEGRATION
# ==============================================================================

class TestEstimatorTrustworthiness:
    """Verifies that the estimator uses observation uncertainty to scale R."""

    def test_measurement_noise_scales_with_spot_uncertainty(self):
        """build_measurement_noise_matrix must scale R with spot uncertainty."""
        # Clean spot (sigma = 0.2 px)
        R_low = build_measurement_noise_matrix(confidence=0.9, spot_uncertainty=(0.2, 0.2))

        # Degraded spot (sigma = 2.0 px)
        R_high = build_measurement_noise_matrix(confidence=0.9, spot_uncertainty=(2.0, 2.0))

        # Higher observation uncertainty yields strictly larger measurement noise R
        assert R_high[0, 0] > R_low[0, 0]
        assert R_high[1, 1] > R_low[1, 1]

    def test_kalman_filter_receives_uncertainty_and_computes_innovation(self):
        """TargetKalmanFilter.update must accept spot_uncertainty and compute innovation."""
        kf = TargetKalmanFilter()
        kf.initialize(measurement=(320.0, 240.0), timestamp=0.0)

        # Step 1: High confidence, low uncertainty measurement
        est1 = kf.update(
            measurement=(325.0, 242.0),
            confidence=0.95,
            timestamp=0.033,
            spot_uncertainty=(0.2, 0.2),
        )

        assert est1.innovation is not None
        assert est1.mahalanobis_distance > 0.0

        # Step 2: High uncertainty observation (e.g. noisy/faint)
        est2 = kf.update(
            measurement=(335.0, 245.0),
            confidence=0.50,
            timestamp=0.066,
            spot_uncertainty=(3.0, 3.0),
        )

        assert est2.innovation is not None
        # Innovation vector is actual residual y = z - H * x_pred
        assert len(est2.innovation) == 2


# ==============================================================================
# 4. TEMPORAL CONSISTENCY & JUMP ROOT-CAUSE INVESTIGATION
# ==============================================================================

class TestTemporalConsistencyAnalyzer:
    """Verifies jump root-cause categorization across consecutive frames."""

    def test_diagnose_hybrid_handoff_jump(self):
        """Jump coincident with detector engine switch must be diagnosed as HYBRID_HANDOFF."""
        analyzer = TemporalConsistencyAnalyzer(jump_threshold_px=10.0)

        # Frame k-1: CLASSICAL detection at (320, 240)
        analyzer.record_frame(
            frame_id=0,
            timestamp=0.0,
            dt=0.033,
            centroid=(320.0, 240.0),
            confidence=0.9,
            detected=True,
            detector_source="CLASSICAL",
        )

        # Frame k: NEURAL proposal handoff at (345, 240) -> 25 px jump
        diag = analyzer.record_frame(
            frame_id=1,
            timestamp=0.033,
            dt=0.033,
            centroid=(345.0, 240.0),
            confidence=0.85,
            detected=True,
            detector_source="NEURAL",
        )

        assert diag is not None
        assert diag.cause == JumpCause.HYBRID_HANDOFF
        assert "handoff" in diag.evidence_summary.lower()

    def test_diagnose_candidate_ambiguity_jump(self):
        """Jump with multiple competing proposals must be diagnosed as CANDIDATE_AMBIGUITY."""
        analyzer = TemporalConsistencyAnalyzer(jump_threshold_px=10.0)

        analyzer.record_frame(
            frame_id=0,
            timestamp=0.0,
            dt=0.033,
            centroid=(320.0, 240.0),
            confidence=0.7,
            detected=True,
            detector_source="HYBRID",
            candidate_count=1,
        )

        # Jump to alternate distractor candidate
        diag = analyzer.record_frame(
            frame_id=1,
            timestamp=0.033,
            dt=0.033,
            centroid=(350.0, 240.0),
            confidence=0.60,
            detected=True,
            detector_source="HYBRID",
            candidate_count=3,
        )

        assert diag is not None
        assert diag.cause == JumpCause.CANDIDATE_AMBIGUITY

    def test_diagnose_noise_jump(self):
        """Jump under low SNR / contrast must be diagnosed as NOISE."""
        analyzer = TemporalConsistencyAnalyzer(jump_threshold_px=10.0)

        analyzer.record_frame(
            frame_id=0,
            timestamp=0.0,
            dt=0.033,
            centroid=(320.0, 240.0),
            confidence=0.8,
            detected=True,
            detector_source="HYBRID",
        )

        # Noise jump: SNR = 1.8, contrast = 8.0
        diag = analyzer.record_frame(
            frame_id=1,
            timestamp=0.033,
            dt=0.033,
            centroid=(340.0, 255.0),
            confidence=0.25,
            detected=True,
            detector_source="HYBRID",
            quality={"snr": 1.8, "local_contrast": 8.0},
        )

        assert diag is not None
        assert diag.cause == JumpCause.NOISE

    def test_diagnose_edge_effect_jump(self):
        """Jump near frame margin must be diagnosed as EDGE_EFFECT."""
        analyzer = TemporalConsistencyAnalyzer(jump_threshold_px=10.0, sensor_margin_px=10)

        analyzer.record_frame(
            frame_id=0,
            timestamp=0.0,
            dt=0.033,
            centroid=(20.0, 240.0),
            confidence=0.8,
            detected=True,
            detector_source="HYBRID",
        )

        # Moves to u = 4 px (inside 10 px margin) and clips
        diag = analyzer.record_frame(
            frame_id=1,
            timestamp=0.033,
            dt=0.033,
            centroid=(4.0, 240.0),
            confidence=0.75,
            detected=True,
            detector_source="HYBRID",
            clipped_by_edge=True,
        )

        assert diag is not None
        assert diag.cause == JumpCause.EDGE_EFFECT

    def test_diagnose_true_target_motion(self):
        """Sustained displacement with high SNR and consistent detector is TRUE_MOTION."""
        analyzer = TemporalConsistencyAnalyzer(jump_threshold_px=10.0, max_physical_speed_px_s=200.0)

        analyzer.record_frame(
            frame_id=0,
            timestamp=0.0,
            dt=0.033,
            centroid=(320.0, 240.0),
            confidence=0.95,
            detected=True,
            detector_source="HYBRID",
            quality={"snr": 25.0, "local_contrast": 180.0},
        )

        # High-velocity true motion (35 px in 0.033s = ~1060 px/s physical step)
        diag = analyzer.record_frame(
            frame_id=1,
            timestamp=0.033,
            dt=0.033,
            centroid=(355.0, 240.0),
            confidence=0.95,
            detected=True,
            detector_source="HYBRID",
            quality={"snr": 24.0, "local_contrast": 175.0},
            candidate_count=1,
        )

        assert diag is not None
        assert diag.cause == JumpCause.TRUE_MOTION
        assert diag.retained_as_valid is True


# ==============================================================================
# 5. REAL MP4 EVALUATION WITH ENRICHED MEASUREMENTS
# ==============================================================================

class TestRealMP4EnrichedMeasurements:
    """Verifies that real MP4 stream produces valid quality, uncertainty, and innovations."""

    def test_sample_video_streams_with_full_telemetry(self):
        if not SAMPLE_VIDEO_PATH.exists():
            pytest.skip("Sample video file not available.")

        pipeline = ExternalHybridPipeline(SAMPLE_VIDEO_PATH, enable_estimator=True)
        records = pipeline.run(max_frames=45)
        pipeline.close()

        assert len(records) == 45

        for i, rec in enumerate(records):
            assert rec.detected is True
            assert rec.centroid is not None
            assert rec.uncertainty is not None
            assert rec.uncertainty[0] > 0.0
            assert rec.uncertainty[1] > 0.0
            assert rec.candidate_quality is not None
            assert rec.candidate_quality["snr"] > 0.0
            if rec.innovation is not None:
                assert rec.innovation_mahalanobis is not None
            assert rec.jump_classification in [c.value for c in JumpCause]
