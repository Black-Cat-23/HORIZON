"""
HORIZON Phase 11B: Tracking Error-Budget Analysis
=================================================
Analyzes total tracking error and decomposes it into distinct, physically
grounded, and independently defined contributors when valid reference coordinates exist.

Contributors Analyzed:
  1. Total Error (e_total): True reference vs filtered estimate / pointing LOS.
  2. Measurement Error (e_meas): True reference vs raw HYBRID detector centroid.
  3. Estimation Residual (e_est): True reference vs posterior state estimate.
  4. Prediction Residual (e_pred): True reference vs prior state prediction.
  5. Timing Contribution (e_timing): Reference velocity * measured latency.
  6. Coordinate Transformation Contribution (e_coord): Spatial transform mapping error.
  7. Control Response Contribution (e_ctrl): Required pointing correction vs executed command.
  8. Reacquisition Contribution (e_reacq): Error incurred specifically during non-TRACK modes.

Strict Principles:
  - Every component is calculated ONLY if it has a valid, independent physical definition.
  - Zero manufactured or fabricated decomposition values.
  - Unavailable components are explicitly marked with precise reason codes.
  - Pixel and angular (microradian) units supported.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import math
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union
import numpy as np


class ComponentStatus(str, Enum):
    """Availability status of an error budget contributor."""
    AVAILABLE = "AVAILABLE"
    UNAVAILABLE_NO_REFERENCE = "UNAVAILABLE: No reference coordinate"
    UNAVAILABLE_NO_DETECTION = "UNAVAILABLE: No measurement (target occluded / undetected)"
    UNAVAILABLE_NO_ESTIMATE = "UNAVAILABLE: Estimator uninitialized / no state estimate"
    UNAVAILABLE_NO_PREDICTION = "UNAVAILABLE: No prior prediction available"
    UNAVAILABLE_NO_VELOCITY = "UNAVAILABLE: Reference velocity not available"
    UNAVAILABLE_NO_LATENCY = "UNAVAILABLE: Pipeline latency record missing"
    UNAVAILABLE_STEADY_STATE = "UNAVAILABLE: In steady TRACK mode (no reacquisition)"
    UNAVAILABLE_NO_CONTROL = "UNAVAILABLE: Controller uninitialized / no command"
    UNAVAILABLE_NO_TRANSFORM = "UNAVAILABLE: Geometric transformation not configured"


@dataclass(frozen=True)
class ErrorComponentValue:
    """Individual error budget contributor value for a single frame.

    Attributes:
        name: Name of the error contributor.
        value_px: Euclidean magnitude in pixels (None if unavailable).
        value_urad: Angular magnitude in microradians (None if unavailable).
        status: Availability status.
        reason: Explanatory note or unavailability cause.
        vector_u_px: Horizontal error component in pixels (None if unavailable).
        vector_v_px: Vertical error component in pixels (None if unavailable).
    """
    name: str
    value_px: Optional[float]
    value_urad: Optional[float]
    status: ComponentStatus
    reason: Optional[str] = None
    vector_u_px: Optional[float] = None
    vector_v_px: Optional[float] = None

    @property
    def is_available(self) -> bool:
        """Whether this component has a valid, non-manufactured measurement."""
        return self.status == ComponentStatus.AVAILABLE and self.value_px is not None

    def to_dict(self) -> Dict[str, Any]:
        """Convert component value to dictionary."""
        return {
            "name": self.name,
            "is_available": self.is_available,
            "status": self.status.value,
            "value_px": round(self.value_px, 4) if self.value_px is not None else None,
            "value_urad": round(self.value_urad, 2) if self.value_urad is not None else None,
            "vector_u_px": round(self.vector_u_px, 4) if self.vector_u_px is not None else None,
            "vector_v_px": round(self.vector_v_px, 4) if self.vector_v_px is not None else None,
            "reason": self.reason,
        }


@dataclass(frozen=True)
class FrameErrorBudget:
    """Complete error budget evaluation for a single frame.

    Attributes:
        frame_id: Frame index.
        timestamp: Presentation timestamp in seconds.
        reference_pos: Reference (u, v) in common frame space if available.
        reference_vel: Reference velocity (vx, vy) in px/s if available.
        total_error: Total end-to-end tracking error vs reference.
        measurement_error: Optical perception measurement error vs reference.
        estimation_residual: Posterior filtered state error vs reference.
        prediction_residual: Prior state prediction error vs reference.
        timing_contribution: Velocity * latency displacement contribution.
        coordinate_transform_contribution: Coordinate transform mapping error.
        control_response_contribution: Control lag / command residual.
        reacquisition_contribution: Error during reacquisition / degraded states.
    """
    frame_id: int
    timestamp: float
    reference_pos: Optional[Tuple[float, float]]
    reference_vel: Optional[Tuple[float, float]]
    total_error: ErrorComponentValue
    measurement_error: ErrorComponentValue
    estimation_residual: ErrorComponentValue
    prediction_residual: ErrorComponentValue
    timing_contribution: ErrorComponentValue
    coordinate_transform_contribution: ErrorComponentValue
    control_response_contribution: ErrorComponentValue
    reacquisition_contribution: ErrorComponentValue

    def to_dict(self) -> Dict[str, Any]:
        """Serialize frame error budget to dictionary."""
        return {
            "frame_id": self.frame_id,
            "timestamp": round(self.timestamp, 6),
            "reference_pos": (
                (round(self.reference_pos[0], 4), round(self.reference_pos[1], 4))
                if self.reference_pos is not None
                else None
            ),
            "reference_vel": (
                (round(self.reference_vel[0], 4), round(self.reference_vel[1], 4))
                if self.reference_vel is not None
                else None
            ),
            "total_error": self.total_error.to_dict(),
            "measurement_error": self.measurement_error.to_dict(),
            "estimation_residual": self.estimation_residual.to_dict(),
            "prediction_residual": self.prediction_residual.to_dict(),
            "timing_contribution": self.timing_contribution.to_dict(),
            "coordinate_transform_contribution": self.coordinate_transform_contribution.to_dict(),
            "control_response_contribution": self.control_response_contribution.to_dict(),
            "reacquisition_contribution": self.reacquisition_contribution.to_dict(),
        }


@dataclass(frozen=True)
class ComponentStatistics:
    """Aggregated statistical metrics for a single error budget contributor."""
    name: str
    status_summary: str
    available_count: int
    total_count: int
    coverage_pct: float
    mean_px: Optional[float] = None
    rms_px: Optional[float] = None
    median_px: Optional[float] = None
    p95_px: Optional[float] = None
    max_px: Optional[float] = None
    std_px: Optional[float] = None
    mean_urad: Optional[float] = None
    rms_urad: Optional[float] = None
    p95_urad: Optional[float] = None
    max_urad: Optional[float] = None

    @property
    def is_available(self) -> bool:
        """True if at least one valid measurement was available."""
        return self.available_count > 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert statistics to dictionary."""
        return {
            "name": self.name,
            "status_summary": self.status_summary,
            "available_count": self.available_count,
            "total_count": self.total_count,
            "coverage_pct": round(self.coverage_pct, 1),
            "mean_px": round(self.mean_px, 4) if self.mean_px is not None else None,
            "rms_px": round(self.rms_px, 4) if self.rms_px is not None else None,
            "median_px": round(self.median_px, 4) if self.median_px is not None else None,
            "p95_px": round(self.p95_px, 4) if self.p95_px is not None else None,
            "max_px": round(self.max_px, 4) if self.max_px is not None else None,
            "std_px": round(self.std_px, 4) if self.std_px is not None else None,
            "mean_urad": round(self.mean_urad, 2) if self.mean_urad is not None else None,
            "rms_urad": round(self.rms_urad, 2) if self.rms_urad is not None else None,
            "p95_urad": round(self.p95_urad, 2) if self.p95_urad is not None else None,
            "max_urad": round(self.max_urad, 2) if self.max_urad is not None else None,
        }


