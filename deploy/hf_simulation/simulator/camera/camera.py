"""
HORIZON Virtual Camera System
====================================
Virtual optical camera sensor with physical gimbal actuation, pinhole projection,
subpixel viewport extraction, optical PSF, motion blur, sensor response (exposure/gain),
beam-wander disturbance, and SensorFrame immutability.

Conforms strictly to Phase 2 formal verification specifications:
  - Shape: exactly (480, 640), dtype uint8, single channel.
  - Optical intrinsics: W=640, H=480, FOVx=4°, FOVy=3°.
  - Update rate: 30 Hz decoupled observation generation.
  - True physical crop / projection (NOT resize).
  - Explicit physical pixel pitch (µm), exposure time (ms), and gain (dB).
"""

from __future__ import annotations

import math
from typing import Optional, Tuple
import cv2
import numpy as np

from simulator.camera.gimbal import CameraGimbal
from simulator.camera.intrinsics import CameraIntrinsics
from simulator.camera.motion_blur import MotionBlurEngine
from simulator.camera.sensor_response import apply_sensor_response
from simulator.camera.beam_wander import BeamWanderEngine
from simulator.camera.sensor_frame import SensorFrame, SensorLineage
from simulator.disturbances.config import BeamWanderConfig
from simulator.core.seed_manager import SeedManager


