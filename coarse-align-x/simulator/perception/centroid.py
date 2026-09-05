"""
HORIZON Subpixel Centroid Estimation Algorithms
======================================================
Algorithms for high-precision subpixel beacon centroid localization:
  1. Geometric Centroid (Binary spatial moments)
  2. Weighted Center of Gravity (Intensity-weighted CoG)
  3. 2D Gaussian Surface Fit (Non-linear least squares surface estimation)

Strict Invariant: Zero integer truncation. Returns pure floating-point coordinates.
"""

from __future__ import annotations

from typing import Tuple
import cv2
import numpy as np
from scipy.optimize import curve_fit

from simulator.perception.config import CentroidConfig


def compute_geometric_centroid(
    roi_mask: np.ndarray, x_offset: int, y_offset: int
) -> Tuple[float, float]:
    """Compute geometric centroid from binary mask moments.

    u_c = M10 / M00,  v_c = M01 / M00
    """
    m = cv2.moments(roi_mask.astype(np.uint8))
    if m["m00"] > 0:
        uc = (m["m10"] / m["m00"]) + 0.5 + float(x_offset)
        vc = (m["m01"] / m["m00"]) + 0.5 + float(y_offset)
        return float(uc), float(vc)
    # Fallback to bounding box center
    h, w = roi_mask.shape
    return float(x_offset + w / 2.0), float(y_offset + h / 2.0)


def compute_weighted_cog(
    roi_frame: np.ndarray,
    roi_mask: np.ndarray,
    bg_level: float,
    x_offset: int,
    y_offset: int,
) -> Tuple[float, float]:
    """Compute intensity-weighted Center of Gravity (Weighted CoG) with subpixel precision.

    u = sum((I_i - bg) * (u_i + 0.5)) / sum(I_i - bg)
    v = sum((I_i - bg) * (v_i + 0.5)) / sum(I_i - bg)
    """
    # Denoise ROI frame to remove isolated S&P impulse specks
    if roi_frame.shape[0] >= 3 and roi_frame.shape[1] >= 3:
        clean_roi = cv2.medianBlur(roi_frame, 3)
    else:
        clean_roi = roi_frame

    # Net intensity above background
    weights = np.maximum(clean_roi.astype(np.float64) - bg_level, 0.0)
    max_w = np.max(weights) if weights.size > 0 else 0.0
    if max_w > 0:
        weights = np.where(weights >= 0.15 * max_w, weights, 0.0)

    # Mask out non-candidate pixels to prevent distant noise pulling the centroid
    if roi_mask is not None:
        weights = np.where(roi_mask > 0, weights, 0.0)

    total_weight = np.sum(weights)
    if total_weight <= 1e-6:
        return compute_geometric_centroid(roi_mask, x_offset, y_offset)

    h, w = roi_frame.shape
    # Pixel centers grid in continuous coordinates
    grid_y, grid_x = np.mgrid[0:h, 0:w]
    grid_x = grid_x.astype(np.float64) + 0.5
    grid_y = grid_y.astype(np.float64) + 0.5

    uc_local = np.sum(weights * grid_x) / total_weight
    vc_local = np.sum(weights * grid_y) / total_weight

    return float(uc_local + x_offset), float(vc_local + y_offset)


def _gaussian_2d(coords, u0, v0, amplitude, sigma, offset):
    """2D symmetric Gaussian model for surface fitting."""
    u, v = coords
    diff_sq = (u - u0) ** 2 + (v - v0) ** 2
    return amplitude * np.exp(-diff_sq / (2.0 * max(sigma, 0.5) ** 2)) + offset


def compute_gaussian_fit(
    roi_frame: np.ndarray,
    roi_mask: np.ndarray,
    bg_level: float,
    x_offset: int,
    y_offset: int,
    config: CentroidConfig,
) -> Tuple[float, float, bool]:
    """Compute subpixel centroid via 2D Gaussian Surface Fitting.

    Initializes with Weighted CoG, then refines parameters via non-linear
    least squares (Levenberg-Marquardt).

    Returns:
        Tuple of (u, v, fit_succeeded_flag)
    """
    # Initial estimate from Weighted CoG
    cog_u, cog_v = compute_weighted_cog(roi_frame, roi_mask, bg_level, x_offset, y_offset)
    init_u_local = cog_u - x_offset
    init_v_local = cog_v - y_offset

    h, w = roi_frame.shape
    grid_y, grid_x = np.mgrid[0:h, 0:w]
    u_flat = grid_x.ravel().astype(np.float64) + 0.5
    v_flat = grid_y.ravel().astype(np.float64) + 0.5
    z_flat = roi_frame.ravel().astype(np.float64)

    # Initial guesses: [u0, v0, amplitude, sigma, offset]
    amp_init = max(float(np.max(roi_frame) - bg_level), 10.0)
    sigma_init = max(min(float(w), float(h)) / 4.0, 1.0)
    p0 = [init_u_local, init_v_local, amp_init, sigma_init, bg_level]

    bounds = (
        [-2.0, -2.0, 1.0, 0.2, 0.0],
        [w + 2.0, h + 2.0, 300.0, max(float(w), float(h)), 255.0],
    )

    try:
        popt, _ = curve_fit(
            _gaussian_2d,
            (u_flat, v_flat),
            z_flat,
            p0=p0,
            bounds=bounds,
            maxfev=config.gaussian_fit_max_iter,
            ftol=config.gaussian_fit_tol,
        )
        u_fit, v_fit = popt[0], popt[1]

        # Verify sanity: fitted center must lie reasonably within the ROI bounds
        if -1.0 <= u_fit <= w + 1.0 and -1.0 <= v_fit <= h + 1.0:
            return float(u_fit + x_offset), float(v_fit + y_offset), True
    except Exception:
        pass

    # Safe fallback if fit fails or diverges
    return cog_u, cog_v, False
