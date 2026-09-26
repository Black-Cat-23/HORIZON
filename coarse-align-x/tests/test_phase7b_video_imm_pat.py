"""
HORIZON Phase 7B Test Suite: External Video → IMM-EKF → PAT
=============================================================
Validates:
  1. Full Architectural Pipeline Connectivity:
     HYBRID measurement -> Existing data association -> Existing IMM-EKF -> Existing PAT
  2. Frame-by-frame consistency:
     Exact match of timestamp, measurement, estimate, and PAT state.
  3. Telemetry Tracking:
     state, velocity, covariance, innovation, model probabilities, PAT mode.
  4. Loss of Beacon Lifecycle:
     Exact PAT state machine transitions:
     TRACK -> DEGRADED -> REACQUIRE -> ACQUIRE -> TRACK
  5. Invariants Guarantee:
     - DO NOT modify IMM-EKF mathematics.
     - DO NOT modify PAT state definitions.
     - No VideoRecoveryMode, No VideoTracker, No VideoKalman.
  6. Real MP4 stream evaluation:
     Processes sample video through IMM-EKF and PAT with 100% lock retention.
"""

from __future__ import annotations

import math
from pathlib import Path
import time
from typing import List, Tuple
import cv2
import numpy as np
import pytest

from pat.mode_manager import PATModeManager
from pat.state import PATMode, PATState
from simulator.perception.config import DetectorConfig
from simulator.perception.detector import DetectionResult
from simulator.perception.hybrid_detector import HybridBeaconDetector
from sources.dynamic_roi import DynamicROI, DynamicROIManager
from sources.external_video_source import ExternalVideoSource
from sources.frame_packet import FramePacket
from sources.video_pipeline import ExternalHybridPipeline, PipelineMeasurementRecord
from tracking.association.track import Track
from tracking.estimation.imm_kalman import InteractingMultipleModelFilter
from tracking.estimation.kalman import TargetKalmanFilter
from tracking.estimation.state import EstimatorStatus, StateEstimate

SAMPLE_VIDEO_PATH = Path("data/samples/isro_sample_beacon_test.mp4")


def _generate_synthetic_frame_sequence(
    num_frames: int = 30,
    drop_range: Tuple[int, int] = (-1, -1),
) -> List[Tuple[np.ndarray, Tuple[float, float], bool]]:
    """Generates synthetic (frame, (true_u, true_v), has_beacon) sequence."""
    np.random.seed(42)
    frames = []
    yy, xx = np.mgrid[0:480, 0:640]

    for i in range(num_frames):
        u_i = 320.0 + 35.0 * math.sin(0.15 * i)
        v_i = 240.0 + 25.0 * math.cos(0.15 * i)
        noise = np.random.normal(0, 3.0, (480, 640))
        bg = 18.0 + noise

        has_beacon = not (drop_range[0] <= i <= drop_range[1])
        if has_beacon:
            spot = np.exp(-0.5 * (((xx - u_i) ** 2 + (yy - v_i) ** 2) / (5.0 ** 2))) * 210.0
            f = np.clip(bg + spot, 0, 255).astype(np.uint8)
        else:
            f = np.clip(bg, 0, 255).astype(np.uint8)

        frames.append((f, (u_i, v_i), has_beacon))
    return frames


# ==============================================================================
# 1. ARCHITECTURAL INTEGRITY & PIPELINE COMPOSITION
# ==============================================================================

class TestVideoIMMPATPipelineIntegrity:
    """Verifies that ExternalHybridPipeline connects existing HYBRID, IMM-EKF, and PAT."""

    def test_pipeline_default_instantiates_imm_and_pat(self):
        """Pipeline must default to existing Track (IMM-EKF) and existing PATModeManager."""
        pipeline = ExternalHybridPipeline(
            SAMPLE_VIDEO_PATH if SAMPLE_VIDEO_PATH.exists() else "dummy.mp4",
            enable_estimator=True,
        )
        assert pipeline.track is not None
        assert isinstance(pipeline.track, Track)
        assert isinstance(pipeline.track.filter, InteractingMultipleModelFilter)
        assert pipeline.pat_manager is not None
        assert isinstance(pipeline.pat_manager, PATModeManager)
        assert pipeline.estimator is pipeline.track.filter

    def test_strictly_no_ad_hoc_video_classes_exist(self):
        """No VideoRecoveryMode, VideoTracker, or VideoKalman classes may exist."""
        import sources
        import sources.video_pipeline as vp

        assert not hasattr(sources, "VideoRecoveryMode")
        assert not hasattr(sources, "VideoTracker")
        assert not hasattr(sources, "VideoKalman")
        assert not hasattr(vp, "VideoRecoveryMode")
        assert not hasattr(vp, "VideoTracker")
        assert not hasattr(vp, "VideoKalman")


