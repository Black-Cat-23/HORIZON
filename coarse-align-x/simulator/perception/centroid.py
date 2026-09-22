"""
HORIZON Subpixel Centroid Estimation Algorithms
======================================================
Algorithms for high-precision subpixel beacon centroid localization:
  1. Geometric Centroid (Binary spatial moments) + uncertainty
  2. Weighted Center of Gravity (Intensity-weighted CoG) + propagated uncertainty
  3. 2D Anisotropic Gaussian Surface Fit (Non-linear least squares) + covariance uncertainty

Strict Invariant:
  - Zero integer truncation. Returns pure floating-point coordinates.
  - No ground-truth information used in any method.
  - Uncertainty is derived from photon statistics of the ROI data only.
"""

from __future__ import annotations

import math
from typing import Tuple

import cv2
import numpy as np
from scipy.optimize import curve_fit

from simulator.perception.config import CentroidConfig


# ---------------------------------------------------------------------------
# 1. Geometric Centroid (Binary Spatial Moments)
# ---------------------------------------------------------------------------

def compute_geometric_centroid(
    roi_mask: np.ndarray, x_offset: int, y_offset: int
) -> Tuple[float, float, float, float]:
    """Compute geometric centroid from binary mask moments."""
    sigma = 0.5
    if roi_mask is not None:
        m = cv2.moments(roi_mask.astype(np.uint8))
        if m["m00"] > 0:
            uc = (m["m10"] / m["m00"]) + 0.5 + float(x_offset)
            vc = (m["m01"] / m["m00"]) + 0.5 + float(y_offset)
            return float(uc), float(vc), sigma, sigma

    h, w = (10, 10) if roi_mask is None else roi_mask.shape
    return float(x_offset + w / 2.0), float(y_offset + h / 2.0), sigma, sigma


# ---------------------------------------------------------------------------
# 2. Weighted Center of Gravity (Intensity-weighted CoG)
# ---------------------------------------------------------------------------

def compute_weighted_cog(
    roi_frame: np.ndarray,
    roi_mask: np.ndarray,
    bg_level: float,
    x_offset: int,
    y_offset: int,
) -> Tuple[float, float, float, float]:
    """Compute intensity-weighted Center of Gravity with subpixel precision.

    Returns:
        (u, v, sigma_u_px, sigma_v_px) in frame pixel coordinates.
    """
    if roi_frame.shape[0] >= 3 and roi_frame.shape[1] >= 3:
        clean_roi = cv2.medianBlur(roi_frame, 3)
    else:
        clean_roi = roi_frame

    roi_float = clean_roi.astype(np.float64)
    weights = np.maximum(roi_float - bg_level, 0.0)
    max_w = np.max(weights) if weights.size > 0 else 0.0
    if max_w > 0:
        weights = np.where(weights >= 0.15 * max_w, weights, 0.0)

    if roi_mask is not None:
        weights = np.where(roi_mask > 0, weights, 0.0)

    total_weight = np.sum(weights)
    if total_weight <= 1e-6:
        u, v, su, sv = compute_geometric_centroid(roi_mask, x_offset, y_offset)
        return u, v, su, sv

    h, w = roi_frame.shape
    grid_y, grid_x = np.mgrid[0:h, 0:w]
    grid_x = grid_x.astype(np.float64) + 0.5
    grid_y = grid_y.astype(np.float64) + 0.5

    uc_local = np.sum(weights * grid_x) / total_weight
    vc_local = np.sum(weights * grid_y) / total_weight

    var_u = float(np.sum(weights * (grid_x - uc_local) ** 2)) / (total_weight ** 2) * total_weight
    var_v = float(np.sum(weights * (grid_y - vc_local) ** 2)) / (total_weight ** 2) * total_weight
    sigma_u = float(np.clip(math.sqrt(max(var_u, 1e-4)), 0.01, 5.0))
    sigma_v = float(np.clip(math.sqrt(max(var_v, 1e-4)), 0.01, 5.0))

    return float(uc_local + x_offset), float(vc_local + y_offset), sigma_u, sigma_v


# ---------------------------------------------------------------------------
# 3. 2D Anisotropic Gaussian Surface Fit
# ---------------------------------------------------------------------------

def _gaussian_2d_anisotropic(coords, u0, v0, amplitude, sigma_u, sigma_v, offset):
    """2D anisotropic Gaussian model for high-precision surface fitting."""
    u, v = coords
    du = u - u0
    dv = v - v0
    su = max(sigma_u, 0.5)
    sv = max(sigma_v, 0.5)
    return amplitude * np.exp(-((du**2) / (2.0 * su**2) + (dv**2) / (2.0 * sv**2))) + offset


def compute_gaussian_fit(
    roi_frame: np.ndarray,
    roi_mask: np.ndarray,
    bg_level: float,
    x_offset: int,
    y_offset: int,
    config: CentroidConfig,
) -> Tuple[float, float, float, float, bool]:
    """Compute subpixel centroid via 2D Anisotropic Gaussian Surface Fitting."""
    cog_u, cog_v, cog_su, cog_sv = compute_weighted_cog(
        roi_frame, roi_mask, bg_level, x_offset, y_offset
    )
    init_u_local = cog_u - x_offset
    init_v_local = cog_v - y_offset

    h, w = roi_frame.shape
    grid_y, grid_x = np.mgrid[0:h, 0:w]
    u_flat = grid_x.ravel().astype(np.float64) + 0.5
    v_flat = grid_y.ravel().astype(np.float64) + 0.5
    z_flat = roi_frame.ravel().astype(np.float64)

    amp_init = max(float(np.max(roi_frame) - bg_level), 10.0)
    sigma_init = max(min(float(w), float(h)) / 4.0, 1.0)
    p0 = [init_u_local, init_v_local, amp_init, sigma_init, sigma_init, bg_level]

    bounds = (
        [-2.0, -2.0, 1.0, 0.2, 0.2, 0.0],
        [w + 2.0, h + 2.0, 300.0, max(float(w), float(h)), max(float(w), float(h)), 255.0],
    )

    try:
        popt, pcov = curve_fit(
            _gaussian_2d_anisotropic,
            (u_flat, v_flat),
            z_flat,
            p0=p0,
            bounds=bounds,
            maxfev=config.gaussian_fit_max_iter,
            ftol=config.gaussian_fit_tol,
        )
        u_fit, v_fit = popt[0], popt[1]

        if -1.0 <= u_fit <= w + 1.0 and -1.0 <= v_fit <= h + 1.0:
            perr = np.sqrt(np.diag(np.abs(pcov)))
            sigma_u_fit = float(np.clip(perr[0], 0.005, 2.0))
            sigma_v_fit = float(np.clip(perr[1], 0.005, 2.0))
            return (
                float(u_fit + x_offset),
                float(v_fit + y_offset),
                sigma_u_fit,
                sigma_v_fit,
                True,
            )
    except (RuntimeError, ValueError):
        pass

    return cog_u, cog_v, cog_su, cog_sv, False