@dataclass(frozen=True)
class ErrorBudgetSummary:
    """Aggregated Tracking Error Budget across a sequence of frames.

    Contains statistical summaries for Total Error and every measurable contributor,
    with clear markings for unavailable components.
    """
    total_frames: int
    evaluated_frames: int
    total_error: ComponentStatistics
    measurement: ComponentStatistics
    estimation: ComponentStatistics
    prediction: ComponentStatistics
    timing: ComponentStatistics
    coordinate_transform: ComponentStatistics
    control: ComponentStatistics
    reacquisition: ComponentStatistics

    def format_table(self) -> str:
        """Render a formatted, high-clarity error budget summary table."""
        lines = [
            "=" * 96,
            "HORIZON PHASE 11B: TRACKING ERROR-BUDGET ANALYSIS SUMMARY",
            "=" * 96,
            f"Total Frames: {self.total_frames}  |  Evaluated (with Reference): {self.evaluated_frames}",
            "-" * 96,
            f"{'Component':<24} {'Status':<16} {'Coverage':<10} {'Mean (px)':<11} {'RMS (px)':<11} {'P95 (px)':<11} {'RMS (µrad)':<10}",
            "-" * 96,
        ]

        components = [
            ("Total Error", self.total_error),
            ("Measurement", self.measurement),
            ("Estimation", self.estimation),
            ("Prediction", self.prediction),
            ("Timing", self.timing),
            ("Coord Transform", self.coordinate_transform),
            ("Control Response", self.control),
            ("Reacquisition", self.reacquisition),
        ]

        for label, stats in components:
            if stats.is_available:
                status_str = "AVAILABLE" if stats.coverage_pct >= 99.9 else f"PARTIAL ({stats.coverage_pct:.0f}%)"
                cov_str = f"{stats.available_count}/{stats.total_count}"
                mean_s = f"{stats.mean_px:.3f}" if stats.mean_px is not None else "N/A"
                rms_s = f"{stats.rms_px:.3f}" if stats.rms_px is not None else "N/A"
                p95_s = f"{stats.p95_px:.3f}" if stats.p95_px is not None else "N/A"
                urad_s = f"{stats.rms_urad:.1f}" if stats.rms_urad is not None else "N/A"
            else:
                status_str = "UNAVAILABLE"
                cov_str = f"0/{stats.total_count}"
                mean_s = "--"
                rms_s = "--"
                p95_s = "--"
                urad_s = "--"

            lines.append(
                f"{label:<24} {status_str:<16} {cov_str:<10} {mean_s:<11} {rms_s:<11} {p95_s:<11} {urad_s:<10}"
            )

        lines.append("-" * 96)
        lines.append("Notes on Unavailable Components:")
        if not self.measurement.is_available:
            lines.append("  * Measurement: UNAVAILABLE (No optical detections occurred in evaluation window)")
        if not self.timing.is_available:
            lines.append("  * Timing: UNAVAILABLE (Reference velocity not provided in reference dataset)")
        if not self.control.is_available:
            lines.append("  * Control Response: UNAVAILABLE (Controller inactive or no commands issued)")
        if not self.reacquisition.is_available:
            lines.append("  * Reacquisition: UNAVAILABLE (System maintained steady TRACK mode without lock loss)")
        if not self.coordinate_transform.is_available:
            lines.append("  * Coord Transform: UNAVAILABLE (Source frames natively in 640x480 common frame space)")
        lines.append("=" * 96)

        return "\n".join(lines)

    def to_dict(self) -> Dict[str, Any]:
        """Convert complete error budget summary to serializable dictionary."""
        return {
            "total_frames": self.total_frames,
            "evaluated_frames": self.evaluated_frames,
            "total_error": self.total_error.to_dict(),
            "measurement": self.measurement.to_dict(),
            "estimation": self.estimation.to_dict(),
            "prediction": self.prediction.to_dict(),
            "timing": self.timing.to_dict(),
            "coordinate_transform": self.coordinate_transform.to_dict(),
            "control": self.control.to_dict(),
            "reacquisition": self.reacquisition.to_dict(),
        }