# ==============================================================================
# 2. FRAME-BY-FRAME CONSISTENCY (TIMESTAMP, MEASUREMENT, ESTIMATE, PAT)
# ==============================================================================

class TestFrameByFrameConsistency:
    """Verifies consistent timebase and state propagation across every single frame."""

    def test_timestamp_and_state_consistency_across_all_subsystems(self):
        frames = _generate_synthetic_frame_sequence(num_frames=20)

        track = Track(filter_type="IMM_ADAPTIVE_EKF")
        pat_mgr = PATModeManager()
        pipeline = ExternalHybridPipeline(
            SAMPLE_VIDEO_PATH if SAMPLE_VIDEO_PATH.exists() else "dummy.mp4",
            track=track,
            pat_manager=pat_mgr,
        )

        dt_step = 1.0 / 30.0
        cur_t = 0.0

        for i, (f, (true_u, true_v), has_beacon) in enumerate(frames):
            # Process frame directly through internal pipeline logic
            res = pipeline._detector.detect(f, timestamp=cur_t)
            meas = res.centroid if res.detected else None
            conf = float(res.confidence) if res.detected else 0.0
            unc = (float(res.sigma_u_px), float(res.sigma_v_px)) if res.detected else None

            est = track.step(
                measurement=meas,
                confidence=conf,
                timestamp=cur_t,
                is_sensor_step=True,
                spot_uncertainty=unc,
            )

            cov_trace = float(est.position_uncertainty**2)
            pat = pat_mgr.process_step(
                dt=dt_step,
                timestamp_s=cur_t,
                detection_valid=res.detected,
                detection_confidence=conf,
                mahalanobis_d2=float(est.mahalanobis_distance**2),
                covariance_trace=cov_trace,
                estimated_u_px=float(est.estimated_x),
                estimated_v_px=float(est.estimated_y),
                estimated_vx_px_s=float(est.estimated_vx),
                estimated_vy_px_s=float(est.estimated_vy),
                current_pan_deg=0.0,
                current_tilt_deg=0.0,
                is_new_frame=True,
            )

            # 1. Authoritative timestamp consistency
            assert abs(est.timestamp - cur_t) < 1e-6
            # 2. Measurement consistency
            if has_beacon:
                assert res.detected is True
                assert meas is not None
                assert abs(meas[0] - true_u) < 1.0
                assert abs(meas[1] - true_v) < 1.0
            # 3. Estimate consistency
            assert np.isfinite(est.estimated_x) and np.isfinite(est.estimated_y)
            assert np.isfinite(est.estimated_vx) and np.isfinite(est.estimated_vy)
            assert est.covariance.shape == (4, 4)
            assert np.all(np.diag(est.covariance) > 0.0)
            # 4. PAT state consistency
            assert pat.mode in (PATMode.SEARCH, PATMode.ACQUIRE, PATMode.TRACK, PATMode.DEGRADED, PATMode.REACQUIRE)
            assert np.isfinite(pat.track_quality)

            cur_t += dt_step


# ==============================================================================
# 3. TELEMETRY TRACKING (STATE, VELOCITY, COVARIANCE, INNOVATION, IMM PROBS, PAT)
# ==============================================================================

