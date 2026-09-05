"""
HORIZON Phase 5 State Estimation & Association Tests
===========================================================
Comprehensive verification test suite covering:
  1. Transition F, observation H, process noise Q, and measurement noise R matrices.
  2. Covariance numerical validation, symmetry, and error ellipse derivation.
  3. Innovation and Mahalanobis distance computation.
  4. Numerical cross-validation against independent textbook Kalman filter.
  5. Joseph-form covariance stabilization.
  6. Constant-velocity tracking convergence.
  7. Missing measurement handling and covariance expansion.
  8. Outlier rejection via Mahalanobis gating.
  9. Multi-candidate association and distractor rejection.
  10. Long-duration numerical stability (1,000+ frames).
  11. Track lifecycle and reset cycles.
  12. Isolated Ground-Truth Evaluator (RMSE, NEES).
"""

from __future__ import annotations

import math
import numpy as np
import pytest

from tests.reference_kalman import IndependentReferenceKalman
from tracking.association.association import (
    AssociationResult,
    MeasurementCandidate,
    TrackAssociator,
)
from tracking.association.gate import MahalanobisGate
from tracking.association.track import Track
from tracking.diagnostics.evaluation import EstimatorEvaluator
from tracking.diagnostics.visualization import draw_tracking_annotations
from tracking.estimation.covariance import (
    compute_covariance_ellipse,
    enforce_symmetry,
    validate_covariance,
)
from tracking.estimation.innovation import compute_innovation
from tracking.estimation.kalman import KalmanFilterConfig, TargetKalmanFilter
from tracking.estimation.model import (
    build_measurement_matrix,
    build_measurement_noise_matrix,
    build_process_noise_matrix,
    build_transition_matrix,
)
from tracking.estimation.state import EstimatorStatus, StateEstimate
from tracking.quality.track_quality import evaluate_track_quality


# =============================================================================
# 1. Model & Matrix Unit Tests
# =============================================================================

class TestModelMatrices:
    def test_transition_matrix_structure(self):
        dt = 0.05
        F = build_transition_matrix(dt)
        assert F.shape == (4, 4)
        expected = np.array([
            [1.0, 0.0, 0.05, 0.0],
            [0.0, 1.0, 0.0, 0.05],
            [0.0, 0.0, 1.0, 0.0],
            [0.0, 0.0, 0.0, 1.0],
        ])
        np.testing.assert_allclose(F, expected, atol=1e-10)

    def test_transition_matrix_negative_dt_raises(self):
        with pytest.raises(ValueError):
            build_transition_matrix(-0.01)

    def test_measurement_matrix_structure(self):
        H = build_measurement_matrix()
        assert H.shape == (2, 4)
        expected = np.array([
            [1.0, 0.0, 0.0, 0.0],
            [0.0, 1.0, 0.0, 0.0],
        ])
        np.testing.assert_allclose(H, expected, atol=1e-10)

    def test_process_noise_cwna_symmetry_and_psd(self):
        dt = 0.02
        sigma_a = 40.0
        Q = build_process_noise_matrix(dt, accel_noise_sigma=sigma_a, model_type="cwna")
        assert Q.shape == (4, 4)
        # Check symmetry
        np.testing.assert_allclose(Q, Q.T, atol=1e-12)
        # Check positive semi-definite (eigenvalues >= 0)
        eigvals = np.linalg.eigvalsh(Q)
        assert np.all(eigvals >= -1e-10)
        # Verify specific analytical values
        q_var = sigma_a**2
        assert math.isclose(Q[0, 0], (dt**3 / 3.0) * q_var, rel_tol=1e-9)
        assert math.isclose(Q[0, 2], (dt**2 / 2.0) * q_var, rel_tol=1e-9)
        assert math.isclose(Q[2, 2], dt * q_var, rel_tol=1e-9)

    def test_measurement_noise_adaptive_scaling(self):
        # Higher confidence -> smaller noise
        R_high = build_measurement_noise_matrix(confidence=1.0, base_sigma_px=0.5)
        R_low = build_measurement_noise_matrix(confidence=0.2, base_sigma_px=0.5)
        assert R_high[0, 0] < R_low[0, 0]
        # Diagonal and symmetric
        assert R_high[0, 1] == 0.0
        assert R_high[1, 0] == 0.0
        assert math.isclose(R_high[0, 0], 0.25, rel_tol=1e-6)  # (0.5)^2 = 0.25


# =============================================================================
# 2. Covariance Mathematics & Ellipse Tests
# =============================================================================

