"""
HORIZON Simulation Engine
=================================
Deterministic core simulation engine.
Orchestrates clock, seed manager, trajectory kinematics, beacon model,
world renderer, and ground-truth recording.

Strict constraint: Independent of GUI or wall-clock timing.
Ground truth state and frames are pure mathematical outputs.
"""

from __future__ import annotations

import logging
import math
import uuid
from typing import Callable, List, Optional, Tuple
import numpy as np

from simulator.camera.camera import VirtualCamera
from simulator.camera.gimbal import CameraGimbal
from simulator.camera.intrinsics import CameraIntrinsics
from simulator.core.clock import FixedTimestepClock
from simulator.core.config import AppConfig
from simulator.core.recorder import GroundTruthRecorder
from simulator.core.seed_manager import SeedManager
from simulator.disturbances.pipeline import DisturbancePipeline, DisturbanceTelemetry
from simulator.trajectories.base import Trajectory
from simulator.trajectories.circular import CircularTrajectory
from simulator.trajectories.figure8 import FigureEightTrajectory
from simulator.trajectories.random_motion import RandomMotionTrajectory
from simulator.trajectories.sinusoidal import SinusoidalTrajectory
from simulator.trajectories.spiral import SpiralTrajectory
from simulator.trajectories.straight import StraightLineTrajectory
from simulator.world.beacon import Beacon
from simulator.world.state import TargetState
from simulator.world.world import WorldRenderer

logger = logging.getLogger(__name__)