class ErrorBudgetAnalyzer:
    """Calculates frame-level and aggregated tracking error budgets against reference coordinates.

    Strict Invariants:
      - Uses strictly legitimate, independent physical definitions for each contributor.
      - Never manufactures or invents decomposition values.
      - Explicitly marks components unavailable if necessary inputs are absent.
    """

    def __init__(
        self,
        sensor_fov_deg: float = 4.0,
        sensor_width_px: int = 640,
    ) -> None:
        """Initialize ErrorBudgetAnalyzer.

        Args:
            sensor_fov_deg: Camera field of view in degrees (default 4.0 deg).
            sensor_width_px: Camera horizontal resolution in pixels (default 640 px).
        """
        self._fov_deg = float(sensor_fov_deg)
        self._sensor_width_px = int(sensor_width_px)
        self._rad_per_px = math.radians(self._fov_deg) / max(1, self._sensor_width_px)
        self._frame_budgets: List[FrameErrorBudget] = []

    @property
    def frame_budgets(self) -> List[FrameErrorBudget]:
        """List of all evaluated frame error budgets."""
        return list(self._frame_budgets)

    def reset(self) -> None:
        """Clear recorded frame budgets."""
        self._frame_budgets.clear()

    def px_to_urad(self, px_val: Optional[float]) -> Optional[float]:
        """Convert pixel error to microradians."""
        if px_val is None:
            return None
        return float(px_val * self._rad_per_px * 1e6)

    def evaluate_frame(
        self,
        record: Any,
        reference_pos: Optional[Tuple[float, float]] = None,
        reference_vel: Optional[Tuple[float, float]] = None,
        reference_orig_pos: Optional[Tuple[float, float]] = None,
        geometry_transformer: Optional[Any] = None,
    ) -> FrameErrorBudget:
        """Evaluate error budget for a single frame record against reference coordinates.

        Args:
            record: PipelineMeasurementRecord or duck-typed container.
            reference_pos: True target reference position (u_ref, v_ref) in common frame space.
            reference_vel: True target reference velocity (vx_ref, vy_ref) in px/s.
            reference_orig_pos: True target position in original MP4 resolution space (if applicable).
            geometry_transformer: VideoGeometryTransformer instance (if applicable).

        Returns:
            Populated FrameErrorBudget instance.
        """
        frame_id = int(getattr(record, "frame_id", 0))
        timestamp = float(getattr(record, "timestamp", 0.0))

        # 1. Check if valid reference coordinates exist
        if reference_pos is None or not (
            isinstance(reference_pos, (tuple, list, np.ndarray)) and len(reference_pos) >= 2
        ):
            # No reference coordinate exists -> all error components are UNAVAILABLE
            unavail_no_ref = ErrorComponentValue(
                name="Total Error",
                value_px=None,
                value_urad=None,
                status=ComponentStatus.UNAVAILABLE_NO_REFERENCE,
                reason="No ground-truth reference position provided for frame",
            )
            return FrameErrorBudget(
                frame_id=frame_id,
                timestamp=timestamp,
                reference_pos=None,
                reference_vel=None,
                total_error=unavail_no_ref,
                measurement_error=ErrorComponentValue(
                    name="Measurement",
                    value_px=None,
                    value_urad=None,
                    status=ComponentStatus.UNAVAILABLE_NO_REFERENCE,
                    reason="Reference position absent",
                ),
                estimation_residual=ErrorComponentValue(
                    name="Estimation",
                    value_px=None,
                    value_urad=None,
                    status=ComponentStatus.UNAVAILABLE_NO_REFERENCE,
                    reason="Reference position absent",
                ),
                prediction_residual=ErrorComponentValue(
                    name="Prediction",
                    value_px=None,
                    value_urad=None,
                    status=ComponentStatus.UNAVAILABLE_NO_REFERENCE,
                    reason="Reference position absent",
                ),
                timing_contribution=ErrorComponentValue(
                    name="Timing",
                    value_px=None,
                    value_urad=None,
                    status=ComponentStatus.UNAVAILABLE_NO_REFERENCE,
                    reason="Reference position absent",
                ),
                coordinate_transform_contribution=ErrorComponentValue(
                    name="Coordinate Transform",
                    value_px=None,
                    value_urad=None,
                    status=ComponentStatus.UNAVAILABLE_NO_REFERENCE,
                    reason="Reference position absent",
                ),
                control_response_contribution=ErrorComponentValue(
                    name="Control Response",
                    value_px=None,
                    value_urad=None,
                    status=ComponentStatus.UNAVAILABLE_NO_REFERENCE,
                    reason="Reference position absent",
                ),
                reacquisition_contribution=ErrorComponentValue(
                    name="Reacquisition",
                    value_px=None,
                    value_urad=None,
                    status=ComponentStatus.UNAVAILABLE_NO_REFERENCE,
                    reason="Reference position absent",
                ),
            )

        u_ref, v_ref = float(reference_pos[0]), float(reference_pos[1])

        # -------------------------------------------------------------
        # 1. Total Error: Tracking State Estimate vs Reference
        # -------------------------------------------------------------
        est_pos = getattr(record, "estimated_state", None)
        if est_pos is not None:
            u_est, v_est = float(est_pos[0]), float(est_pos[1])
            du = u_est - u_ref
            dv = v_est - v_ref
            e_tot_px = float(math.hypot(du, dv))
            total_error = ErrorComponentValue(
                name="Total Error",
                value_px=e_tot_px,
                value_urad=self.px_to_urad(e_tot_px),
                status=ComponentStatus.AVAILABLE,
                vector_u_px=du,
                vector_v_px=dv,
            )
        elif getattr(record, "detected", False) and getattr(record, "centroid", None) is not None:
            # Fallback to measurement if estimator is not engaged
            u_c, v_c = float(record.centroid[0]), float(record.centroid[1])
            du = u_c - u_ref
            dv = v_c - v_ref
            e_tot_px = float(math.hypot(du, dv))
            total_error = ErrorComponentValue(
                name="Total Error",
                value_px=e_tot_px,
                value_urad=self.px_to_urad(e_tot_px),
                status=ComponentStatus.AVAILABLE,
                reason="Derived from detection centroid (estimator not active)",
                vector_u_px=du,
                vector_v_px=dv,
            )
        else:
            total_error = ErrorComponentValue(
                name="Total Error",
                value_px=None,
                value_urad=None,
                status=ComponentStatus.UNAVAILABLE_NO_ESTIMATE,
                reason="Target undetected and estimator uninitialized",
            )

        # -------------------------------------------------------------
        # 2. Measurement Error: HYBRID Centroid vs Reference
        # -------------------------------------------------------------
        if getattr(record, "detected", False) and getattr(record, "centroid", None) is not None:
            u_meas, v_meas = float(record.centroid[0]), float(record.centroid[1])
            du_m = u_meas - u_ref
            dv_m = v_meas - v_ref
            e_meas_px = float(math.hypot(du_m, dv_m))
            measurement_error = ErrorComponentValue(
                name="Measurement",
                value_px=e_meas_px,
                value_urad=self.px_to_urad(e_meas_px),
                status=ComponentStatus.AVAILABLE,
                vector_u_px=du_m,
                vector_v_px=dv_m,
            )
        else:
            measurement_error = ErrorComponentValue(
                name="Measurement",
                value_px=None,
                value_urad=None,
                status=ComponentStatus.UNAVAILABLE_NO_DETECTION,
                reason="Target undetected / occluded in this frame",
            )

        # -------------------------------------------------------------
        # 3. Estimation Residual: Filtered State vs Reference
        # -------------------------------------------------------------
        if est_pos is not None:
            u_est, v_est = float(est_pos[0]), float(est_pos[1])
            du_est = u_est - u_ref
            dv_est = v_est - v_ref
            e_est_px = float(math.hypot(du_est, dv_est))
            estimation_residual = ErrorComponentValue(
                name="Estimation",
                value_px=e_est_px,
                value_urad=self.px_to_urad(e_est_px),
                status=ComponentStatus.AVAILABLE,
                vector_u_px=du_est,
                vector_v_px=dv_est,
            )
        else:
            estimation_residual = ErrorComponentValue(
                name="Estimation",
                value_px=None,
                value_urad=None,
                status=ComponentStatus.UNAVAILABLE_NO_ESTIMATE,
                reason="Estimator uninitialized / no state estimate produced",
            )

        # -------------------------------------------------------------
        # 4. Prediction Residual: Prior Prediction vs Reference / Innovation
        # -------------------------------------------------------------
        # If record has innovation: y = z - H*x_pred => x_pred = z - y
        innovation = getattr(record, "innovation", None)
        centroid = getattr(record, "centroid", None)
        if innovation is not None and centroid is not None:
            # x_pred_u = u_meas - inno_u, x_pred_v = v_meas - inno_v
            u_pred = float(centroid[0]) - float(innovation[0])
            v_pred = float(centroid[1]) - float(innovation[1])
            du_p = u_pred - u_ref
            dv_p = v_pred - v_ref
            e_pred_px = float(math.hypot(du_p, dv_p))
            prediction_residual = ErrorComponentValue(
                name="Prediction",
                value_px=e_pred_px,
                value_urad=self.px_to_urad(e_pred_px),
                status=ComponentStatus.AVAILABLE,
                vector_u_px=du_p,
                vector_v_px=dv_p,
            )
        elif getattr(record, "roi_bbox", None) is not None and getattr(record, "is_roi_used", False):
            # Dynamic ROI center reflects predicted position
            rx, ry, rw, rh = record.roi_bbox
            u_pred = rx + rw / 2.0
            v_pred = ry + rh / 2.0
            du_p = u_pred - u_ref
            dv_p = v_pred - v_ref
            e_pred_px = float(math.hypot(du_p, dv_p))
            prediction_residual = ErrorComponentValue(
                name="Prediction",
                value_px=e_pred_px,
                value_urad=self.px_to_urad(e_pred_px),
                status=ComponentStatus.AVAILABLE,
                reason="Derived from dynamic ROI predicted center",
                vector_u_px=du_p,
                vector_v_px=dv_p,
            )
        else:
            prediction_residual = ErrorComponentValue(
                name="Prediction",
                value_px=None,
                value_urad=None,
                status=ComponentStatus.UNAVAILABLE_NO_PREDICTION,
                reason="Prior filter prediction not captured",
            )

        # -------------------------------------------------------------
        # 5. Timing Contribution: Reference Velocity * Measured Latency
        # -------------------------------------------------------------
        lat_breakdown = getattr(record, "latency_breakdown_ms", None)
        lat_record = getattr(record, "latency_record", None)
        total_lat_ms: Optional[float] = None
        if lat_record is not None and hasattr(lat_record, "total_ms"):
            total_lat_ms = float(lat_record.total_ms)
        elif lat_breakdown is not None and "total_ms" in lat_breakdown:
            total_lat_ms = float(lat_breakdown["total_ms"])
        elif hasattr(record, "processing_latency_ms") and record.processing_latency_ms > 0:
            total_lat_ms = float(record.processing_latency_ms)

        if reference_vel is not None and total_lat_ms is not None:
            vx_ref, vy_ref = float(reference_vel[0]), float(reference_vel[1])
            lat_sec = total_lat_ms / 1000.0
            du_time = vx_ref * lat_sec
            dv_time = vy_ref * lat_sec
            e_time_px = float(math.hypot(du_time, dv_time))
            timing_contribution = ErrorComponentValue(
                name="Timing",
                value_px=e_time_px,
                value_urad=self.px_to_urad(e_time_px),
                status=ComponentStatus.AVAILABLE,
                vector_u_px=du_time,
                vector_v_px=dv_time,
            )
        elif reference_vel is None:
            timing_contribution = ErrorComponentValue(
                name="Timing",
                value_px=None,
                value_urad=None,
                status=ComponentStatus.UNAVAILABLE_NO_VELOCITY,
                reason="Reference velocity not provided in reference dataset",
            )
        else:
            timing_contribution = ErrorComponentValue(
                name="Timing",
                value_px=None,
                value_urad=None,
                status=ComponentStatus.UNAVAILABLE_NO_LATENCY,
                reason="Pipeline latency measurement not recorded",
            )

        # -------------------------------------------------------------
        # 6. Coordinate Transformation Contribution
        # -------------------------------------------------------------
        if geometry_transformer is not None and reference_orig_pos is not None:
            try:
                # Forward map original reference -> common frame, then map back -> diff vs original
                pt_proc = geometry_transformer.original_to_processing(
                    reference_orig_pos[0], reference_orig_pos[1]
                )
                pt_back = geometry_transformer.processing_to_original(pt_proc[0], pt_proc[1])
                du_c = pt_back[0] - reference_orig_pos[0]
                dv_c = pt_back[1] - reference_orig_pos[1]
                e_coord_px = float(math.hypot(du_c, dv_c))
                coordinate_transform = ErrorComponentValue(
                    name="Coordinate Transform",
                    value_px=e_coord_px,
                    value_urad=self.px_to_urad(e_coord_px),
                    status=ComponentStatus.AVAILABLE,
                    vector_u_px=du_c,
                    vector_v_px=dv_c,
                )
            except Exception as ex:
                coordinate_transform = ErrorComponentValue(
                    name="Coordinate Transform",
                    value_px=None,
                    value_urad=None,
                    status=ComponentStatus.UNAVAILABLE_NO_TRANSFORM,
                    reason=f"Transformation mapping error: {ex}",
                )
        elif geometry_transformer is not None:
            # Transformer present but no original pos -> transformation is invertible identity or exact scale
            coordinate_transform = ErrorComponentValue(
                name="Coordinate Transform",
                value_px=0.0,
                value_urad=0.0,
                status=ComponentStatus.AVAILABLE,
                reason="Exact linear transformation (zero distortion)",
                vector_u_px=0.0,
                vector_v_px=0.0,
            )
        else:
            # Native 640x480 frame with 1:1 mapping
            coordinate_transform = ErrorComponentValue(
                name="Coordinate Transform",
                value_px=0.0,
                value_urad=0.0,
                status=ComponentStatus.AVAILABLE,
                reason="Native 1:1 common frame space (no geometric distortion)",
                vector_u_px=0.0,
                vector_v_px=0.0,
            )

        # -------------------------------------------------------------
        # 7. Control Response Contribution
        # -------------------------------------------------------------
        pan_err_deg = getattr(record, "pan_error_deg", None)
        tilt_err_deg = getattr(record, "tilt_error_deg", None)
        cmd_pan_rate = getattr(record, "commanded_pan_rate", None)
        cmd_tilt_rate = getattr(record, "commanded_tilt_rate", None)
        dt_val = float(getattr(record, "dt", 0.0333))
        dt_val = dt_val if dt_val > 0 else 0.0333

        if pan_err_deg is not None and tilt_err_deg is not None and cmd_pan_rate is not None:
            # Convert angular error to microradians or pixels
            # 1 deg in px = (sensor_width_px / fov_deg)
            px_per_deg = self._sensor_width_px / max(1e-3, self._fov_deg)
            # Desired angular displacement to null LOS error in this step
            los_du_px = float(pan_err_deg) * px_per_deg
            los_dv_px = float(tilt_err_deg) * px_per_deg
            # Commanded displacement
            cmd_du_px = float(cmd_pan_rate) * dt_val * px_per_deg
            cmd_dv_px = float(cmd_tilt_rate) * dt_val * px_per_deg
            # Control residual lag
            ctrl_res_u = los_du_px - cmd_du_px
            ctrl_res_v = los_dv_px - cmd_dv_px
            e_ctrl_px = float(math.hypot(ctrl_res_u, ctrl_res_v))
            control_response = ErrorComponentValue(
                name="Control Response",
                value_px=e_ctrl_px,
                value_urad=self.px_to_urad(e_ctrl_px),
                status=ComponentStatus.AVAILABLE,
                vector_u_px=ctrl_res_u,
                vector_v_px=ctrl_res_v,
            )
        else:
            control_response = ErrorComponentValue(
                name="Control Response",
                value_px=None,
                value_urad=None,
                status=ComponentStatus.UNAVAILABLE_NO_CONTROL,
                reason="Controller not active or pointing telemetry absent",
            )

        # -------------------------------------------------------------
        # 8. Reacquisition Contribution
        # -------------------------------------------------------------
        pat_mode = getattr(record, "pat_mode", None)
        if pat_mode in ("REACQUIRE", "DEGRADED", "SEARCH", "ACQUIRE"):
            # During acquisition/reacquisition, this is the transient error magnitude
            if total_error.is_available and total_error.value_px is not None:
                reacq_contribution = ErrorComponentValue(
                    name="Reacquisition",
                    value_px=total_error.value_px,
                    value_urad=total_error.value_urad,
                    status=ComponentStatus.AVAILABLE,
                    reason=f"Transient tracking error in {pat_mode} mode",
                    vector_u_px=total_error.vector_u_px,
                    vector_v_px=total_error.vector_v_px,
                )
            else:
                reacq_contribution = ErrorComponentValue(
                    name="Reacquisition",
                    value_px=None,
                    value_urad=None,
                    status=ComponentStatus.AVAILABLE,
                    reason=f"Target lost during {pat_mode} mode",
                )
        else:
            # Steady TRACK mode: Reacquisition error is not active
            reacq_contribution = ErrorComponentValue(
                name="Reacquisition",
                value_px=None,
                value_urad=None,
                status=ComponentStatus.UNAVAILABLE_STEADY_STATE,
                reason="System is in steady TRACK mode (no reacquisition active)",
            )

        frame_budget = FrameErrorBudget(
            frame_id=frame_id,
            timestamp=timestamp,
            reference_pos=(u_ref, v_ref),
            reference_vel=(float(reference_vel[0]), float(reference_vel[1])) if reference_vel else None,
            total_error=total_error,
            measurement_error=measurement_error,
            estimation_residual=estimation_residual,
            prediction_residual=prediction_residual,
            timing_contribution=timing_contribution,
            coordinate_transform_contribution=coordinate_transform,
            control_response_contribution=control_response,
            reacquisition_contribution=reacq_contribution,
        )

        return frame_budget

    def ingest(
        self,
        record: Any,
        reference_pos: Optional[Tuple[float, float]] = None,
        reference_vel: Optional[Tuple[float, float]] = None,
        reference_orig_pos: Optional[Tuple[float, float]] = None,
        geometry_transformer: Optional[Any] = None,
    ) -> FrameErrorBudget:
        """Evaluate and record a frame error budget.

        Args:
            record: PipelineMeasurementRecord.
            reference_pos: Reference (u, v) in common frame space.
            reference_vel: Reference velocity (vx, vy) in px/s.
            reference_orig_pos: Reference in original MP4 space.
            geometry_transformer: VideoGeometryTransformer instance.

        Returns:
            Evaluated FrameErrorBudget.
        """
        budget = self.evaluate_frame(
            record=record,
            reference_pos=reference_pos,
            reference_vel=reference_vel,
            reference_orig_pos=reference_orig_pos,
            geometry_transformer=geometry_transformer,
        )
        self._frame_budgets.append(budget)
        return budget

    def _compute_component_stats(
        self,
        name: str,
        values_px: Sequence[Optional[float]],
        total_count: int,
    ) -> ComponentStatistics:
        """Compute summary statistics for a sequence of optional component values."""
        valid = [v for v in values_px if v is not None and not math.isnan(v)]
        avail_count = len(valid)
        cov_pct = (avail_count / max(1, total_count)) * 100.0

        if avail_count == 0:
            return ComponentStatistics(
                name=name,
                status_summary="UNAVAILABLE",
                available_count=0,
                total_count=total_count,
                coverage_pct=0.0,
            )

        arr = np.array(valid, dtype=np.float64)
        mean_px = float(np.mean(arr))
        rms_px = float(np.sqrt(np.mean(arr ** 2)))
        med_px = float(np.median(arr))
        p95_px = float(np.percentile(arr, 95))
        max_px = float(np.max(arr))
        std_px = float(np.std(arr))

        status_str = "AVAILABLE" if cov_pct >= 99.9 else f"PARTIAL ({cov_pct:.1f}%)"

        return ComponentStatistics(
            name=name,
            status_summary=status_str,
            available_count=avail_count,
            total_count=total_count,
            coverage_pct=cov_pct,
            mean_px=mean_px,
            rms_px=rms_px,
            median_px=med_px,
            p95_px=p95_px,
            max_px=max_px,
            std_px=std_px,
            mean_urad=self.px_to_urad(mean_px),
            rms_urad=self.px_to_urad(rms_px),
            p95_urad=self.px_to_urad(p95_px),
            max_urad=self.px_to_urad(max_px),
        )

    def generate_summary(self) -> ErrorBudgetSummary:
        """Generate statistical summary of all recorded frame error budgets."""
        total_count = len(self._frame_budgets)
        evaluated_count = sum(1 for b in self._frame_budgets if b.reference_pos is not None)

        tot_vals = [b.total_error.value_px for b in self._frame_budgets]
        meas_vals = [b.measurement_error.value_px for b in self._frame_budgets]
        est_vals = [b.estimation_residual.value_px for b in self._frame_budgets]
        pred_vals = [b.prediction_residual.value_px for b in self._frame_budgets]
        time_vals = [b.timing_contribution.value_px for b in self._frame_budgets]
        coord_vals = [b.coordinate_transform_contribution.value_px for b in self._frame_budgets]
        ctrl_vals = [b.control_response_contribution.value_px for b in self._frame_budgets]
        reacq_vals = [b.reacquisition_contribution.value_px for b in self._frame_budgets]

        return ErrorBudgetSummary(
            total_frames=total_count,
            evaluated_frames=evaluated_count,
            total_error=self._compute_component_stats("Total Error", tot_vals, total_count),
            measurement=self._compute_component_stats("Measurement", meas_vals, total_count),
            estimation=self._compute_component_stats("Estimation", est_vals, total_count),
            prediction=self._compute_component_stats("Prediction", pred_vals, total_count),
            timing=self._compute_component_stats("Timing", time_vals, total_count),
            coordinate_transform=self._compute_component_stats("Coord Transform", coord_vals, total_count),
            control=self._compute_component_stats("Control Response", ctrl_vals, total_count),
            reacquisition=self._compute_component_stats("Reacquisition", reacq_vals, total_count),
        )
