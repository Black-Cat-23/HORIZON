"""
HORIZON Tracking Diagnostic Visualization Utilities
===========================================================
Draws multi-layer diagnostic markers on sensor frames:
  - Ground Truth: White reference crosshair [Evaluation Only]
  - Measurement: Bright red perception reticle
  - State Estimate: Bright cyan reticle with velocity vector
  - State Prediction: Yellow/amber prediction marker
  - Covariance: Parametric uncertainty ellipse (2-sigma / 95%)
"""

from __future__ import annotations

import math
from typing import Optional, Tuple
import cv2
import numpy as np

from tracking.estimation.covariance import CovarianceEllipseData, compute_covariance_ellipse
from tracking.estimation.state import StateEstimate


def draw_tracking_annotations(
    frame: np.ndarray,
    estimate: Optional[StateEstimate] = None,
    ground_truth_pos: Optional[Tuple[float, float]] = None,
    measurement_pos: Optional[Tuple[float, float]] = None,
    draw_ellipse: bool = True,
    draw_velocity_vector: bool = True,
) -> np.ndarray:
    """Render multi-layer visual diagnostics on a camera frame.

    Args:
        frame: 2D grayscale or 3D BGR image (e.g. 640×480).
        estimate: Current StateEstimate output.
        ground_truth_pos: Optional (u, v) ground-truth position (evaluation only).
        measurement_pos: Optional (u, v) raw detection measurement.
        draw_ellipse: Toggle drawing of the covariance uncertainty ellipse.
        draw_velocity_vector: Toggle drawing of the estimated velocity ray.

    Returns:
        Annotated BGR 3-channel image.
    """
    if frame.ndim == 2:
        canvas = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
    else:
        canvas = frame.copy()

    h, w = canvas.shape[:2]

    # 1. Draw Ground-Truth Marker (White, reference only)
    if ground_truth_pos is not None:
        gt_x, gt_y = int(round(ground_truth_pos[0])), int(round(ground_truth_pos[1]))
        if 0 <= gt_x < w and 0 <= gt_y < h:
            cv2.circle(canvas, (gt_x, gt_y), 4, (255, 255, 255), 1)
            cv2.line(canvas, (gt_x - 6, gt_y), (gt_x + 6, gt_y), (255, 255, 255), 1)
            cv2.line(canvas, (gt_x, gt_y - 6), (gt_x, gt_y + 6), (255, 255, 255), 1)

    # 2. Draw Raw Perception Measurement Marker (Bright Red)
    if measurement_pos is not None:
        mx, my = int(round(measurement_pos[0])), int(round(measurement_pos[1]))
        if 0 <= mx < w and 0 <= my < h:
            cv2.line(canvas, (mx - 7, my), (mx + 7, my), (0, 0, 240), 1)
            cv2.line(canvas, (mx, my - 7), (mx, my + 7), (0, 0, 240), 1)
            cv2.circle(canvas, (mx, my), 2, (0, 0, 255), -1)
            cv2.putText(canvas, "P", (mx + 8, my - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 0, 255), 1, cv2.LINE_AA)

    if estimate is None:
        return canvas

    # 3. Draw Predicted Position Marker (Amber / Yellow)
    px, py = int(round(estimate.predicted_x)), int(round(estimate.predicted_y))
    if 0 <= px < w and 0 <= py < h:
        cv2.drawMarker(canvas, (px, py), (0, 215, 255), cv2.MARKER_TILTED_CROSS, 8, 1)

    # 4. Draw Covariance Uncertainty Ellipse (Thin Cyan)
    if draw_ellipse and estimate.covariance is not None:
        try:
            ellipse_data = compute_covariance_ellipse(
                P=estimate.covariance,
                center_x=estimate.estimated_x,
                center_y=estimate.estimated_y,
                confidence_level=0.95,
            )
            center = (int(round(ellipse_data.center_x)), int(round(ellipse_data.center_y)))
            axes = (
                max(1, int(round(ellipse_data.semi_major_axis))),
                max(1, int(round(ellipse_data.semi_minor_axis))),
            )
            angle = int(round(ellipse_data.orientation_deg))

            # Only draw if ellipse is within reasonable bounds
            if axes[0] < 500 and axes[1] < 500:
                cv2.ellipse(
                    canvas,
                    center=center,
                    axes=axes,
                    angle=angle,
                    startAngle=0,
                    endAngle=360,
                    color=(255, 220, 0),  # Cyan in BGR is (255, 255, 0) or (255, 220, 0)
                    thickness=1,
                    lineType=cv2.LINE_AA,
                )
        except Exception:
            pass

    # 5. Draw Estimated Position & Velocity Vector (Bright Cyan)
    ex, ey = int(round(estimate.estimated_x)), int(round(estimate.estimated_y))
    if 0 <= ex < w and 0 <= ey < h:
        # Cyan reticle
        cv2.circle(canvas, (ex, ey), 5, (255, 255, 0), 1, lineType=cv2.LINE_AA)
        cv2.line(canvas, (ex - 8, ey), (ex + 8, ey), (255, 255, 0), 1)
        cv2.line(canvas, (ex, ey - 8), (ex, ey + 8), (255, 255, 0), 1)
        cv2.putText(canvas, "EST", (ex + 8, ey + 12), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (255, 255, 0), 1, cv2.LINE_AA)

        # Velocity vector (scaled by 0.2s for visual length)
        if draw_velocity_vector:
            vx, vy = estimate.estimated_vx, estimate.estimated_vy
            end_x = int(round(ex + (vx * 0.2)))
            end_y = int(round(ey + (vy * 0.2)))
            cv2.arrowedLine(
                canvas,
                (ex, ey),
                (end_x, end_y),
                (255, 200, 0),
                1,
                tipLength=0.25,
            )

    return canvas