class TestCovarianceMath:
    def test_validate_covariance_valid(self):
        P = np.diag([1.0, 2.0, 3.0, 4.0])
        valid, reason = validate_covariance(P)
        assert valid
        assert reason == "Valid"

    def test_validate_covariance_non_symmetric(self):
        P = np.array([[1.0, 2.0], [0.0, 1.0]])
        valid, reason = validate_covariance(P)
        assert not valid
        assert "asymmetry" in reason.lower()

    def test_validate_covariance_nan(self):
        P = np.eye(4)
        P[0, 0] = np.nan
        valid, reason = validate_covariance(P)
        assert not valid
        assert "non-finite" in reason.lower()

    def test_validate_covariance_negative_diagonal(self):
        P = np.diag([1.0, -0.5, 3.0, 4.0])
        valid, reason = validate_covariance(P)
        assert not valid

    def test_enforce_symmetry(self):
        P = np.array([[1.0, 2.0], [1.0, 3.0]])
        P_sym = enforce_symmetry(P)
        np.testing.assert_allclose(P_sym, np.array([[1.0, 1.5], [1.5, 3.0]]))

    def test_compute_covariance_ellipse_diagonal(self):
        # Diagonal covariance with sigma_x=3 (var=9), sigma_y=1 (var=1)
        # For 1-sigma / p=0.3934, k=1.0: major=2*3=6, minor=2*1=2, angle=0 deg
        P = np.diag([9.0, 1.0, 0.0, 0.0])
        ellipse = compute_covariance_ellipse(P, center_x=100.0, center_y=200.0, confidence_level=0.39346934)
        assert math.isclose(ellipse.center_x, 100.0)
        assert math.isclose(ellipse.center_y, 200.0)
        assert math.isclose(ellipse.semi_major_axis, 3.0, rel_tol=1e-3)
        assert math.isclose(ellipse.semi_minor_axis, 1.0, rel_tol=1e-3)
        assert math.isclose(abs(ellipse.orientation_deg), 0.0, abs_tol=1e-3)

    def test_compute_covariance_ellipse_95_percent(self):
        # Chi-squared 95% scaling for 2 DOF: k = sqrt(5.991) ≈ 2.4477
        P = np.diag([1.0, 1.0, 0.0, 0.0])
        ellipse = compute_covariance_ellipse(P, confidence_level=0.95)
        expected_radius = math.sqrt(5.99146)
        assert math.isclose(ellipse.semi_major_axis, expected_radius, rel_tol=1e-3)
        assert math.isclose(ellipse.semi_minor_axis, expected_radius, rel_tol=1e-3)


# =============================================================================
# 3. Innovation & Mahalanobis Distance Tests
# =============================================================================

class TestInnovation:
    def test_innovation_zero_residual(self):
        z = np.array([[100.0], [50.0]])
        x_pred = np.array([[100.0], [50.0], [0.0], [0.0]])
        P_pred = np.eye(4)
        H = build_measurement_matrix()
        R = np.eye(2)

        inno = compute_innovation(z, x_pred, P_pred, H, R)
        assert inno.norm == 0.0
        assert inno.mahalanobis_sq == 0.0
        assert inno.mahalanobis_distance == 0.0
        assert inno.is_valid

    def test_innovation_known_distance(self):
        # Known residual: dx = 2, dy = 0. S = diag(4, 4).
        # d^2 = [2, 0] * [1/4, 0; 0, 1/4] * [2; 0] = 4 * 1/4 = 1.0
        z = np.array([[102.0], [50.0]])
        x_pred = np.array([[100.0], [50.0], [0.0], [0.0]])
        P_pred = np.diag([3.0, 3.0, 1.0, 1.0])
        H = build_measurement_matrix()
        R = np.diag([1.0, 1.0])  # S = 3 + 1 = 4

        inno = compute_innovation(z, x_pred, P_pred, H, R)
        assert math.isclose(inno.residual_x, 2.0)
        assert math.isclose(inno.residual_y, 0.0)
        assert math.isclose(inno.norm, 2.0)
        assert math.isclose(inno.mahalanobis_sq, 1.0, rel_tol=1e-6)
        assert math.isclose(inno.mahalanobis_distance, 1.0, rel_tol=1e-6)


# =============================================================================
# 4. Numerical Cross-Validation Against Independent Reference
# =============================================================================

