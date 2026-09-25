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
    detection_result: Optional[Any] = None,
) -> np.ndarray:
    """Render multi-layer visual diagnostics on a camera frame.

    Args:
        frame: 2D grayscale or 3D BGR image (e.g. 640×480).
        estimate: Current StateEstimate output.
        ground_truth_pos: Optional (u, v) ground-truth position (evaluation only).
        measurement_pos: Optional (u, v) raw detection measurement.
        draw_ellipse: Toggle drawing of the covariance uncertainty ellipse.
        draw_velocity_vector: Toggle drawing of the estimated velocity ray.
        detection_result: Optional DetectionResult object containing bbox, candidates, confidence.

    Returns:
        Annotated BGR 3-channel image.
    """
    if frame.ndim == 2:
        canvas = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
    else:
        canvas = frame.copy()

    h, w = canvas.shape[:2]

    # 0. Draw Detection Bounding Boxes & Lock Banner if DetectionResult provided
    if detection_result is not None:
        bbox = getattr(detection_result, "bbox", None)
        detected = getattr(detection_result, "detected", False)
        confidence = getattr(detection_result, "confidence", 0.0)
        candidates = getattr(detection_result, "candidates", None)

        # Draw all non-selected candidates as thin yellow boxes
        if candidates:
            for cand in candidates:
                cand_bbox = getattr(cand, "bbox", None)
                if cand_bbox:
                    cx_box, cy_box, cw, ch = cand_bbox
                    cv2.rectangle(canvas, (cx_box, cy_box), (cx_box + cw, cy_box + ch), (0, 215, 255), 1, cv2.LINE_AA)

        # Draw main selected detected bounding box in bright green
        if detected and bbox is not None:
            bx, by, bw, bh = bbox
            cv2.rectangle(canvas, (bx, by), (bx + bw, by + bh), (0, 255, 0), 2, cv2.LINE_AA)
            corner_len = min(6, bw // 2, bh // 2)
            if corner_len > 0:
                cv2.line(canvas, (bx, by), (bx + corner_len, by), (0, 255, 0), 2)
                cv2.line(canvas, (bx, by), (bx, by + corner_len), (0, 255, 0), 2)
                cv2.line(canvas, (bx + bw, by), (bx + bw - corner_len, by), (0, 255, 0), 2)
                cv2.line(canvas, (bx + bw, by), (bx + bw, by + corner_len), (0, 255, 0), 2)
                cv2.line(canvas, (bx, by + bh), (bx + corner_len, by + bh), (0, 255, 0), 2)
                cv2.line(canvas, (bx, by + bh), (bx, by + bh - corner_len), (0, 255, 0), 2)
                cv2.line(canvas, (bx + bw, by + bh), (bx + bw - corner_len, by + bh), (0, 255, 0), 2)
                cv2.line(canvas, (bx + bw, by + bh), (bx + bw, by + bh - corner_len), (0, 255, 0), 2)

            conf_str = f"BEACON LOCK: {confidence * 100.0:.0f}%"
            cv2.putText(canvas, conf_str, (bx, max(by - 6, 14)), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 3, cv2.LINE_AA)
            cv2.putText(canvas, conf_str, (bx, max(by - 6, 14)), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 0), 1, cv2.LINE_AA)

    # 1. Draw Ground-Truth Marker (White/Yellow Dual Ring, reference only)
    if ground_truth_pos is not None:
        gt_x, gt_y = int(round(ground_truth_pos[0])), int(round(ground_truth_pos[1]))
        if 0 <= gt_x < w and 0 <= gt_y < h:
            cv2.circle(canvas, (gt_x, gt_y), 10, (0, 215, 255), 2, cv2.LINE_AA)
            cv2.circle(canvas, (gt_x, gt_y), 3, (0, 255, 255), -1, cv2.LINE_AA)
            cv2.line(canvas, (gt_x - 16, gt_y), (gt_x - 11, gt_y), (0, 215, 255), 2, cv2.LINE_AA)
            cv2.line(canvas, (gt_x + 11, gt_y), (gt_x + 16, gt_y), (0, 215, 255), 2, cv2.LINE_AA)
            cv2.line(canvas, (gt_x, gt_y - 16), (gt_x, gt_y - 11), (0, 215, 255), 2, cv2.LINE_AA)
            cv2.line(canvas, (gt_x, gt_y + 11), (gt_x, gt_y + 16), (0, 215, 255), 2, cv2.LINE_AA)
            label_gt = "BEACON (GT)"
            cv2.putText(canvas, label_gt, (gt_x + 14, gt_y - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 3, cv2.LINE_AA)
            cv2.putText(canvas, label_gt, (gt_x + 14, gt_y - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 255), 1, cv2.LINE_AA)

    # 2. Draw Raw Perception Measurement Marker (Bright Red Reticle)
    if measurement_pos is not None:
        mx, my = int(round(measurement_pos[0])), int(round(measurement_pos[1]))
        if 0 <= mx < w and 0 <= my < h:
            cv2.line(canvas, (mx - 10, my), (mx + 10, my), (0, 0, 255), 2, cv2.LINE_AA)
            cv2.line(canvas, (mx, my - 10), (mx, my + 10), (0, 0, 255), 2, cv2.LINE_AA)
            cv2.circle(canvas, (mx, my), 4, (0, 0, 255), -1, cv2.LINE_AA)
            p_label = "P (RAW CENTROID)"
            cv2.putText(canvas, p_label, (mx + 12, my - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 0), 3, cv2.LINE_AA)
            cv2.putText(canvas, p_label, (mx + 12, my - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 255), 1, cv2.LINE_AA)

    if estimate is None:
        return canvas

    # 3. Draw Predicted Position Marker (Amber / Yellow)
    px, py = int(round(estimate.predicted_x)), int(round(estimate.predicted_y))
    if 0 <= px < w and 0 <= py < h:
        cv2.drawMarker(canvas, (px, py), (0, 215, 255), cv2.MARKER_TILTED_CROSS, 8, 1, cv2.LINE_AA)

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

            if axes[0] < 500 and axes[1] < 500:
                cv2.ellipse(
                    canvas,
                    center=center,
                    axes=axes,
                    angle=angle,
                    startAngle=0,
                    endAngle=360,
                    color=(255, 220, 0),
                    thickness=1,
                    lineType=cv2.LINE_AA,
                )
        except Exception:
            pass

    # 5. Draw Estimated Position & Velocity Vector (Bright Cyan Reticle)
    ex, ey = int(round(estimate.estimated_x)), int(round(estimate.estimated_y))
    if 0 <= ex < w and 0 <= ey < h:
        cv2.circle(canvas, (ex, ey), 6, (255, 255, 0), 2, lineType=cv2.LINE_AA)
        cv2.line(canvas, (ex - 10, ey), (ex + 10, ey), (255, 255, 0), 2, lineType=cv2.LINE_AA)
        cv2.line(canvas, (ex, ey - 10), (ex, ey + 10), (255, 255, 0), 2, lineType=cv2.LINE_AA)
        est_label = "EST (TRACKED)"
        cv2.putText(canvas, est_label, (ex + 12, ey + 14), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 0), 3, cv2.LINE_AA)
        cv2.putText(canvas, est_label, (ex + 12, ey + 14), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 0), 1, cv2.LINE_AA)

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
                line_type=cv2.LINE_AA,
            )

    return canvas
