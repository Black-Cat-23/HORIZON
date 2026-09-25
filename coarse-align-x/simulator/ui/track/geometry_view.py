"""HORIZON Phase 11.4 Filter Geometry & Observation View
=========================================================
Primary large geometry view rendering 640x480 filter state observations.
Features:
  - Dual-Mode Visualization:
      1. 🔭 WIDE FIELD (640x480 full sensor FOV with diagnostic reticles & 4x subpixel PIP lens)
      2. 🔬 SUBPIXEL LOCK (12x laser microscope showing CMOS pixel grid, beam spot profile,
         and reactive 1-sigma / 2-sigma / 3-sigma confidence ellipses)
  - Measured centroid (perception detector measurement)
  - Estimated centroid (Kalman filter state estimate)
  - Predicted centroid (Kalman filter state prediction)
  - Ground-truth evaluation marker — ONLY when Evaluation Mode toggle is ON
  - Covariance uncertainty ellipses (dynamically reactive to 1-sigma / 2-sigma / 3-sigma buttons)
  - Tracking error vector ray
  - Image center reference mark (320, 240)
  - Ground-Truth Firewall: Evaluation mode toggle OFF by default, clearly labeled as offline reference only.
"""

from __future__ import annotations
import math
from typing import Optional, Tuple
import cv2
import numpy as np

from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from simulator.ui.foundation.tokens import (
    COLOR_FIELD,
    COLOR_HAIRLINE_BORDER_HEX,
    COLOR_LOCK_CYAN,
    COLOR_LOST_RED,
    COLOR_TEXT_PRIMARY,
    COLOR_TEXT_SECONDARY,
    COLOR_VOID,
    FONT_BODY,
    FONT_TELEMETRY,
    SPACING_8,
    SPACING_12,
    SPACING_16,
)
from simulator.ui.foundation.primitives import (
    PanelSurface,
    PanelVariant,
    SectionHeaderLabel,
)
from tracking.estimation.covariance import compute_covariance_ellipse
from tracking.estimation.state import StateEstimate
from simulator.perception.detector import DetectionResult


