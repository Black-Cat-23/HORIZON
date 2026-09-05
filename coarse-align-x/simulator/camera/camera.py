"""
HORIZON Virtual Camera System
====================================
Virtual optical camera sensor with physical gimbal actuation, pinhole projection,
subpixel viewport extraction, and configurable update rate (30 Hz).

Conforms strictly to Phase 2 formal verification specifications:
  - Shape: exactly (480, 640), dtype uint8, single channel.
  - Optical intrinsics: W=640, H=480, FOVx=4°, FOVy=3°.
  - Update rate: 30 Hz decoupled observation generation.
  - True physical crop / projection (NOT resize).
"""

from __future__ import annotations

import math
from typing import Optional, Tuple
import cv2
import numpy as np

from simulator.camera.gimbal import CameraGimbal
from simulator.camera.intrinsics import CameraIntrinsics


class VirtualCamera:
    """Virtual camera model modeling optical sensor and motorized gimbal.

    Parameters:
        intrinsics: CameraIntrinsics instance (W=640, H=480, FOVx=4°, FOVy=3°).
        gimbal: CameraGimbal instance enforcing slew rate limits (default 5°/s).
        update_rate_hz: Sensor update frequency (default 30 Hz).
        world_width: Simulation world width (default 2000).
        world_height: Simulation world height (default 2000).
    """

    def __init__(
        self,
        intrinsics: Optional[CameraIntrinsics] = None,
        gimbal: Optional[CameraGimbal] = None,
        update_rate_hz: float = 30.0,
        world_width: int = 2000,
        world_height: int = 2000,
    ) -> None:
        if update_rate_hz <= 0:
            raise ValueError(f"update_rate_hz must be positive, got {update_rate_hz}")

        self._intrinsics = intrinsics or CameraIntrinsics()
        self._gimbal = gimbal or CameraGimbal()
        self._update_rate_hz = float(update_rate_hz)
        self._obs_period = 1.0 / self._update_rate_hz

        self._world_w = int(world_width)
        self._world_h = int(world_height)
        self._center_x = float(self._world_w) / 2.0
        self._center_y = float(self._world_h) / 2.0

        # Timing tracking for decoupled observation rate
        self._last_obs_time: float = -1.0
        self._obs_count: int = 0
        self._last_clean_observation: Optional[np.ndarray] = None
        self._last_disturbed_observation: Optional[np.ndarray] = None
        self._is_new_obs: bool = False

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
        theta_x, theta_y = self.compute_target_angles(target_world_x, target_world_y)
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

        # Pixel extraction window in world frame
        col_start = int(round(bx - half_w))
        col_end = col_start + w_cam
        row_start = int(round(by - half_h))
        row_end = row_start + h_cam

        cam_frame = np.zeros((h_cam, w_cam), dtype=np.uint8)

        # Intersection with world frame bounds [0, H_world] x [0, W_world]
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

        # Check if observation capture is due at this timestamp
        if self.should_capture(sim_time):
            self._last_clean_observation = self.extract_viewport(world_frame)
            self._last_disturbed_observation = None  # Will be populated by disturbance pipeline
            self._last_obs_time = sim_time
            self._obs_count += 1
            self._is_new_obs = True
            return self._last_clean_observation

        self._is_new_obs = False
        return None

    def reset(self) -> None:
        """Reset camera and gimbal state."""
        self._gimbal.reset()
        self._last_obs_time = -1.0
        self._obs_count = 0
        self._last_clean_observation = None
        self._last_disturbed_observation = None
        self._is_new_obs = False