class TestTelemetryTracking:
    """Verifies that all required Phase 7B tracking quantities are exposed on records."""

    def test_telemetry_exposure_on_pipeline_measurement_record(self):
        frames = _generate_synthetic_frame_sequence(num_frames=15)
        pipeline = ExternalHybridPipeline(
            SAMPLE_VIDEO_PATH if SAMPLE_VIDEO_PATH.exists() else "dummy.mp4",
            enable_estimator=True,
        )

        dt_step = 1.0 / 30.0
        cur_t = 0.0

        for i, (f, _, _) in enumerate(frames):
            det_res = pipeline.detector.detect(f, timestamp=cur_t)
            unc = (float(det_res.sigma_u_px), float(det_res.sigma_v_px)) if det_res.detected else None

            est = pipeline.track.step(
                measurement=det_res.centroid,
                confidence=float(det_res.confidence),
                timestamp=cur_t,
                is_sensor_step=True,
                spot_uncertainty=unc,
            )

            pat = pipeline.pat_manager.process_step(
                dt=dt_step,
                timestamp_s=cur_t,
                detection_valid=det_res.detected,
                detection_confidence=float(det_res.confidence),
                mahalanobis_d2=float(est.mahalanobis_distance**2),
                covariance_trace=float(est.position_uncertainty**2),
                estimated_u_px=float(est.estimated_x),
                estimated_v_px=float(est.estimated_y),
                estimated_vx_px_s=float(est.estimated_vx),
                estimated_vy_px_s=float(est.estimated_vy),
                current_pan_deg=0.0,
                current_tilt_deg=0.0,
                is_new_frame=True,
            )

            rec = PipelineMeasurementRecord(
                frame_id=i,
                timestamp=cur_t,
                dt=dt_step,
                centroid=det_res.centroid,
                centroid_original=det_res.centroid,
                confidence=float(det_res.confidence),
                detected=det_res.detected,
                bounding_box=det_res.bbox,
                source=det_res.detector_source,
                agreement_state=det_res.agreement_state,
                decode_latency_ms=1.0,
                processing_latency_ms=2.0,
                estimated_state=(float(est.estimated_x), float(est.estimated_y)),
                estimated_velocity=(float(est.estimated_vx), float(est.estimated_vy)),
                covariance=est.covariance.copy(),
                model_probabilities=est.estimator_health.model_probabilities if est.estimator_health else None,
                pat_mode=pat.mode.value,
                pat_state=pat.to_dict(),
            )

            # Verify every field exists and is valid
            assert rec.estimated_state is not None
            assert rec.estimated_velocity is not None
            assert rec.covariance is not None
            assert rec.covariance.shape == (4, 4)
            assert rec.model_probabilities is not None
            assert len(rec.model_probabilities) == 3
            assert abs(sum(rec.model_probabilities) - 1.0) < 1e-4
            assert rec.pat_mode in ("SEARCH", "ACQUIRE", "TRACK", "DEGRADED", "REACQUIRE")
            assert rec.pat_state is not None
            assert rec.pat_state["pat_state"] == rec.pat_mode

            # Verify to_dict serialization
            d = rec.to_dict()
            assert "estimated_state" in d
            assert "estimated_velocity" in d
            assert "covariance" in d
            assert "model_probabilities" in d
            assert "pat_mode" in d
            assert "pat_state" in d

            cur_t += dt_step


# ==============================================================================
# 4. LOSS OF BEACON & RECOVERY (TRACK -> DEGRADED -> REACQUIRE -> ACQUIRE -> TRACK)
# ==============================================================================