class TestNumericalReferenceEquivalence:
    def test_production_matches_reference_filter(self):
        """Cross-check production filter against independent textbook Kalman filter."""
        dt = 0.033
        sigma_a = 50.0
        sigma_r = 0.5

        config = KalmanFilterConfig(
            accel_noise_sigma=sigma_a,
            base_measurement_sigma_px=sigma_r,
            initial_pos_sigma_px=5.0,
            initial_vel_sigma_px_s=120.0,
            use_joseph_form=True,
        )
        prod_kf = TargetKalmanFilter(config=config)
        ref_kf = IndependentReferenceKalman(
            q_accel_var=sigma_a**2,
            r_meas_var=sigma_r**2,
            p_pos_var=25.0,
            p_vel_var=14400.0,
        )

        # Initialize both at same observation
        init_z = (320.0, 240.0)
        prod_kf.initialize(init_z, timestamp=0.0)
        ref_kf.initialize(init_z)

        # Feed 30 synthetic steps
        rng = np.random.default_rng(42)
        true_x, true_y = 320.0, 240.0
        vx, vy = 15.0, -8.0

        for step in range(1, 31):
            true_x += vx * dt
            true_y += vy * dt
            meas = (true_x + rng.normal(0, sigma_r), true_y + rng.normal(0, sigma_r))
            t = step * dt

            # Prod
            est = prod_kf.update(meas, confidence=1.0, timestamp=t)
            # Ref
            ref_kf.predict(dt)
            ref_x, ref_P = ref_kf.update(meas)

            # Assert states match to within 1e-4 px
            prod_x = prod_kf.state_vector
            assert prod_x is not None
            np.testing.assert_allclose(prod_x, ref_x, atol=1e-4)
            # Assert covariances match to within 1e-4
            prod_P = prod_kf.covariance_matrix
            assert prod_P is not None
            np.testing.assert_allclose(prod_P, ref_P, atol=1e-4)


# =============================================================================
# 5. Kinematic Tracking Scenarios
# =============================================================================

class TestKinematicScenarios:
    def test_constant_velocity_tracking_convergence(self):
        """Filter tracks constant velocity and correctly estimates velocity vector."""
        kf = TargetKalmanFilter(
            KalmanFilterConfig(
                accel_noise_sigma=5.0,
                base_measurement_sigma_px=0.4,
                initial_pos_sigma_px=2.0,
                initial_vel_sigma_px_s=100.0,
            )
        )

        dt = 0.01667  # 60 Hz
        true_vx, true_vy = 25.0, -15.0
        x, y = 100.0, 200.0
        t = 0.0

        kf.initialize((x, y), timestamp=t)

        rng = np.random.default_rng(12345)
        for _ in range(150):  # 2.5 seconds
            t += dt
            x += true_vx * dt
            y += true_vy * dt
            meas = (x + rng.normal(0, 0.4), y + rng.normal(0, 0.4))
            est = kf.update(meas, confidence=1.0, timestamp=t)

        # After 2.5 seconds, velocity estimate must be close to true velocity
        assert math.isclose(est.estimated_vx, true_vx, abs_tol=2.0)
        assert math.isclose(est.estimated_vy, true_vy, abs_tol=2.0)
        # Verify 3-sigma statistical consistency
        sigma_vx = est.velocity_sigma_x
        sigma_vy = est.velocity_sigma_y
        assert abs(est.estimated_vx - true_vx) <= 3.0 * sigma_vx
        assert abs(est.estimated_vy - true_vy) <= 3.0 * sigma_vy
        # Position error must be small (< 0.8 px)
        pos_err = math.hypot(est.estimated_x - x, est.estimated_y - y)
        assert pos_err < 0.8

    def test_missing_measurement_gap_and_covariance_expansion(self):
        """Controlled gap test: M1, M2, M3, GAP, GAP, M4, M5."""
        kf = TargetKalmanFilter()
        dt = 0.02
        t = 0.0

        # Step 1-3: Nominal measurements
        est1 = kf.initialize((300.0, 200.0), timestamp=t)
        t += dt
        est2 = kf.update((301.0, 200.5), timestamp=t)
        t += dt
        est3 = kf.update((302.0, 201.0), timestamp=t)
        P3_trace = np.trace(est3.covariance)

        # Step 4: Missing measurement 1
        t += dt
        est4 = kf.update_missing(timestamp=t)
        assert est4.filter_status == EstimatorStatus.PREDICTING
        assert not est4.measurement_available
        assert est4.consecutive_misses == 1
        P4_trace = np.trace(est4.covariance)
        # Covariance MUST expand during coasting/prediction
        assert P4_trace > P3_trace

        # Step 5: Missing measurement 2
        t += dt
        est5 = kf.update_missing(timestamp=t)
        assert est5.consecutive_misses == 2
        assert np.trace(est5.covariance) > P4_trace

        # Step 6: Measurement resumes
        t += dt
        est6 = kf.update((305.0, 202.5), timestamp=t)
        assert est6.filter_status == EstimatorStatus.TRACKING
        assert est6.measurement_available
        assert est6.consecutive_misses == 0
        assert est6.consecutive_measurements == 1
        # Covariance contracts upon measurement
        assert np.trace(est6.covariance) < np.trace(est5.covariance)

    def test_outlier_rejection_via_mahalanobis_gate(self):
        """Outlier test: correct, correct, huge outlier, correct."""
        kf = TargetKalmanFilter(KalmanFilterConfig(gate_chi2_threshold=9.21))
        dt = 0.02
        t = 0.0

        kf.initialize((200.0, 200.0), timestamp=t)
        t += dt
        kf.update((200.5, 200.2), timestamp=t)
        t += dt
        est_before_outlier = kf.update((201.0, 200.4), timestamp=t)

        # Inject massive outlier 150 pixels away
        t += dt
        outlier_meas = (351.0, 350.0)
        est_outlier = kf.update(outlier_meas, timestamp=t)

        # Outlier MUST be rejected
        assert est_outlier.filter_status == EstimatorStatus.REJECTED_MEASUREMENT
        assert not est_outlier.measurement_available
        assert est_outlier.mahalanobis_distance > math.sqrt(9.21)

        # State must NOT be pulled toward outlier
        assert abs(est_outlier.estimated_x - est_before_outlier.estimated_x) < 2.0
        assert abs(est_outlier.estimated_y - est_before_outlier.estimated_y) < 2.0

        # Normal measurement resumes
        t += dt
        est_recovery = kf.update((202.0, 200.8), timestamp=t)
        assert est_recovery.filter_status == EstimatorStatus.TRACKING
        assert est_recovery.measurement_available