class GeometryCanvasWidget(QLabel):
    """Canvas widget for rendering filter geometry overlays."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumSize(320, 240)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet(f"background-color: {COLOR_VOID}; border: 1px solid {COLOR_HAIRLINE_BORDER_HEX}; border-radius: 4px;")
        self._current_pixmap: Optional[QPixmap] = None

    def update_frame(self, frame_bgr: np.ndarray) -> None:
        if frame_bgr is None or frame_bgr.size == 0:
            return
        h, w, ch = frame_bgr.shape
        rgb_frame = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        rgb_frame = np.ascontiguousarray(rgb_frame)
        qimg = QImage(rgb_frame.data, w, h, ch * w, QImage.Format.Format_RGB888).copy()
        self._current_pixmap = QPixmap.fromImage(qimg)
        self._repaint_canvas()

    def _repaint_canvas(self) -> None:
        if self._current_pixmap is not None:
            scaled = self._current_pixmap.scaled(
                self.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            self.setPixmap(scaled)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._repaint_canvas()


class TrackGeometryView(QWidget):
    """Filter Geometry & State Observation Display View with Dual-Mode Laser Microscope."""

    MODE_WIDE_FIELD = 0
    MODE_SUBPIXEL_LOCK = 1

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._sigma_level = 2.0  # 2-sigma (95.4%) default
        self._eval_mode_enabled = False
        self._view_mode = self.MODE_WIDE_FIELD

        # Cache last telemetry inputs for instant re-rendering on mode/sigma changes
        self._last_sensor_frame: Optional[np.ndarray] = None
        self._last_detection_res: Optional[DetectionResult] = None
        self._last_estimate: Optional[StateEstimate] = None
        self._last_ground_truth_pos: Optional[Tuple[float, float]] = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(SPACING_8)

        # 1. Header Bar: Title + Dual-Mode View Switcher + Ground-Truth Firewall
        header_bar = QHBoxLayout()
        header_bar.setContentsMargins(0, 0, 0, 0)
        header_bar.setSpacing(SPACING_8)

        lbl_title = SectionHeaderLabel("Filter geometry & state observation", self)
        lbl_title.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY}; font-family: {FONT_BODY}; font-size: 14px; font-weight: 600;")
        header_bar.addWidget(lbl_title)

        header_bar.addSpacing(12)

        # Dual-Mode View Switcher Buttons
        self.btn_mode_wide = QPushButton("🔭 Full FOV", self)
        self.btn_mode_subpixel = QPushButton("🔬 8x Subpixel Lock", self)
        self.btn_mode_wide.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_mode_subpixel.setCursor(Qt.CursorShape.PointingHandCursor)

        self.btn_mode_wide.clicked.connect(lambda: self.set_view_mode(self.MODE_WIDE_FIELD))
        self.btn_mode_subpixel.clicked.connect(lambda: self.set_view_mode(self.MODE_SUBPIXEL_LOCK))

        mode_btn_row = QHBoxLayout()
        mode_btn_row.setSpacing(4)
        mode_btn_row.addWidget(self.btn_mode_wide)
        mode_btn_row.addWidget(self.btn_mode_subpixel)
        header_bar.addLayout(mode_btn_row)

        header_bar.addStretch()

        # Ground-Truth Firewall Toggle (OFF by default, labeled offline reference only)
        self.chk_eval_mode = QCheckBox("GT [OFFLINE EVAL ONLY]", self)
        self.chk_eval_mode.setStyleSheet(
            f"color: {COLOR_TEXT_SECONDARY}; font-family: {FONT_BODY}; font-size: 11px; font-weight: 500;"
        )
        self.chk_eval_mode.stateChanged.connect(self._on_eval_mode_toggled)
        header_bar.addWidget(self.chk_eval_mode)

        layout.addLayout(header_bar)

        # 2. Main Canvas Area
        self.canvas = GeometryCanvasWidget(self)
        layout.addWidget(self.canvas, stretch=1)

        self._update_mode_button_styles()

    def set_view_mode(self, mode: int) -> None:
        """Switch between Full Sensor FOV (0) and 8x Subpixel Lock (1)."""
        if self._view_mode != mode:
            self._view_mode = mode
            self._update_mode_button_styles()
            self._rerender_cached()

    def _update_mode_button_styles(self) -> None:
        active_style = (
            "QPushButton {"
            f"  background-color: #162B38; color: {COLOR_LOCK_CYAN}; "
            f"  border: 1px solid {COLOR_LOCK_CYAN}; border-radius: 4px; "
            "  font-weight: 700; font-size: 11px; padding: 3px 10px;"
            "}"
        )
        inactive_style = (
            "QPushButton {"
            f"  background-color: {COLOR_VOID}; color: {COLOR_TEXT_SECONDARY}; "
            "  border: 1px solid #30363D; border-radius: 4px; "
            "  font-weight: 500; font-size: 11px; padding: 3px 10px;"
            "}"
            "QPushButton:hover { background-color: #21262D; color: #C9D1D9; border-color: #58A6FF; }"
        )

        if self._view_mode == self.MODE_WIDE_FIELD:
            self.btn_mode_wide.setStyleSheet(active_style)
            self.btn_mode_subpixel.setStyleSheet(inactive_style)
        else:
            self.btn_mode_wide.setStyleSheet(inactive_style)
            self.btn_mode_subpixel.setStyleSheet(active_style)

    def set_sigma_level(self, sigma: float) -> None:
        """Update selected covariance ellipse confidence level (1.0, 2.0, 3.0)."""
        self._sigma_level = sigma
        self._rerender_cached()

    def _on_eval_mode_toggled(self, state: int) -> None:
        self._eval_mode_enabled = (state == Qt.CheckState.Checked.value)
        if self._eval_mode_enabled:
            self.chk_eval_mode.setStyleSheet(
                f"color: {COLOR_LOCK_CYAN}; font-family: {FONT_BODY}; font-size: 11px; font-weight: 700;"
            )
        else:
            self.chk_eval_mode.setStyleSheet(
                f"color: {COLOR_TEXT_SECONDARY}; font-family: {FONT_BODY}; font-size: 11px; font-weight: 500;"
            )
        self._rerender_cached()

    def _rerender_cached(self) -> None:
        """Re-render current frame immediately when toggles or sigma level change."""
        if self._last_sensor_frame is not None:
            self.render_geometry(
                sensor_frame=self._last_sensor_frame,
                detection_res=self._last_detection_res,
                estimate=self._last_estimate,
                ground_truth_pos=self._last_ground_truth_pos,
            )

    def render_geometry(
        self,
        sensor_frame: np.ndarray,
        detection_res: Optional[DetectionResult],
        estimate: Optional[StateEstimate],
        ground_truth_pos: Optional[Tuple[float, float]] = None,
    ) -> None:
        """Render filter state observation overlays with mathematical covariance ellipse accuracy."""
        if sensor_frame is None or sensor_frame.size == 0:
            return

        # Cache inputs for dynamic updates
        self._last_sensor_frame = sensor_frame
        self._last_detection_res = detection_res
        self._last_estimate = estimate
        self._last_ground_truth_pos = ground_truth_pos

        if self._view_mode == self.MODE_SUBPIXEL_LOCK:
            self._render_subpixel_microscope(sensor_frame, detection_res, estimate, ground_truth_pos)
        else:
            self._render_wide_field(sensor_frame, detection_res, estimate, ground_truth_pos)

    def _render_wide_field(
        self,
        sensor_frame: np.ndarray,
        detection_res: Optional[DetectionResult],
        estimate: Optional[StateEstimate],
        ground_truth_pos: Optional[Tuple[float, float]] = None,
    ) -> None:
        """Mode 0: 640x480 full sensor observation with diagnostic reticles & 4x subpixel PIP lens."""
        h, w = sensor_frame.shape[:2]
        canvas = cv2.cvtColor(sensor_frame, cv2.COLOR_GRAY2BGR) if sensor_frame.ndim == 2 else sensor_frame.copy()

        # 1. Image Center Reference Crosshair (320, 240)
        cx, cy = w // 2, h // 2
        cv2.line(canvas, (cx - 10, cy), (cx + 10, cy), (90, 90, 95), 1)
        cv2.line(canvas, (cx, cy - 10), (cx, cy + 10), (90, 90, 95), 1)

        # 2. Ground-Truth Marker — ONLY rendered when Evaluation Mode is active (Ground-truth firewall)
        if self._eval_mode_enabled and ground_truth_pos is not None:
            gt_x, gt_y = int(round(ground_truth_pos[0])), int(round(ground_truth_pos[1]))
            if 0 <= gt_x < w and 0 <= gt_y < h:
                cv2.circle(canvas, (gt_x, gt_y), 5, (255, 255, 255), 1, cv2.LINE_AA)
                cv2.line(canvas, (gt_x - 8, gt_y), (gt_x + 8, gt_y), (255, 255, 255), 1)
                cv2.line(canvas, (gt_x, gt_y - 8), (gt_x, gt_y + 8), (255, 255, 255), 1)
                cv2.putText(canvas, "GT [EVAL]", (gt_x + 8, gt_y - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (255, 255, 255), 1, cv2.LINE_AA)

        # 3. Measured Centroid Marker (Bright Red Reticle)
        meas_x, meas_y = None, None
        if detection_res and detection_res.detected and detection_res.centroid:
            meas_x, meas_y = int(round(detection_res.centroid[0])), int(round(detection_res.centroid[1]))
            if 0 <= meas_x < w and 0 <= meas_y < h:
                cv2.line(canvas, (meas_x - 7, meas_y), (meas_x + 7, meas_y), (0, 0, 240), 1)
                cv2.line(canvas, (meas_x, meas_y - 7), (meas_x, meas_y + 7), (0, 0, 240), 1)
                cv2.circle(canvas, (meas_x, meas_y), 2, (0, 0, 255), -1)
                cv2.putText(canvas, "MEAS", (meas_x + 8, meas_y - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 0, 255), 1, cv2.LINE_AA)

        # 4. Filter State Estimate & Covariance Ellipse
        if estimate is not None:
            est_x, est_y = int(round(estimate.estimated_x)), int(round(estimate.estimated_y))

            # Predicted Centroid Marker (Amber 'x' Marker)
            pred_x, pred_y = int(round(estimate.predicted_x)), int(round(estimate.predicted_y))
            if 0 <= pred_x < w and 0 <= pred_y < h:
                cv2.drawMarker(canvas, (pred_x, pred_y), (0, 215, 255), cv2.MARKER_TILTED_CROSS, 8, 1)
                cv2.putText(canvas, "PRED", (pred_x + 8, pred_y - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 215, 255), 1, cv2.LINE_AA)

            # Mathematically Accurate Covariance Ellipse on full FOV
            if estimate.covariance is not None:
                try:
                    conf_level = 0.683 if self._sigma_level == 1.0 else (0.954 if self._sigma_level == 2.0 else 0.997)
                    ellipse_data = compute_covariance_ellipse(
                        P=estimate.covariance,
                        center_x=estimate.estimated_x,
                        center_y=estimate.estimated_y,
                        confidence_level=conf_level,
                    )
                    c_pt = (int(round(ellipse_data.center_x)), int(round(ellipse_data.center_y)))
                    axes_pt = (
                        max(1, int(round(ellipse_data.semi_major_axis))),
                        max(1, int(round(ellipse_data.semi_minor_axis))),
                    )
                    ang = int(round(ellipse_data.orientation_deg))

                    if axes_pt[0] < 500 and axes_pt[1] < 500:
                        cv2.ellipse(
                            canvas,
                            center=c_pt,
                            axes=axes_pt,
                            angle=ang,
                            startAngle=0,
                            endAngle=360,
                            color=(232, 212, 127),
                            thickness=1,
                            lineType=cv2.LINE_AA,
                        )
                except Exception:
                    pass

            # Estimated Position Reticle (Bright Cyan)
            if 0 <= est_x < w and 0 <= est_y < h:
                cv2.circle(canvas, (est_x, est_y), 5, (232, 212, 127), 1, cv2.LINE_AA)
                cv2.line(canvas, (est_x - 8, est_y), (est_x + 8, est_y), (232, 212, 127), 1)
                cv2.line(canvas, (est_x, est_y - 8), (est_x, est_y + 8), (232, 212, 127), 1)
                cv2.putText(canvas, f"EST (+/-{int(self._sigma_level)}s)", (est_x + 8, est_y + 12), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (232, 212, 127), 1, cv2.LINE_AA)

                # Tracking Error Vector Line (connecting measurement to estimate)
                if meas_x is not None and meas_y is not None:
                    cv2.line(canvas, (meas_x, meas_y), (est_x, est_y), (0, 165, 255), 1, cv2.LINE_AA)

            # 5. Picture-in-Picture 4x Subpixel Magnifying Lens
            try:
                roi_size = 32
                x1 = max(0, min(w - roi_size, est_x - roi_size // 2))
                y1 = max(0, min(h - roi_size, est_y - roi_size // 2))
                patch = sensor_frame[y1:y1 + roi_size, x1:x1 + roi_size]

                if patch.shape[0] == roi_size and patch.shape[1] == roi_size:
                    pip_size = 136
                    scale_pip = pip_size / roi_size
                    patch_bgr = cv2.cvtColor(patch, cv2.COLOR_GRAY2BGR) if patch.ndim == 2 else patch.copy()
                    pip_img = cv2.resize(patch_bgr, (pip_size, pip_size), interpolation=cv2.INTER_NEAREST)

                    # Subpixel center within PIP
                    pip_cx = int(round((estimate.estimated_x - x1) * scale_pip))
                    pip_cy = int(round((estimate.estimated_y - y1) * scale_pip))

                    # Subtle pixel grid lines
                    for g in range(0, pip_size, int(round(scale_pip * 4))):
                        cv2.line(pip_img, (g, 0), (g, pip_size), (35, 42, 50), 1)
                        cv2.line(pip_img, (0, g), (pip_size, g), (35, 42, 50), 1)

                    # Nested 1-sigma, 2-sigma, 3-sigma confidence ellipses on PIP
                    if estimate.covariance is not None:
                        for s_lvl, col in [(1.0, (180, 180, 190)), (2.0, (111, 232, 168)), (3.0, (92, 161, 232))]:
                            is_active = (abs(s_lvl - self._sigma_level) < 0.1)
                            draw_col = (255, 230, 80) if is_active else col
                            th = 2 if is_active else 1
                            c_lvl = 0.683 if s_lvl == 1.0 else (0.954 if s_lvl == 2.0 else 0.997)
                            e_data = compute_covariance_ellipse(estimate.covariance, estimate.estimated_x, estimate.estimated_y, c_lvl)
                            ax = (
                                max(1, int(round(e_data.semi_major_axis * scale_pip))),
                                max(1, int(round(e_data.semi_minor_axis * scale_pip))),
                            )
                            if ax[0] < pip_size and ax[1] < pip_size:
                                cv2.ellipse(pip_img, (pip_cx, pip_cy), ax, int(round(e_data.orientation_deg)), 0, 360, draw_col, th, cv2.LINE_AA)

                    # Subpixel crosshair reticle
                    cv2.drawMarker(pip_img, (pip_cx, pip_cy), (232, 212, 127), cv2.MARKER_CROSS, 10, 1)

                    # Velocity leader vector
                    vx, vy = estimate.estimated_vx, estimate.estimated_vy
                    v_spd = math.hypot(vx, vy)
                    if v_spd > 5.0:
                        v_len = min(28.0, v_spd * 0.12)
                        end_x = int(round(pip_cx + (vx / v_spd) * v_len))
                        end_y = int(round(pip_cy + (vy / v_spd) * v_len))
                        cv2.arrowedLine(pip_img, (pip_cx, pip_cy), (end_x, end_y), (0, 215, 255), 1, tipLength=0.3)

                    # Embed PIP into top-right corner of canvas
                    px0 = w - pip_size - 10
                    py0 = 10
                    cv2.rectangle(canvas, (px0 - 2, py0 - 18), (px0 + pip_size + 2, py0 + pip_size + 16), (22, 22, 26), -1)
                    cv2.rectangle(canvas, (px0 - 2, py0 - 18), (px0 + pip_size + 2, py0 + pip_size + 16), (127, 212, 232), 1)
                    canvas[py0:py0 + pip_size, px0:px0 + pip_size] = pip_img

                    # PIP Header & Footnote
                    cv2.putText(canvas, f"PIP 4x LOCK (+/-{int(self._sigma_level)}s)", (px0 + 4, py0 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.32, (127, 212, 232), 1, cv2.LINE_AA)
                    cv2.putText(canvas, f"({estimate.estimated_x:.1f}, {estimate.estimated_y:.1f})", (px0 + 4, py0 + pip_size + 12), cv2.FONT_HERSHEY_SIMPLEX, 0.32, (200, 205, 215), 1, cv2.LINE_AA)

                    # Bounding box & faint dotted leader line from sensor spot to PIP
                    cv2.rectangle(canvas, (x1, y1), (x1 + roi_size, y1 + roi_size), (127, 212, 232), 1)
                    cv2.line(canvas, (x1 + roi_size, y1), (px0, py0 + pip_size // 2), (80, 90, 105), 1)
            except Exception:
                pass

        self.canvas.update_frame(canvas)

    def _render_subpixel_microscope(
        self,
        sensor_frame: np.ndarray,
        detection_res: Optional[DetectionResult],
        estimate: Optional[StateEstimate],
        ground_truth_pos: Optional[Tuple[float, float]] = None,
    ) -> None:
        """Mode 1: Laboratory Optical Beam Profiler canvas (Airy Disc PSF & D86 Encircled Energy).
        Extracts 36x36 ROI, subtracts dark-current noise floor, fits diffraction rings,
        computes D86 encircled energy diameter, and highlights active confidence bound.
        """
        orig_h, orig_w = sensor_frame.shape[:2]
        canvas_w, canvas_h = 640, 480

        # Determine center of interest
        if estimate is not None:
            cx_ref = estimate.estimated_x
            cy_ref = estimate.estimated_y
        elif detection_res and detection_res.detected and detection_res.centroid:
            cx_ref, cy_ref = detection_res.centroid
        else:
            cx_ref, cy_ref = orig_w / 2.0, orig_h / 2.0

        roi_span = 36  # 36x36 sensor pixels cropped
        rx0 = int(round(cx_ref - roi_span // 2))
        ry0 = int(round(cy_ref - roi_span // 2))

        # Safe ROI extraction with border clamp
        rx0_clamped = max(0, min(orig_w - roi_span, rx0))
        ry0_clamped = max(0, min(orig_h - roi_span, ry0))
        patch_raw = sensor_frame[ry0_clamped:ry0_clamped + roi_span, rx0_clamped:rx0_clamped + roi_span]
        if patch_raw.ndim == 3:
            patch_gray = cv2.cvtColor(patch_raw, cv2.COLOR_BGR2GRAY)
        else:
            patch_gray = patch_raw.copy()

        # Build clean microscope canvas (dark void background)
        canvas = np.full((canvas_h, canvas_w, 3), 13, dtype=np.uint8)

        # Microscope viewing viewport dimensions
        view_size = 400
        vx0 = (canvas_w - view_size) // 2
        vy0 = (canvas_h - view_size) // 2 + 10

        scale_micro = view_size / float(roi_span)  # ~11.1x magnification

        # 1. Optical Lab Beam Profiling & Dark-Current Noise Floor Rejection
        # Sample perimeter pixels (boundary of 36x36 patch) as background baseline
        perim_pixels = np.concatenate([
            patch_gray[0, :], patch_gray[-1, :],
            patch_gray[:, 0], patch_gray[:, -1]
        ])
        bg_median = float(np.median(perim_pixels))
        bg_std = max(1.0, float(np.std(perim_pixels)))

        peak_val = float(np.max(patch_gray))
        contrast = peak_val - bg_median

        # Base magnified view starts as dark optical void (#0D1117)
        magnified_view = np.full((view_size, view_size, 3), 15, dtype=np.uint8)

        d86_val_px = 0.0
        snr_db = 0.0

        if contrast > 2.5 * bg_std:
            # Genuine optical beacon present: subtract noise floor cleanly
            snr_db = 20.0 * math.log10(max(1.0, contrast / bg_std))
            noise_thresh = bg_median + 1.2 * bg_std
            clean_patch = np.maximum(0.0, patch_gray.astype(np.float32) - noise_thresh)
            norm_beam = np.clip((clean_patch / max(1.0, peak_val - noise_thresh)) * 255.0, 0.0, 255.0).astype(np.uint8)

            # Apply pseudo-color thermal colormap (Inferno palette)
            thermal_map = cv2.applyColorMap(norm_beam, cv2.COLORMAP_INFERNO)
            beam_magnified = cv2.resize(thermal_map, (view_size, view_size), interpolation=cv2.INTER_NEAREST)

            # Mask: where flux is zero, keep dark void
            mask = cv2.resize(norm_beam, (view_size, view_size), interpolation=cv2.INTER_NEAREST)
            has_flux = (mask > 5)
            magnified_view[has_flux] = beam_magnified[has_flux]

            # Compute D86 Encircled Energy Radius
            total_flux = float(np.sum(clean_patch))
            if total_flux > 10.0:
                cy_local, cx_local = np.indices(clean_patch.shape)
                c_x = float(np.sum(cx_local * clean_patch) / total_flux)
                c_y = float(np.sum(cy_local * clean_patch) / total_flux)
                dists = np.hypot(cx_local - c_x, cy_local - c_y).flatten()
                fluxes = clean_patch.flatten()
                sort_idx = np.argsort(dists)
                cum_flux = np.cumsum(fluxes[sort_idx])
                d86_idx = int(np.searchsorted(cum_flux, 0.865 * total_flux))
                r86 = float(dists[sort_idx[min(len(sort_idx) - 1, d86_idx)]])
                d86_val_px = 2.0 * r86

                # Render D86 Encircled Energy ring as subtle dashed gold circle
                c_mx = int(round(c_x * scale_micro))
                c_my = int(round(c_y * scale_micro))
                r_micro = max(4, int(round(r86 * scale_micro)))
                cv2.circle(magnified_view, (c_mx, c_my), r_micro, (70, 190, 230), 1, cv2.LINE_AA)

        # 2. Draw Physical CMOS Detector Pixel Boundaries
        step_px = int(round(scale_micro))
        for p in range(0, view_size + 1, step_px):
            cv2.line(magnified_view, (p, 0), (p, view_size), (35, 42, 52), 1)
            cv2.line(magnified_view, (0, p), (view_size, p), (35, 42, 52), 1)

        # Coordinate transformation helper into magnified view
        def to_micro_coords(sx: float, sy: float) -> Tuple[int, int]:
            mx = int(round((sx - rx0_clamped) * scale_micro))
            my = int(round((sy - ry0_clamped) * scale_micro))
            return mx, my

        # 3. Ground Truth Marker (Firewall protected: renders ONLY when eval mode is unlocked)
        if self._eval_mode_enabled and ground_truth_pos is not None:
            gt_mx, gt_my = to_micro_coords(ground_truth_pos[0], ground_truth_pos[1])
            if 0 <= gt_mx < view_size and 0 <= gt_my < view_size:
                cv2.circle(magnified_view, (gt_mx, gt_my), 10, (255, 255, 255), 1, cv2.LINE_AA)
                cv2.drawMarker(magnified_view, (gt_mx, gt_my), (255, 255, 255), cv2.MARKER_CROSS, 16, 1)
                cv2.putText(magnified_view, "GT EVAL", (gt_mx + 8, gt_my - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (255, 255, 255), 1, cv2.LINE_AA)

        # 4. Measurement Centroid Reticle
        meas_pt = None
        if detection_res and detection_res.detected and detection_res.centroid:
            meas_mx, meas_my = to_micro_coords(detection_res.centroid[0], detection_res.centroid[1])
            if 0 <= meas_mx < view_size and 0 <= meas_my < view_size:
                meas_pt = (meas_mx, meas_my)
                cv2.circle(magnified_view, meas_pt, 8, (0, 0, 240), 1, cv2.LINE_AA)
                cv2.drawMarker(magnified_view, meas_pt, (0, 0, 240), cv2.MARKER_TILTED_CROSS, 14, 1)
                cv2.putText(magnified_view, "MEAS", (meas_mx + 8, meas_my - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 0, 240), 1, cv2.LINE_AA)

        # 5. Kalman Filter State Estimate, Error Vector & Reactive Covariance Ellipses
        if estimate is not None:
            est_mx, est_my = to_micro_coords(estimate.estimated_x, estimate.estimated_y)

            # Draw Concentric 1-sigma, 2-sigma, 3-sigma Ellipses (Scaled to Micro View!)
            if estimate.covariance is not None:
                sigma_configs = [
                    (1.0, 0.683, (120, 180, 240), "1s"),
                    (2.0, 0.954, (111, 232, 168), "2s"),
                    (3.0, 0.997, (92, 161, 232), "3s"),
                ]
                for s_lvl, c_lvl, col, s_tag in sigma_configs:
                    try:
                        is_active = (abs(s_lvl - self._sigma_level) < 0.1)
                        e_data = compute_covariance_ellipse(
                            P=estimate.covariance,
                            center_x=estimate.estimated_x,
                            center_y=estimate.estimated_y,
                            confidence_level=c_lvl,
                        )
                        ax_micro = (
                            max(1, int(round(e_data.semi_major_axis * scale_micro))),
                            max(1, int(round(e_data.semi_minor_axis * scale_micro))),
                        )
                        ang = int(round(e_data.orientation_deg))

                        if ax_micro[0] < view_size * 2 and ax_micro[1] < view_size * 2:
                            if is_active:
                                # Active ring: Highlighted bold neon outline
                                cv2.ellipse(magnified_view, (est_mx, est_my), ax_micro, ang, 0, 360, (255, 230, 80), 2, cv2.LINE_AA)
                                # Semi-transparent filled overlay
                                overlay = magnified_view.copy()
                                cv2.ellipse(overlay, (est_mx, est_my), ax_micro, ang, 0, 360, (255, 230, 80), -1)
                                cv2.addWeighted(overlay, 0.18, magnified_view, 0.82, 0, magnified_view)
                            else:
                                # Inactive ring: subtle thin contour
                                cv2.ellipse(magnified_view, (est_mx, est_my), ax_micro, ang, 0, 360, col, 1, cv2.LINE_AA)
                    except Exception:
                        pass

            # Error Ray (Measurement to Estimate)
            if meas_pt is not None and 0 <= est_mx < view_size and 0 <= est_my < view_size:
                cv2.line(magnified_view, meas_pt, (est_mx, est_my), (0, 165, 255), 1, cv2.LINE_AA)
                dist_px = math.hypot(detection_res.centroid[0] - estimate.estimated_x, detection_res.centroid[1] - estimate.estimated_y)
                mid_x = (meas_pt[0] + est_mx) // 2
                mid_y = (meas_pt[1] + est_my) // 2
                cv2.putText(magnified_view, f"err={dist_px:.2f}px", (mid_x + 6, mid_y), cv2.FONT_HERSHEY_SIMPLEX, 0.32, (0, 165, 255), 1, cv2.LINE_AA)

            # Subpixel Centroid Reticle
            if 0 <= est_mx < view_size and 0 <= est_my < view_size:
                cv2.circle(magnified_view, (est_mx, est_my), 7, (232, 212, 127), 1, cv2.LINE_AA)
                cv2.drawMarker(magnified_view, (est_mx, est_my), (232, 212, 127), cv2.MARKER_CROSS, 18, 1)
                cv2.putText(magnified_view, f"EST ({estimate.estimated_x:.2f}, {estimate.estimated_y:.2f})", (est_mx + 8, est_my + 14), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (232, 212, 127), 1, cv2.LINE_AA)

            # Velocity Vector Arrow
            vx, vy = estimate.estimated_vx, estimate.estimated_vy
            v_spd = math.hypot(vx, vy)
            if v_spd > 2.0:
                v_len = min(60.0, v_spd * scale_micro * 0.15)
                end_x = int(round(est_mx + (vx / v_spd) * v_len))
                end_y = int(round(est_my + (vy / v_spd) * v_len))
                cv2.arrowedLine(magnified_view, (est_mx, est_my), (end_x, end_y), (0, 215, 255), 2, tipLength=0.25)
                cv2.putText(magnified_view, f"{v_spd:.1f} px/s", (end_x + 4, end_y + 4), cv2.FONT_HERSHEY_SIMPLEX, 0.32, (0, 215, 255), 1, cv2.LINE_AA)

        # Embed magnified viewport into canvas
        canvas[vy0:vy0 + view_size, vx0:vx0 + view_size] = magnified_view

        # Reticle Border around microscope viewport
        cv2.rectangle(canvas, (vx0 - 1, vy0 - 1), (vx0 + view_size + 1, vy0 + view_size + 1), (127, 212, 232), 1)

        # Corner reticles for high-tech aerospace look
        c_len = 12
        for cx_c, cy_c, dx, dy in [(vx0, vy0, 1, 1), (vx0 + view_size, vy0, -1, 1), (vx0, vy0 + view_size, 1, -1), (vx0 + view_size, vy0 + view_size, -1, -1)]:
            cv2.line(canvas, (cx_c, cy_c), (cx_c + dx * c_len, cy_c), (255, 230, 80), 2)
            cv2.line(canvas, (cx_c, cy_c), (cx_c, cy_c + dy * c_len), (255, 230, 80), 2)

        # HUD Top Banner Overlay
        top_title = f"11.1x OPTICAL BEAM PROFILER | D86: {d86_val_px:.1f}px | SNR: {snr_db:.1f}dB" if d86_val_px > 0 else "11.1x OPTICAL BEAM PROFILER"
        cv2.putText(canvas, top_title, (vx0, vy0 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (127, 212, 232), 1, cv2.LINE_AA)
        conf_pct = 68.3 if self._sigma_level == 1.0 else (95.4 if self._sigma_level == 2.0 else 99.7)
        active_conf_str = f"BOUND: +/-{int(self._sigma_level)}s ({conf_pct:.1f}%)"
        cv2.putText(canvas, active_conf_str, (vx0 + view_size - 150, vy0 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (255, 230, 80), 1, cv2.LINE_AA)

        # HUD Bottom Telemetry Readout
        if estimate is not None:
            hud_bot = f"SENSOR ROI: [{rx0_clamped}:{rx0_clamped+roi_span}, {ry0_clamped}:{ry0_clamped+roi_span}]  |  EST: ({estimate.estimated_x:.2f}, {estimate.estimated_y:.2f}) px  |  PITCH: 12.5 um"
        else:
            hud_bot = f"SENSOR ROI: [{rx0_clamped}:{rx0_clamped+roi_span}, {ry0_clamped}:{ry0_clamped+roi_span}]  |  AWAITING ESTIMATOR LOCK"
        cv2.putText(canvas, hud_bot, (vx0, vy0 + view_size + 18), cv2.FONT_HERSHEY_SIMPLEX, 0.32, (180, 190, 205), 1, cv2.LINE_AA)

        self.canvas.update_frame(canvas)