class SimulationEngine:
    """Core deterministic simulation engine for HORIZON.

    Parameters:
        config: Validated AppConfig instance.
        experiment_id: Optional string identifier. If None, auto-generated.
    """

    def __init__(self, config: AppConfig, experiment_id: Optional[str] = None) -> None:
        self._config = config
        self._experiment_id = experiment_id or f"EXP_{uuid.uuid4().hex[:8].upper()}"

        # Subsystems (initialized in initialize())
        self._clock: Optional[FixedTimestepClock] = None
        self._seed_mgr: Optional[SeedManager] = None
        self._world_renderer: Optional[WorldRenderer] = None
        self._beacon: Optional[Beacon] = None
        self._trajectory: Optional[Trajectory] = None
        self._recorder: Optional[GroundTruthRecorder] = None
        self._camera: Optional[VirtualCamera] = None
        self._disturbance_pipeline: Optional[DisturbancePipeline] = None
        self._last_disturbance_telemetry: Optional[DisturbanceTelemetry] = None

        # State tracking
        self._current_state: Optional[TargetState] = None
        self._current_frame: Optional[np.ndarray] = None
        self._path_history: List[Tuple[float, float]] = []
        self._max_path_history: int = 120  # Keep last 2 seconds at 60Hz
        self._is_initialized: bool = False
        self._is_running: bool = False

    @property
    def config(self) -> AppConfig:
        return self._config

    @property
    def experiment_id(self) -> str:
        return self._experiment_id

    @property
    def clock(self) -> FixedTimestepClock:
        if self._clock is None:
            raise RuntimeError("Engine not initialized. Call initialize() first.")
        return self._clock

    @property
    def recorder(self) -> GroundTruthRecorder:
        if self._recorder is None:
            raise RuntimeError("Engine not initialized. Call initialize() first.")
        return self._recorder

    @property
    def camera(self) -> VirtualCamera:
        if self._camera is None:
            raise RuntimeError("Engine not initialized. Call initialize() first.")
        return self._camera

    @property
    def disturbance_pipeline(self) -> DisturbancePipeline:
        if self._disturbance_pipeline is None:
            raise RuntimeError("Engine not initialized. Call initialize() first.")
        return self._disturbance_pipeline

    @property
    def last_disturbance_telemetry(self) -> Optional[DisturbanceTelemetry]:
        return self._last_disturbance_telemetry

    @property
    def is_running(self) -> bool:
        if self._clock is None:
            return False
        return self._clock.current_frame < self._config.simulation.total_frames

    @property
    def is_initialized(self) -> bool:
        return self._is_initialized

    def initialize(self) -> None:
        """Initialize all subsystems according to configuration."""
        cfg = self._config

        # 1. Clock
        self._clock = FixedTimestepClock(frequency_hz=cfg.simulation.frequency_hz)

        # 2. Seed Manager
        self._seed_mgr = SeedManager(seed=cfg.simulation.seed)

        # 3. World Renderer
        self._world_renderer = WorldRenderer(
            width=cfg.world.width,
            height=cfg.world.height,
            background_level=cfg.world.background_level,
        )

        # 4. Beacon
        self._beacon = Beacon(
            target_id=1,
            size_px=cfg.target.size_px,
            intensity=cfg.target.intensity,
            shape="square",
            psf_model=cfg.target.psf_model,
            psf_sigma_px=cfg.target.psf_sigma_px,
            psf_background_adu=cfg.target.psf_background_adu,
        )

        # 5. Trajectory setup
        self._trajectory = self._create_trajectory()

        # 6. Recorder
        self._recorder = GroundTruthRecorder(
            experiment_id=self._experiment_id,
            seed=cfg.simulation.seed,
            trajectory_type=cfg.trajectory.type,
            world_width=cfg.world.width,
            world_height=cfg.world.height,
            target_size_px=cfg.target.size_px,
        )

        # 7. Camera
        intrinsics = CameraIntrinsics(
            width=cfg.camera.width,
            height=cfg.camera.height,
            fov_horizontal_deg=cfg.camera.fov_horizontal_deg,
            fov_vertical_deg=cfg.camera.fov_vertical_deg,
        )
        initial_pan, initial_tilt = self._determine_initial_camera_pointing()
        gimbal = CameraGimbal(
            rate_limit_deg_s=cfg.camera.rate_limit_deg_s,
            initial_pan_deg=initial_pan,
            initial_tilt_deg=initial_tilt,
        )
        self._camera = VirtualCamera(
            intrinsics=intrinsics,
            gimbal=gimbal,
            update_rate_hz=cfg.camera.update_rate_hz,
            world_width=cfg.world.width,
            world_height=cfg.world.height,
            pixel_pitch_um=cfg.camera.pixel_pitch_um,
            exposure_ms=cfg.camera.exposure_ms,
            gain_db=cfg.camera.gain_db,
            beam_wander_config=cfg.disturbance.beam_wander,
            seed_mgr=self._seed_mgr,
        )

        # 8. Disturbance Pipeline (Phase 3)
        self._disturbance_pipeline = DisturbancePipeline(
            config=cfg.disturbance,
            seed_mgr=self._seed_mgr,
        )
        self._last_disturbance_telemetry = None

        # 9. Compute initial state at t = 0
        self._path_history.clear()
        self._update_state_at(t=0.0)

        self._is_initialized = True
        logger.info(
            "SimulationEngine initialized: exp=%s, seed=%d, traj=%s, dt=%.4f",
            self._experiment_id,
            cfg.simulation.seed,
            cfg.trajectory.type,
            self._clock.dt,
        )

    def _determine_initial_camera_pointing(self) -> Tuple[float, float]:
        """Resolve initial camera gimbal pointing (pan_deg, tilt_deg).

        Priority (high → low):
          1. Explicit ``initial_pan_deg`` / ``initial_tilt_deg`` from CameraConfig.
          2. Seed-derived uniform random offset within
             ±``max_initial_offset_deg`` on each axis.
          3. Default: (0.0, 0.0) — boresight centered.

        Returns:
            (pan_deg, tilt_deg) in degrees.
        """
        cfg = self._config.camera
        offset = cfg.max_initial_offset_deg

        if offset > 0.0:
            camera_rng = self._seed_mgr.get_rng("initial_camera_pointing")
            pan_deg = (
                float(cfg.initial_pan_deg)
                if cfg.initial_pan_deg != 0.0
                else float(camera_rng.uniform(-offset, offset))
            )
            tilt_deg = (
                float(cfg.initial_tilt_deg)
                if cfg.initial_tilt_deg != 0.0
                else float(camera_rng.uniform(-offset, offset))
            )
        else:
            pan_deg = float(cfg.initial_pan_deg)
            tilt_deg = float(cfg.initial_tilt_deg)

        return pan_deg, tilt_deg

    def _determine_initial_position(self) -> Tuple[float, float]:
        """Resolve initial position: explicit from config or deterministic from seed."""
        cfg = self._config
        init_pos = cfg.target.initial_position

        margin = cfg.target.size_px / 2.0 + 50.0  # Safe margin from boundary
        x_min = margin
        x_max = cfg.world.width - margin
        y_min = margin
        y_max = cfg.world.height - margin

        placement_rng = self._seed_mgr.get_rng("initial_placement")

        x0 = (
            float(init_pos.x)
            if init_pos.x is not None
            else float(placement_rng.uniform(x_min, x_max))
        )
        y0 = (
            float(init_pos.y)
            if init_pos.y is not None
            else float(placement_rng.uniform(y_min, y_max))
        )
        return x0, y0

    def _create_trajectory(self) -> Trajectory:
        """Instantiate selected trajectory based on configuration."""
        cfg = self._config
        t_type = cfg.trajectory.type
        x0, y0 = self._determine_initial_position()

        if t_type == "straight":
            st_cfg = cfg.trajectory.straight
            return StraightLineTrajectory(
                x0=x0,
                y0=y0,
                vx0=st_cfg.velocity_x,
                vy0=st_cfg.velocity_y,
                world_width=cfg.world.width,
                world_height=cfg.world.height,
                target_size_px=cfg.target.size_px,
                boundary_mode=st_cfg.boundary_mode,
            )

        elif t_type == "circular":
            c_cfg = cfg.trajectory.circular
            return CircularTrajectory(
                center_x=c_cfg.center_x,
                center_y=c_cfg.center_y,
                radius=c_cfg.radius,
                angular_velocity=c_cfg.angular_velocity,
                phase=c_cfg.phase,
                world_width=cfg.world.width,
                world_height=cfg.world.height,
                target_size_px=cfg.target.size_px,
            )

        elif t_type == "figure8":
            f_cfg = cfg.trajectory.figure8
            return FigureEightTrajectory(
                center_x=f_cfg.center_x,
                center_y=f_cfg.center_y,
                amplitude_x=f_cfg.amplitude_x,
                amplitude_y=f_cfg.amplitude_y,
                angular_velocity=f_cfg.angular_velocity,
                phase=f_cfg.phase,
                world_width=cfg.world.width,
                world_height=cfg.world.height,
                target_size_px=cfg.target.size_px,
            )

        elif t_type == "random":
            r_cfg = cfg.trajectory.random
            traj_rng = self._seed_mgr.get_rng("random_trajectory")
            return RandomMotionTrajectory(
                rng=traj_rng,
                x0=x0,
                y0=y0,
                max_speed=r_cfg.max_speed,
                max_acceleration=r_cfg.max_acceleration,
                world_width=cfg.world.width,
                world_height=cfg.world.height,
                target_size_px=cfg.target.size_px,
                sim_dt=self._clock.dt,
            )

        elif t_type == "spiral":
            sp_cfg = cfg.trajectory.spiral
            return SpiralTrajectory(
                center_x=sp_cfg.center_x,
                center_y=sp_cfg.center_y,
                initial_radius=sp_cfg.initial_radius,
                expansion_rate=sp_cfg.expansion_rate,
                angular_velocity=sp_cfg.angular_velocity,
                phase=sp_cfg.phase,
            )

        elif t_type == "sinusoidal":
            sn_cfg = cfg.trajectory.sinusoidal
            return SinusoidalTrajectory(
                center_x=sn_cfg.center_x,
                center_y=sn_cfg.center_y,
                amplitude_x=sn_cfg.amplitude_x,
                amplitude_y=sn_cfg.amplitude_y,
                frequency_x=sn_cfg.frequency_x,
                frequency_y=sn_cfg.frequency_y,
                phase_x=sn_cfg.phase_x,
                phase_y=sn_cfg.phase_y,
            )

        raise ValueError(f"Unsupported trajectory type: {t_type}")

    def _update_state_at(self, t: float) -> None:
        """Compute state at simulation time t, render frame, and record ground truth."""
        x, y, vx, vy, ax, ay = self._trajectory.state_at(t)

        self._current_state = TargetState(
            target_id=1,
            timestamp=t,
            x=x,
            y=y,
            vx=vx,
            vy=vy,
            ax=ax,
            ay=ay,
            visible=True,
        )

        # Update path history (FIFO)
        self._path_history.append((x, y))
        if len(self._path_history) > self._max_path_history:
            self._path_history.pop(0)

        # Render frame
        self._current_frame = self._world_renderer.render(
            beacon=self._beacon,
            target_x=x,
            target_y=y,
            visible=True,
            path_history=self._path_history,
        )

        # Step camera and project target
        self._camera.step(
            sim_time=t,
            sim_dt=self._clock.dt,
            world_frame=self._current_frame,
            target_world_x=x,
            target_world_y=y,
        )
        if self._camera.is_new_observation and self._camera.last_clean_observation is not None:
            disturbed_frame, dist_telemetry = self._disturbance_pipeline.apply(
                clean_frame=self._camera.last_clean_observation,
                sim_time=t,
                sim_dt=self._clock.dt,
            )
            self._camera.set_disturbed_observation(disturbed_frame)
            self._last_disturbance_telemetry = dist_telemetry

        theta_x, theta_y, u, v, in_fov = self._camera.project_target(x, y)

        # Record ground truth
        self._recorder.record_frame(
            frame_index=self._clock.current_frame,
            state=self._current_state,
            camera_pan_deg=self._camera.gimbal.pan_deg,
            camera_tilt_deg=self._camera.gimbal.tilt_deg,
            camera_pan_rate_deg_s=self._camera.gimbal.actual_pan_rate,
            camera_tilt_rate_deg_s=self._camera.gimbal.actual_tilt_rate,
            target_theta_x_deg=math.degrees(theta_x),
            target_theta_y_deg=math.degrees(theta_y),
            target_pixel_u=u,
            target_pixel_v=v,
            target_in_fov=in_fov,
            disturbance_telemetry=self._last_disturbance_telemetry,
        )

    def step(self) -> np.ndarray:
        """Advance the simulation by one fixed timestep dt.

        Returns:
            The newly rendered 2000×2000 uint8 monochrome world frame.
        """
        if not self._is_initialized:
            self.initialize()

        self._clock.step()
        self._update_state_at(t=self._clock.current_time)
        return self._current_frame

    def get_current_state(self) -> TargetState:
        """Get the current ground-truth target state."""
        if self._current_state is None:
            raise RuntimeError("Engine not initialized.")
        return self._current_state

    @property
    def current_target_state(self) -> Optional[TargetState]:
        """Property alias for current target ground-truth state."""
        return self._current_state

    def get_current_frame(self) -> np.ndarray:
        """Get the current rendered monochrome world frame."""
        if self._current_frame is None:
            raise RuntimeError("Engine not initialized.")
        return self._current_frame

    def get_clean_frame(self) -> np.ndarray:
        """Get the latest uncorrupted camera frame (480×640 uint8)."""
        if self._camera is None:
            raise RuntimeError("Engine not initialized.")
        if self._camera.last_clean_observation is not None:
            return self._camera.last_clean_observation
        return self._camera.extract_viewport(self._current_frame)

    def get_disturbed_frame(self) -> np.ndarray:
        """Get the latest disturbed camera frame (480×640 uint8)."""
        if self._camera is None:
            raise RuntimeError("Engine not initialized.")
        if self._camera.last_disturbed_observation is not None:
            return self._camera.last_disturbed_observation
        return self.get_clean_frame()

    def get_camera_frame(self) -> np.ndarray:
        """Get the latest camera observation frame (480×640 uint8, disturbed if active)."""
        if self._camera is None:
            raise RuntimeError("Engine not initialized.")
        if self._camera.last_observation is not None:
            return self._camera.last_observation
        return self._camera.extract_viewport(self._current_frame)

    def run(self, callback: Optional[Callable[[int, TargetState, np.ndarray], None]] = None) -> None:
        """Run the simulation to completion (duration_seconds).

        Args:
            callback: Optional hook called per frame as:
                      callback(frame_idx, target_state, frame_image)
        """
        if not self._is_initialized:
            self.initialize()

        total = self._config.simulation.total_frames
        logger.info("Running simulation for %d frames...", total)

        # Invoke callback for frame 0
        if callback:
            callback(self._clock.current_frame, self._current_state, self._current_frame)

        while self._clock.current_frame < total:
            frame = self.step()
            if callback:
                callback(self._clock.current_frame, self._current_state, frame)

        logger.info("Simulation completed: %d frames recorded.", self._recorder.record_count)

    def reset(self) -> None:
        """Reset the simulation back to frame 0 with identical initial conditions."""
        self.initialize()