# =============================================================================
# 6. Multi-Candidate Association Tests
# =============================================================================

class TestCandidateAssociation:
    def test_multi_candidate_distractor_rejection(self):
        """True beacon, bright distractor, and noise blob are presented to associator."""
        associator = TrackAssociator(gate_threshold=9.21)
        H = build_measurement_matrix()

        # Predicted target at (300, 200)
        x_pred = np.array([[300.0], [200.0], [5.0], [0.0]], dtype=np.float64)
        P_pred = np.diag([4.0, 4.0, 20.0, 20.0]).astype(np.float64)

        candidates = [
            # Candidate 1: Noise blob far away (380, 260)
            MeasurementCandidate(
                candidate_id=1,
                centroid_x=380.0,
                centroid_y=260.0,
                confidence=0.3,
                score=0.2,
            ),
            # Candidate 2: Bright distractor slightly away (330, 200) -> outside gate
            MeasurementCandidate(
                candidate_id=2,
                centroid_x=330.0,
                centroid_y=200.0,
                confidence=0.95,
                score=0.9,
            ),
            # Candidate 3: True beacon near prediction (300.8, 199.6) -> inside gate
            MeasurementCandidate(
                candidate_id=3,
                centroid_x=300.8,
                centroid_y=199.6,
                confidence=0.92,
                score=0.88,
            ),
        ]

        result = associator.associate(candidates, x_pred, P_pred)
        assert result.associated
        assert result.selected_candidate is not None
        assert result.selected_candidate.candidate_id == 3
        # Ensure rejected candidates include cand 1 and cand 2
        rejected_ids = [c.candidate_id for c in result.rejected_candidates]
        assert 1 in rejected_ids
        assert 2 in rejected_ids

    def test_track_step_with_candidate_list(self):
        track = Track(track_id=1)
        t = 0.0

        # Step 1: Initialize with candidates
        cands = [
            MeasurementCandidate(candidate_id=10, centroid_x=100.0, centroid_y=150.0, confidence=0.8),
            MeasurementCandidate(candidate_id=11, centroid_x=50.0, centroid_y=50.0, confidence=0.2),
        ]
        est = track.step(candidates=cands, timestamp=t)
        assert track.status == EstimatorStatus.TRACKING
        assert math.isclose(est.estimated_x, 100.0)

        # Step 2: Update with next candidates
        t += 0.02
        cands2 = [
            MeasurementCandidate(candidate_id=12, centroid_x=100.5, centroid_y=150.2, confidence=0.85),
            MeasurementCandidate(candidate_id=13, centroid_x=250.0, centroid_y=300.0, confidence=0.9),  # distractor
        ]
        est2 = track.step(candidates=cands2, timestamp=t)
        assert track.last_association is not None
        assert track.last_association.selected_candidate is not None
        assert track.last_association.selected_candidate.candidate_id == 12