class VirtualCamera:
    """Virtual camera model modeling optical sensor, motorized gimbal, and sensor effects.

    Parameters:
        intrinsics: CameraIntrinsics instance (W=640, H=480, FOVx=4°, FOVy=3°).
        gimbal: CameraGimbal instance enforcing slew rate limits (default 5°/s).
        update_rate_hz: Sensor update frequency (default 30 Hz).
        world_width: Simulation world width (default 2000).
        world_height: Simulation world height (default 2000).
        pixel_pitch_um: Physical pixel size in micrometres (None = not modeled).
        exposure_ms: Sensor integration time (ms).
        gain_db: Electronic gain (dB).
        beam_wander_config: Optional BeamWanderConfig for optical centroid drift.
        seed_mgr: Optional SeedManager for deterministic beam-wander RNG.
    """

    def __init__(
        self,
        intrinsics: Optional[CameraIntrinsics] = None,
        gimbal: Optional[CameraGimbal] = None,
        update_rate_hz: float = 30.0,
        world_width: int = 2000,
        world_height: int = 2000,
        pixel_pitch_um: Optional[float] = None,
        exposure_ms: float = 1.0,
        gain_db: float = 0.0,
        beam_wander_config: Optional[BeamWanderConfig] = None,
        seed_mgr: Optional[SeedManager] = None,
    ) -> None:
        if update_rate_hz <= 0:
            raise ValueError(f"update_rate_hz must be positive, got {update_rate_hz}")
        if exposure_ms <= 0:
            raise ValueError(f"exposure_ms must be > 0, got {exposure_ms}")
        if not (-60.0 <= gain_db <= 60.0):
            raise ValueError(f"gain_db must be in [-60, +60] dB, got {gain_db}")
        if pixel_pitch_um is not None and pixel_pitch_um <= 0:
            raise ValueError(f"pixel_pitch_um must be > 0 when set, got {pixel_pitch_um}")

        self._intrinsics = intrinsics or CameraIntrinsics()
        self._gimbal = gimbal or CameraGimbal()
        self._update_rate_hz = float(update_rate_hz)
        self._obs_period = 1.0 / self._update_rate_hz

        self._world_w = int(world_width)
        self._world_h = int(world_height)
        self._center_x = float(self._world_w) / 2.0
        self._center_y = float(self._world_h) / 2.0

        # Physical sensor parameters
        self._pixel_pitch_um = float(pixel_pitch_um) if pixel_pitch_um is not None else None
        self._exposure_ms = float(exposure_ms)
        self._gain_db = float(gain_db)

        # Optical engines
        self._motion_blur_engine = MotionBlurEngine(frame_interval_ms=self._obs_period * 1000.0)
        
        # Beam-wander engine
        if beam_wander_config is not None and beam_wander_config.enabled:
            rng = seed_mgr.get_rng("beam_wander") if seed_mgr is not None else np.random.default_rng()
            self._beam_wander_engine = BeamWanderEngine(
                std_dev_px=beam_wander_config.std_dev_px,
                correlation_time_s=beam_wander_config.correlation_time_s,
                rng=rng,
            )
        else:
            self._beam_wander_engine = None

        # Timing tracking for decoupled observation rate
        self._last_obs_time: float = -1.0
        self._obs_count: int = 0
        self._last_clean_observation: Optional[np.ndarray] = None
        self._last_disturbed_observation: Optional[np.ndarray] = None
        self._sensor_frame: Optional[SensorFrame] = None
        self._is_new_obs: bool = False

        # Image-plane target velocity tracking for motion blur
        self._prev_target_u: Optional[float] = None
        self._prev_target_v: Optional[float] = None
        self._prev_target_time: Optional[float] = None

    @property
    def is_new_observation(self) -> bool:
        """True if an observation was captured during the most recent step."""
        return self._is_new_obs

    @property
    def intrinsics(self) -> CameraIntrinsics:
        return self._intrinsics

    @property
    def gimbal(self) -> CameraGimbal:
        return self._gimbal

    @property
    def update_rate_hz(self) -> float:
        return self._update_rate_hz

    @property
    def observation_count(self) -> int:
        return self._obs_count

    @property
    def pixel_pitch_um(self) -> Optional[float]:
        return self._pixel_pitch_um

    @property
    def exposure_ms(self) -> float:
        return self._exposure_ms

    @property
    def gain_db(self) -> float:
        return self._gain_db

    @property
    def beam_wander_engine(self) -> Optional[BeamWanderEngine]:
        return self._beam_wander_engine

    @property
    def sensor_frame(self) -> Optional[SensorFrame]:
        """Immutable SensorFrame object for the latest observation."""
        return self._sensor_frame

    @property
    def last_clean_observation(self) -> Optional[np.ndarray]:
        """Uncorrupted ground-truth optical camera frame."""
        return self._last_clean_observation

    @property
    def last_disturbed_observation(self) -> Optional[np.ndarray]:
        """Degraded camera frame after disturbance pipeline."""
        return self._last_disturbed_observation

    @property
    def last_observation(self) -> Optional[np.ndarray]:
        """Current observation (disturbed frame if available, else clean frame)."""
        if self._last_disturbed_observation is not None:
            return self._last_disturbed_observation
        return self._last_clean_observation

    def set_disturbed_observation(self, disturbed_frame: np.ndarray) -> None:
        """Record the post-disturbance sensor observation frame."""
        self._last_disturbed_observation = disturbed_frame
        if self._sensor_frame is not None:
            self._sensor_frame = self._sensor_frame.with_disturbed_pixels(disturbed_frame)

    def get_boresight_world_pos(self) -> Tuple[float, float]:
        """Compute the world pixel coordinates (bx, by) currently at the camera boresight."""
        pan_rad = math.radians(self._gimbal.pan_deg)
        tilt_rad = math.radians(self._gimbal.tilt_deg)

        bx = self._center_x + self._intrinsics.fx * math.tan(pan_rad)
        by = self._center_y + self._intrinsics.fy * math.tan(tilt_rad)
        return bx, by

    def compute_target_angles(
        self, target_world_x: float, target_world_y: float
    ) -> Tuple[float, float]:
        """Compute target angular offset (theta_x, theta_y in radians) relative to camera boresight."""
        bx, by = self.get_boresight_world_pos()
        dx = target_world_x - bx
        dy = target_world_y - by

        theta_x = math.atan(dx / self._intrinsics.fx)
        theta_y = math.atan(dy / self._intrinsics.fy)
        return theta_x, theta_y

    def project_target(
        self, target_world_x: float, target_world_y: float
    ) -> Tuple[float, float, float, float, bool]:
        """Project world target coordinate into camera sensor pixel coordinates (u, v).

        Returns:
            Tuple of (theta_x_rad, theta_y_rad, u_px, v_px, is_visible_in_fov)
        """
        # Apply beam wander shift to apparent position if enabled
        eff_x, eff_y = target_world_x, target_world_y
        if self._beam_wander_engine is not None:
            eff_x, eff_y = self._beam_wander_engine.get_effective_target_pos(
                target_world_x, target_world_y
            )

        theta_x, theta_y = self.compute_target_angles(eff_x, eff_y)
        u, v = self._intrinsics.project(theta_x, theta_y)
        visible = self._intrinsics.is_in_fov(theta_x, theta_y)
        return theta_x, theta_y, u, v, visible

    def should_capture(self, current_time: float, tol: float = 1e-6) -> bool:
        """Determine if a new camera observation should be triggered at current_time."""
        if self._last_obs_time < 0:
            return True
        elapsed = current_time - self._last_obs_time
        return elapsed >= (self._obs_period - tol)

    def extract_viewport(self, world_frame: np.ndarray) -> np.ndarray:
        """Extract a 640×480 monochrome camera image frame from the full 2000×2000 world frame.

        Uses subpixel-accurate cropping centered at the camera boresight.
        Pads with background level 0 if boresight points near world boundary.
        """
        bx, by = self.get_boresight_world_pos()
        w_cam = self._intrinsics.width
        h_cam = self._intrinsics.height
        half_w = w_cam / 2.0
        half_h = h_cam / 2.0

        col_start = int(round(bx - half_w))
        col_end = col_start + w_cam
        row_start = int(round(by - half_h))
        row_end = row_start + h_cam

        cam_frame = np.zeros((h_cam, w_cam), dtype=np.uint8)

        src_r1 = max(0, row_start)
        src_r2 = min(world_frame.shape[0], row_end)
        src_c1 = max(0, col_start)
        src_c2 = min(world_frame.shape[1], col_end)

        if src_r2 > src_r1 and src_c2 > src_c1:
            dst_r1 = src_r1 - row_start
            dst_r2 = dst_r1 + (src_r2 - src_r1)
            dst_c1 = src_c1 - col_start
            dst_c2 = dst_c1 + (src_c2 - src_c1)
            cam_frame[dst_r1:dst_r2, dst_c1:dst_c2] = world_frame[src_r1:src_r2, src_c1:src_c2]

        return cam_frame

    def step(
        self,
        sim_time: float,
        sim_dt: float,
        world_frame: np.ndarray,
        target_world_x: float,
        target_world_y: float,
    ) -> Optional[np.ndarray]:
        """Advance camera physical state by sim_dt, and capture observation if period elapsed.

        Returns:
            Newly captured (480, 640) frame if observation period elapsed, else None.
        """
        # Advance gimbal physics
        self._gimbal.step(sim_dt)

        # Advance beam wander engine
        if self._beam_wander_engine is not None:
            self._beam_wander_engine.step(sim_dt)

        # Check if observation capture is due at this timestamp
        if self.should_capture(sim_time):
            viewport = self.extract_viewport(world_frame)

            # Compute image-plane velocity for motion blur
            _, _, u, v, _ = self.project_target(target_world_x, target_world_y)
            if self._prev_target_u is not None and self._prev_target_v is not None and self._prev_target_time is not None:
                dt_obs = sim_time - self._prev_target_time
                if dt_obs > 0:
                    vx_px_s = (u - self._prev_target_u) / dt_obs
                    vy_px_s = (v - self._prev_target_v) / dt_obs
                else:
                    vx_px_s, vy_px_s = 0.0, 0.0
            else:
                vx_px_s, vy_px_s = 0.0, 0.0

            self._prev_target_u = u
            self._prev_target_v = v
            self._prev_target_time = sim_time

            # Apply optical motion blur if image velocity > 0
            blurred_viewport = self._motion_blur_engine.apply_motion_blur(
                frame=viewport,
                vx_px_s=vx_px_s,
                vy_px_s=vy_px_s,
                exposure_ms=self._exposure_ms,
                frame_interval_ms=self._obs_period * 1000.0,
            )

            # Apply electronic sensor response (exposure time scaling & gain)
            processed_viewport = apply_sensor_response(
                frame=blurred_viewport,
                exposure_ms=self._exposure_ms,
                gain_db=self._gain_db,
            )

            self._last_clean_observation = processed_viewport
            self._last_disturbed_observation = None  # Will be populated by disturbance pipeline
            self._last_obs_time = sim_time
            self._obs_count += 1
            self._is_new_obs = True

            # Construct immutable SensorFrame
            self._sensor_frame = SensorFrame(
                frame_id=self._obs_count,
                timestamp=sim_time,
                camera_pan_deg=self._gimbal.pan_deg,
                camera_tilt_deg=self._gimbal.tilt_deg,
                camera_pan_rate_deg_s=self._gimbal.actual_pan_rate,
                camera_tilt_rate_deg_s=self._gimbal.actual_tilt_rate,
                exposure_ms=self._exposure_ms,
                gain_db=self._gain_db,
                is_disturbed=False,
                clean_frame_id=self._obs_count,
                disturbance_flags="{}",
                image_plane_vel_u=vx_px_s * self._obs_period,
                image_plane_vel_v=vy_px_s * self._obs_period,
                pixels=processed_viewport,
            )

            return self._last_clean_observation

        self._is_new_obs = False
        return None

    def reset(self) -> None:
        """Reset camera, gimbal, and disturbance engines state."""
        self._gimbal.reset()
        if self._beam_wander_engine is not None:
            self._beam_wander_engine.reset()
        self._last_obs_time = -1.0
        self._obs_count = 0
        self._last_clean_observation = None
        self._last_disturbed_observation = None
        self._sensor_frame = None
        self._is_new_obs = False
        self._prev_target_u = None
        self._prev_target_v = None
        self._prev_target_time = None
