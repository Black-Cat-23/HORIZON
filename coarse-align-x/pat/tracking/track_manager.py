"""
PAT Track Manager & Pointing Error Calculation.
HORIZON Phase 6
"""

import math
from typing import Tuple, Dict, Any
import numpy as np


class PATTrackManager:
    """
    Manages tracking state calculations and calculates angular pointing errors
    between estimated target position and camera optical boresight using exact
    pinhole inverse-tangent optics.
    Zero ground truth leakage: consumes only StateEstimate and CameraState.
    """

    def __init__(
        self,
        image_width_px: int = 640,
        image_height_px: int = 480,
        fov_pan_deg: float = 4.0,
        fov_tilt_deg: float = 3.0,
    ):
        self.image_width_px = image_width_px
        self.image_height_px = image_height_px
        self.fov_pan_deg = fov_pan_deg
        self.fov_tilt_deg = fov_tilt_deg

        self.cx_px = image_width_px / 2.0
        self.cy_px = image_height_px / 2.0

        # Exact focal lengths from optical FOVs (px)
        self.fx_px = (image_width_px / 2.0) / math.tan(math.radians(fov_pan_deg / 2.0))
        self.fy_px = (image_height_px / 2.0) / math.tan(math.radians(fov_tilt_deg / 2.0))

        # Linear approximation scale factors for fallbacks (deg/px)
        self.deg_per_px_pan = fov_pan_deg / image_width_px
        self.deg_per_px_tilt = fov_tilt_deg / image_height_px

    def compute_pointing_error(
        self, estimated_u_px: float, estimated_v_px: float
    ) -> Tuple[float, float]:
        """
        Computes pointing angular error (deg) from estimated target image position relative to optical center.
        Uses exact pinhole inverse-tangent optics.
        
        Returns:
            Tuple[pan_error_deg, tilt_error_deg]
        """
        if (estimated_u_px == 0.0 and estimated_v_px == 0.0) or not (np.isfinite(estimated_u_px) and np.isfinite(estimated_v_px)):
            return (0.0, 0.0)

        # Error in pixels (target relative to camera center)
        error_u_px = estimated_u_px - self.cx_px
        error_v_px = estimated_v_px - self.cy_px

        # Exact pinhole inverse-tangent angle calculation (deg)
        pan_error_deg = math.degrees(math.atan(error_u_px / self.fx_px))
        tilt_error_deg = math.degrees(math.atan(error_v_px / self.fy_px))

        return (pan_error_deg, tilt_error_deg)

    def compute_angular_velocity_estimate(
        self, estimated_vx_px_s: float, estimated_vy_px_s: float
    ) -> Tuple[float, float]:
        """
        Computes target angular velocity estimate (deg/s) from state estimation velocity vector.
        Uses pinhole focal length angular differential scaling.
        """
        if not (np.isfinite(estimated_vx_px_s) and np.isfinite(estimated_vy_px_s)):
            return (0.0, 0.0)

        pan_vel_deg_s = math.degrees(math.atan(estimated_vx_px_s / self.fx_px))
        tilt_vel_deg_s = math.degrees(math.atan(estimated_vy_px_s / self.fy_px))
        return (pan_vel_deg_s, tilt_vel_deg_s)