# =============================================================================
# 7. Quality, Evaluation & Diagnostics Tests
# =============================================================================

class TestQualityAndEvaluation:
    def test_evaluate_track_quality_fields(self):
        P = np.diag([1.0, 4.0, 9.0, 16.0])
        q = evaluate_track_quality(
            P=P,
            innovation_norm=1.5,
            mahalanobis_dist=1.2,
            measurement_available=True,
            consecutive_hits=5,
            consecutive_misses=0,
            last_update_time=1.0,
            track_age=10,
            detector_confidence=0.9,
        )
        assert q.measurement_available
        assert math.isclose(q.position_uncertainty, math.sqrt(5.0))
        assert math.isclose(q.velocity_uncertainty, math.sqrt(25.0))
        assert math.isclose(q.covariance_trace, 30.0)
        assert q.association_quality > 0.0

    def test_estimator_evaluator_metrics(self):
        evaluator = EstimatorEvaluator()
        P = np.eye(4)

        # Sample 1: error = 3 px
        evaluator.record_step(
            estimated_pos=(103.0, 100.0),
            estimated_vel=(0.0, 0.0),
            covariance=P,
            gt_pos=(100.0, 100.0),
            gt_vel=(0.0, 0.0),
            timestamp=0.1,
        )
        # Sample 2: error = 4 px
        evaluator.record_step(
            estimated_pos=(100.0, 104.0),
            estimated_vel=(0.0, 0.0),
            covariance=P,
            gt_pos=(100.0, 100.0),
            gt_vel=(0.0, 0.0),
            timestamp=0.2,
        )

        metrics = evaluator.compute_metrics()
        assert metrics.samples_count == 2
        # RMSE of [3, 4] = sqrt((9+16)/2) = sqrt(12.5) ≈ 3.5355
        assert math.isclose(metrics.position_rmse, math.sqrt(12.5), rel_tol=1e-4)
        assert math.isclose(metrics.position_error_mean, 3.5)
        assert math.isclose(metrics.position_error_max, 4.0)

    def test_draw_tracking_annotations_execution(self):
        frame = np.zeros((480, 640), dtype=np.uint8)
        kf = TargetKalmanFilter()
        est = kf.initialize((320.0, 240.0), timestamp=0.0)

        annotated = draw_tracking_annotations(
            frame=frame,
            estimate=est,
            ground_truth_pos=(320.0, 240.0),
            measurement_pos=(320.5, 239.8),
            draw_ellipse=True,
            draw_velocity_vector=True,
        )
        assert annotated.shape == (480, 640, 3)
        assert annotated.dtype == np.uint8


# =============================================================================
# 8. Numerical Stability & Long-Run Stress Tests
# =============================================================================

class TestNumericalStability:
    def test_long_run_1000_steps_no_nan_or_divergence(self):
        """1,000 steps continuous tracking under random motion and noise."""
        kf = TargetKalmanFilter()
        kf.initialize((100.0, 100.0), timestamp=0.0)

        dt = 0.01667
        t = 0.0
        x, y = 100.0, 100.0
        rng = np.random.default_rng(999)

        for step in range(1, 1001):
            t += dt
            # Subtle random acceleration
            ax = rng.normal(0, 10.0)
            ay = rng.normal(0, 10.0)
            x += (15.0 * dt) + (0.5 * ax * dt**2)
            y += (-10.0 * dt) + (0.5 * ay * dt**2)

            meas = (x + rng.normal(0, 0.5), y + rng.normal(0, 0.5))
            est = kf.update(meas, confidence=0.9, timestamp=t)

            # Assert validity every 50 frames
            if step % 50 == 0:
                assert np.all(np.isfinite(est.covariance))
                valid, _ = validate_covariance(est.covariance)
                assert valid
                assert np.isfinite(est.estimated_x)
                assert np.isfinite(est.estimated_y)
                assert np.isfinite(est.estimated_vx)
                assert np.isfinite(est.estimated_vy)

    def test_repeated_track_reset_cycles(self):
        """Verify clean state after 25 repeated initialize-update-reset cycles."""
        track = Track(track_id=1)
        for cycle in range(25):
            track.step(measurement=(100.0 + cycle, 200.0), timestamp=0.0)
            for s in range(1, 6):
                track.step(measurement=(100.0 + cycle + s, 200.0 + s), timestamp=s * 0.02)
            assert track.status == EstimatorStatus.TRACKING
            track.reset()
            assert track.status == EstimatorStatus.RESET
            assert track.last_estimate is None
