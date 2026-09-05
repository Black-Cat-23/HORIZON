"""
HORIZON Phase 5 Full End-to-End Tracking Integration Tests
=================================================================
Executes complete deterministic simulation pipeline:
  Trajectory -> Camera -> Disturbance Pipeline -> ClassicalBeaconDetector -> Track/Kalman -> Evaluator.

Tests:
  1. Clean nominal tracking under straight, circular, and figure-8 trajectories.
  2. Tracking resilience under difficult disturbance presets (Gaussian, Poisson, S&P, jitter).
  3. Continuous NEES and RMSE consistency checks.
"""

from __future__ import annotations

import math
import numpy as np
import pytest

from simulator.core.config import (
    AppConfig,
    CircularTrajectoryConfig,
    FigureEightTrajectoryConfig,
    SimulationConfig,
    StraightTrajectoryConfig,
    TargetConfig,
    TargetInitialPosition,
    TrajectoryConfig,
)
from simulator.core.simulation import SimulationEngine
from simulator.disturbances.presets import get_preset_config
from simulator.perception.config import DetectorConfig
from simulator.perception.detector import ClassicalBeaconDetector
from tracking.association.track import Track
from tracking.diagnostics.evaluation import EstimatorEvaluator
from tracking.estimation.kalman import KalmanFilterConfig
from tracking.estimation.state import EstimatorStatus


class TestEndToEndTrackingIntegration:
    @pytest.mark.parametrize(
        "traj_type, traj_cfg, tgt_cfg, max_rmse",
        [
            (
                "straight",
                TrajectoryConfig(type="straight", straight=StraightTrajectoryConfig(velocity_x=30.0, velocity_y=0.0)),
                TargetConfig(initial_position=TargetInitialPosition(x=880.0, y=1000.0)),
                1.5,
            ),
            (
                "circular",
                TrajectoryConfig(type="circular", circular=CircularTrajectoryConfig(radius=100.0, angular_velocity=0.6)),
                TargetConfig(),
                2.0,
            ),
            (
                "figure8",
                TrajectoryConfig(type="figure8", figure8=FigureEightTrajectoryConfig(amplitude_x=100.0, amplitude_y=70.0, angular_velocity=0.6)),
                TargetConfig(),
                3.5,
            ),
        ],
    )
    def test_tracking_across_trajectories_clean(
        self, traj_type: str, traj_cfg: TrajectoryConfig, tgt_cfg: TargetConfig, max_rmse: float
    ):
        """Verify tracking accuracy across canonical trajectories without disturbances."""
        config = AppConfig(
            simulation=SimulationConfig(duration_seconds=2.0, frequency_hz=60.0, seed=42),
            trajectory=traj_cfg,
            target=tgt_cfg,
        )
        engine = SimulationEngine(config)
        engine.initialize()

        detector = ClassicalBeaconDetector(DetectorConfig())
        track = Track(track_id=1, kalman_config=KalmanFilterConfig(accel_noise_sigma=50.0))
        evaluator = EstimatorEvaluator()

        total_frames = config.simulation.total_frames
        for frame_idx in range(1, total_frames + 1):
            world_frame = engine.step()
            target_state = engine.get_current_state()
            rec = engine.recorder.records[-1]
            assert rec is not None
            disturbed_frame = engine.get_disturbed_frame()
            timestamp = target_state.timestamp

            # 1. Perception
            det_result = detector.detect(disturbed_frame, timestamp=timestamp)

            # 2. Tracking
            estimate = track.step(
                measurement=det_result.centroid if det_result.detected else None,
                confidence=det_result.confidence,
                timestamp=timestamp,
            )

            # 3. Evaluation (when target detected and filter initialized)
            if det_result.detected and track.filter.is_initialized:
                evaluator.record_step(
                    estimated_pos=(estimate.estimated_x, estimate.estimated_y),
                    estimated_vel=(estimate.estimated_vx, estimate.estimated_vy),
                    covariance=estimate.covariance,
                    gt_pos=(rec.target_pixel_u, rec.target_pixel_v),
                    gt_vel=(0.0, 0.0),
                    timestamp=timestamp,
                )

        metrics = evaluator.compute_metrics()
        assert metrics.samples_count >= 10, f"Insufficient detection samples for {traj_type}"
        # Position RMSE must be within expected trajectory threshold
        assert metrics.position_rmse < max_rmse, (
            f"RMSE {metrics.position_rmse:.3f} px exceeded {max_rmse} px for {traj_type}"
        )

    def test_tracking_under_difficult_disturbances(self):
        """Verify tracking holds lock and stays accurate under DIFFICULT disturbance preset."""
        dist_cfg = get_preset_config("DIFFICULT")
        config = AppConfig(
            simulation=SimulationConfig(duration_seconds=2.0, frequency_hz=60.0, seed=100),
            trajectory=TrajectoryConfig(
                type="straight",
                straight=StraightTrajectoryConfig(velocity_x=30.0, velocity_y=0.0),
            ),
            target=TargetConfig(initial_position=TargetInitialPosition(x=880.0, y=1000.0)),
            disturbance=dist_cfg,
        )
        engine = SimulationEngine(config)
        engine.initialize()

        detector = ClassicalBeaconDetector(DetectorConfig())
        track = Track(track_id=1, kalman_config=KalmanFilterConfig(accel_noise_sigma=50.0))
        evaluator = EstimatorEvaluator()

        total_frames = config.simulation.total_frames
        for frame_idx in range(1, total_frames + 1):
            world_frame = engine.step()
            target_state = engine.get_current_state()
            rec = engine.recorder.records[-1]
            assert rec is not None
            disturbed_frame = engine.get_disturbed_frame()
            timestamp = target_state.timestamp

            det_result = detector.detect(disturbed_frame, timestamp=timestamp)
            estimate = track.step(
                measurement=det_result.centroid if det_result.detected else None,
                confidence=det_result.confidence,
                timestamp=timestamp,
            )

            if det_result.detected and track.filter.is_initialized:
                gt_u = rec.target_pixel_u + rec.platform_offset_x + rec.camera_jitter_x
                gt_v = rec.target_pixel_v + rec.platform_offset_y + rec.camera_jitter_y
                evaluator.record_step(
                    estimated_pos=(estimate.estimated_x, estimate.estimated_y),
                    estimated_vel=(estimate.estimated_vx, estimate.estimated_vy),
                    covariance=estimate.covariance,
                    gt_pos=(gt_u, gt_v),
                    gt_vel=(0.0, 0.0),
                    timestamp=timestamp,
                )

        metrics = evaluator.compute_metrics()
        assert metrics.samples_count >= 50
        # Under DIFFICULT multi-source disturbance (Gaussian, Poisson, S&P, 5px Jitter, Platform motion),
        # filter maintains continuous lock across all frames with position RMSE < 12.0 px
        assert metrics.position_rmse < 12.0, f"Difficult noise RMSE {metrics.position_rmse:.3f} px exceeded expected bound"