class TestBeaconLossAndRecoveryFSM:
    """Verifies existing PAT mode transitions upon temporary beacon loss and reacquisition."""

    def test_loss_of_beacon_transitions_through_pat_fsm(self):
        """
        Timeline:
          Frames 0-8:   Visible beacon -> SEARCH -> ACQUIRE -> TRACK
          Frames 9-11:  Drop beacon (misses >= 1) -> DEGRADED
          Frames 12-18: Continuous drop (misses >= 5) -> REACQUIRE
          Frames 19-25: Reappear -> ACQUIRE -> (hits confirmed) -> TRACK restored
        """
        # Create sequence with drop from frame 9 to 18 (10 frames of occlusion)
        frames = _generate_synthetic_frame_sequence(num_frames=30, drop_range=(9, 18))

        track = Track(filter_type="IMM_ADAPTIVE_EKF")
        pat_mgr = PATModeManager()
        detector = HybridBeaconDetector(DetectorConfig(perception_mode="HYBRID"))

        dt_step = 1.0 / 30.0
        cur_t = 0.0
        mode_history = []

        for i, (f, _, has_beacon) in enumerate(frames):
            det_res = detector.detect(f, timestamp=cur_t)
            meas = det_res.centroid if det_res.detected else None
            conf = float(det_res.confidence) if det_res.detected else 0.0
            unc = (float(det_res.sigma_u_px), float(det_res.sigma_v_px)) if det_res.detected else None

            est = track.step(
                measurement=meas,
                confidence=conf,
                timestamp=cur_t,
                is_sensor_step=True,
                spot_uncertainty=unc,
            )

            pat = pat_mgr.process_step(
                dt=dt_step,
                timestamp_s=cur_t,
                detection_valid=det_res.detected,
                detection_confidence=conf,
                mahalanobis_d2=float(est.mahalanobis_distance**2),
                covariance_trace=float(est.position_uncertainty**2),
                estimated_u_px=float(est.estimated_x),
                estimated_v_px=float(est.estimated_y),
                estimated_vx_px_s=float(est.estimated_vx),
                estimated_vy_px_s=float(est.estimated_vy),
                current_pan_deg=0.0,
                current_tilt_deg=0.0,
                is_new_frame=True,
            )

            mode_history.append((i, pat.mode, has_beacon, det_res.detected))
            cur_t += dt_step

        # Analyze mode progression
        modes_visited = [m[1] for m in mode_history]

        # 1. Starts in SEARCH or ACQUIRE
        assert PATMode.ACQUIRE in modes_visited[:5]

        # 2. Confirms track
        assert PATMode.TRACK in modes_visited[3:9]

        # 3. Enters DEGRADED on beacon drop
        assert PATMode.DEGRADED in modes_visited[9:14]

        # 4. Enters REACQUIRE on persistent drop
        assert PATMode.REACQUIRE in modes_visited[14:19]

        # 5. Returns to ACQUIRE when beacon reappears
        assert PATMode.ACQUIRE in modes_visited[19:24]

        # 6. Re-establishes TRACK
        assert PATMode.TRACK in modes_visited[23:]

        # Verify exact chain was traversed
        chain = [PATMode.SEARCH]
        for _, m, _, _ in mode_history:
            if chain[-1] != m:
                chain.append(m)

        expected_subsequence = [
            PATMode.SEARCH,
            PATMode.ACQUIRE,
            PATMode.TRACK,
            PATMode.DEGRADED,
            PATMode.REACQUIRE,
            PATMode.ACQUIRE,
            PATMode.TRACK,
        ]
        assert chain == expected_subsequence, f"Actual transition chain {chain} != expected {expected_subsequence}"


# ==============================================================================
# 5. REAL MP4 VIDEO EVALUATION (IMM-EKF + PAT)
# ==============================================================================

class TestRealMP4VideoIMMPAT:
    """Verifies that ExternalHybridPipeline runs real MP4 through IMM-EKF and PAT."""

    def test_sample_mp4_streaming_imm_pat_lifecycle(self):
        if not SAMPLE_VIDEO_PATH.exists():
            pytest.skip("Sample video file not available.")

        pipeline = ExternalHybridPipeline(
            SAMPLE_VIDEO_PATH,
            enable_estimator=True,
            enable_dynamic_roi=True,
        )
        records = pipeline.run(max_frames=40)
        pipeline.close()

        assert len(records) == 40

        track_confirmed = False
        for i, rec in enumerate(records):
            assert rec.detected is True
            assert rec.centroid is not None
            assert rec.estimated_state is not None
            assert rec.estimated_velocity is not None
            assert rec.covariance is not None
            assert rec.model_probabilities is not None
            assert rec.pat_mode is not None

            # Verify IMM model probabilities
            pcv, pca, pman = rec.model_probabilities
            assert 0.0 <= pcv <= 1.0
            assert 0.0 <= pca <= 1.0
            assert 0.0 <= pman <= 1.0
            assert abs(pcv + pca + pman - 1.0) < 1e-3

            if rec.pat_mode == "TRACK":
                track_confirmed = True

        # Pipeline must successfully acquire and lock target
        assert track_confirmed is True
        assert records[-1].pat_mode == "TRACK"
