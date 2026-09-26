"""
HORIZON Dynamic Region of Interest (ROI) Manager (Phase 6B)
============================================================
Derives dynamic perception search bounds from the EXISTING estimator's
predicted target state and covariance.

Conceptually:
    IMM-EKF prediction
            ↓
       uncertainty (Sigma_pos)
            ↓
       dynamic ROI
            ↓
     existing HYBRID

Behavior:
    - High confidence / low uncertainty: smaller ROI (faster processing)
    - High uncertainty: larger ROI (covers wider dispersion)
    - Target lost / uninitialized / high misses: full-frame recovery

Strict Invariants:
    - No hard-coded ROI sizes (e.g. no 100x100 or 200x200).
    - ROI dynamically depends on: prediction, covariance, image dimensions,
      target geometry, and valid image boundaries.
    - Zero ground-truth leakage: relies strictly on estimator predictions
      and physical candidate geometry.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional, Tuple, Union

import numpy as np

from tracking.estimation.state import EstimatorStatus


@dataclass(frozen=True)
class DynamicROI:
    """Immutable representation of a dynamic Region of Interest."""

    x1: int
    y1: int
    x2: int
    y2: int
    full_frame_w: int
    full_frame_h: int
    is_full_frame: bool
    confidence: float
    sigma_u: float
    sigma_v: float
    target_geometry: Tuple[float, float] = (15.0, 15.0)

    @property
    def width(self) -> int:
        """Width of ROI in pixels."""
        return max(0, self.x2 - self.x1)

    @property
    def height(self) -> int:
        """Height of ROI in pixels."""
        return max(0, self.y2 - self.y1)

    @property
    def bbox(self) -> Tuple[int, int, int, int]:
        """(x1, y1, width, height) bounding box tuple."""
        return (self.x1, self.y1, self.width, self.height)

    @property
    def coordinates(self) -> Tuple[int, int, int, int]:
        """(x1, y1, x2, y2) coordinate tuple."""
        return (self.x1, self.y1, self.x2, self.y2)

    def crop(self, frame: np.ndarray) -> np.ndarray:
        """Slice the frame within this ROI."""
        return frame[self.y1 : self.y2, self.x1 : self.x2]

    def to_global_coords(self, u_local: float, v_local: float) -> Tuple[float, float]:
        """Map subpixel ROI-local coordinate back to full-frame global coordinates."""
        return (float(u_local + self.x1), float(v_local + self.y1))

    def to_global_bbox(
        self, bx: int, by: int, bw: int, bh: int
    ) -> Tuple[int, int, int, int]:
        """Map ROI-local bounding box back to full-frame global bounding box."""
        return (bx + self.x1, by + self.y1, bw, bh)


class DynamicROIManager:
    """Computes dynamic Regions of Interest using estimator predictions and covariance.

    Derives spatial bounds via statistical sigma gating (chi-squared confidence)
    plus physical target geometry margins, clamped to sensor boundaries.
    """

    def __init__(
        self,
        base_sigma_gate: float = 3.5,
        min_geometry_margin_factor: float = 1.5,
        max_misses_for_roi: int = 3,
        min_track_age_for_roi: int = 2,
    ) -> None:
        """Initialize DynamicROIManager.

        Args:
            base_sigma_gate: Statistical standard deviation multiplier for ~99.9%
                containment (default: 3.5).
            min_geometry_margin_factor: Multiplier on target geometry to ensure complete
                PSF and annular background containment (default: 1.5).
            max_misses_for_roi: Number of consecutive misses before reverting to
                full-frame recovery (default: 3).
            min_track_age_for_roi: Minimum number of filter steps before activating
                ROI narrowing (default: 2).
        """
        self._base_sigma_gate = float(base_sigma_gate)
        self._min_geom_factor = float(min_geometry_margin_factor)
        self._max_misses = int(max_misses_for_roi)
        self._min_track_age = int(min_track_age_for_roi)

    def compute_roi(
        self,
        predicted_position: Optional[Tuple[float, float]],
        covariance: Optional[np.ndarray],
        image_shape: Tuple[int, int],
        target_geometry: Optional[Tuple[float, float]] = None,
        confidence: float = 1.0,
        track_age: int = 5,
        consecutive_misses: int = 0,
        filter_status: EstimatorStatus = EstimatorStatus.TRACKING,
    ) -> DynamicROI:
        """Compute dynamic ROI based on prediction, covariance, image shape, and geometry.

        Args:
            predicted_position: Predicted (u, v) beacon centroid in pixels.
            covariance: Predicted (2, 2) or (4, 4) state covariance matrix.
            image_shape: (height, width) of the full sensor frame.
            target_geometry: (width, height) of nominal or last detected beacon spot.
            confidence: Track or detection confidence in [0.0, 1.0].
            track_age: Number of updates in current track.
            consecutive_misses: Consecutive measurement misses.
            filter_status: Current EstimatorStatus.

        Returns:
            DynamicROI instance.
        """
        frame_h, frame_w = int(image_shape[0]), int(image_shape[1])
        geom = target_geometry if target_geometry is not None else (15.0, 15.0)
        target_w, target_h = max(2.0, float(geom[0])), max(2.0, float(geom[1]))

        # Full-frame fallback conditions (Target lost, uninitialized, or recovery)
        is_lost = (
            predicted_position is None
            or filter_status in (EstimatorStatus.UNINITIALIZED, EstimatorStatus.INITIALIZING, EstimatorStatus.RESET)
            or track_age < self._min_track_age
            or consecutive_misses >= self._max_misses
        )

        if is_lost:
            return DynamicROI(
                x1=0,
                y1=0,
                x2=frame_w,
                y2=frame_h,
                full_frame_w=frame_w,
                full_frame_h=frame_h,
                is_full_frame=True,
                confidence=float(confidence),
                sigma_u=float(frame_w / 2.0),
                sigma_v=float(frame_h / 2.0),
                target_geometry=(target_w, target_h),
            )

        u_pred, v_pred = float(predicted_position[0]), float(predicted_position[1])

        # If predicted position lies outside the frame margins, recover full-frame
        if u_pred < 0.0 or u_pred >= frame_w or v_pred < 0.0 or v_pred >= frame_h:
            return DynamicROI(
                x1=0,
                y1=0,
                x2=frame_w,
                y2=frame_h,
                full_frame_w=frame_w,
                full_frame_h=frame_h,
                is_full_frame=True,
                confidence=float(confidence),
                sigma_u=float(frame_w / 2.0),
                sigma_v=float(frame_h / 2.0),
                target_geometry=(target_w, target_h),
            )

        # Extract spatial uncertainties sigma_u, sigma_v from covariance
        if covariance is not None and covariance.ndim == 2 and covariance.shape[0] >= 2 and covariance.shape[1] >= 2:
            sigma_u = float(math.sqrt(max(0.01, float(covariance[0, 0]))))
            sigma_v = float(math.sqrt(max(0.01, float(covariance[1, 1]))))
        else:
            # Fallback uncertainty scaled inversely by confidence
            sigma_u = float(max(1.0, (1.0 - np.clip(confidence, 0.0, 1.0)) * 25.0 + 2.0))
            sigma_v = float(max(1.0, (1.0 - np.clip(confidence, 0.0, 1.0)) * 25.0 + 2.0))

        # Dynamic gating multiplier: expands if consecutive misses occurred
        gate = self._base_sigma_gate + (1.0 * consecutive_misses)

        # Margin derived dynamically from target geometry (ensures complete PSF and annulus)
        margin_u = target_w * self._min_geom_factor
        margin_v = target_h * self._min_geom_factor

        # Half-widths dynamically depending on prediction, covariance, and target geometry
        half_w = gate * sigma_u + margin_u
        half_h = gate * sigma_v + margin_v

        # Ensure half-width at least accommodates the beacon footprint
        half_w = max(half_w, target_w * 1.5)
        half_h = max(half_h, target_h * 1.5)

        # If computed half-width covers more than 80% of sensor dimensions, use full frame
        if half_w >= 0.40 * frame_w or half_h >= 0.40 * frame_h:
            return DynamicROI(
                x1=0,
                y1=0,
                x2=frame_w,
                y2=frame_h,
                full_frame_w=frame_w,
                full_frame_h=frame_h,
                is_full_frame=True,
                confidence=float(confidence),
                sigma_u=sigma_u,
                sigma_v=sigma_v,
                target_geometry=(target_w, target_h),
            )

        # Boundary clamping to valid sensor dimensions
        x1 = max(0, int(math.floor(u_pred - half_w)))
        y1 = max(0, int(math.floor(v_pred - half_h)))
        x2 = min(frame_w, int(math.ceil(u_pred + half_w)))
        y2 = min(frame_h, int(math.ceil(v_pred + half_h)))

        # Sanity check: if clipped to degenerate slice, fall back to full frame
        if (x2 - x1) < int(target_w) or (y2 - y1) < int(target_h):
            return DynamicROI(
                x1=0,
                y1=0,
                x2=frame_w,
                y2=frame_h,
                full_frame_w=frame_w,
                full_frame_h=frame_h,
                is_full_frame=True,
                confidence=float(confidence),
                sigma_u=sigma_u,
                sigma_v=sigma_v,
                target_geometry=(target_w, target_h),
            )

        return DynamicROI(
            x1=x1,
            y1=y1,
            x2=x2,
            y2=y2,
            full_frame_w=frame_w,
            full_frame_h=frame_h,
            is_full_frame=False,
            confidence=float(confidence),
            sigma_u=sigma_u,
            sigma_v=sigma_v,
            target_geometry=(target_w, target_h),
        )
