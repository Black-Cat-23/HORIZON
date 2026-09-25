"""
HORIZON Perception Preprocessing & Input Validation
==========================================================
Phase 4 UPGRADE: Multi-scale adaptive background estimation, adaptive median
filtering, and robust noise characterisation for optical camera sensor frames.

Exports:
    validate_input_frame         — strict (480, 640) uint8 enforcer
    apply_adaptive_median_filter — impulse-noise removal preserving subpixel edges
    estimate_background_statistics — robust MAD-based global bg statistics
    estimate_local_background    — per-candidate annular background model exposing
                                   bg_mean, bg_variance, local_contrast

Strict Invariant: Does not access ground truth. Validates all array inputs.
"""

from __future__ import annotations

from typing import Tuple
import cv2
import numpy as np

from simulator.perception.config import PreprocessingConfig


# ---------------------------------------------------------------------------
# 1.  Input Validation
# ---------------------------------------------------------------------------

def validate_input_frame(
    frame: object, expected_width: int = 640, expected_height: int = 480
) -> np.ndarray:
    """Rigorous input frame validation.

    Enforces:
      - Valid numpy ndarray
      - Exact dimensions (height, width) == (480, 640)
      - Single-channel grayscale (2D array, not 3D / RGB)
      - Dtype is uint8
      - Non-empty, no NaNs, no Infinities

    Returns:
        Validated 2D uint8 numpy array.

    Raises:
        ValueError / TypeError: With clear descriptive error message on violation.
    """
    if frame is None:
        raise ValueError("Input frame is None. Expected valid (480, 640) numpy array.")

    if not isinstance(frame, np.ndarray):
        raise TypeError(f"Input frame must be a numpy.ndarray, got {type(frame).__name__}")

    if frame.size == 0:
        raise ValueError("Input frame is empty (0 elements).")

    # Reject multi-channel (e.g. RGB or BGR)
    if frame.ndim != 2:
        if frame.ndim == 3 and frame.shape[2] in (3, 4):
            raise ValueError(
                f"Multi-channel RGB/RGBA frame rejected. Expected 2D grayscale ({expected_height}, {expected_width}), "
                f"got shape {frame.shape}. Convert to single-channel grayscale before passing."
            )
        raise ValueError(
            f"Invalid array dimensions: expected 2D ({expected_height}, {expected_width}), got ndim={frame.ndim} shape={frame.shape}"
        )

    # Check dimensions
    h, w = frame.shape
    if h != expected_height or w != expected_width:
        raise ValueError(
            f"Invalid frame dimensions: expected ({expected_height}, {expected_width}), got ({h}, {w})"
        )

    # Check dtype
    if frame.dtype != np.uint8:
        # Check for NaN / Inf in non-integer arrays
        if np.issubdtype(frame.dtype, np.floating):
            if np.isnan(frame).any() or np.isinf(frame).any():
                raise ValueError("Input frame contains NaN or Infinity values.")
        raise TypeError(f"Invalid frame dtype: expected uint8, got {frame.dtype}")

    return frame


# ---------------------------------------------------------------------------
# 2.  Adaptive Impulse-Noise Removal
# ---------------------------------------------------------------------------

def apply_adaptive_median_filter(
    frame: np.ndarray, config: PreprocessingConfig
) -> np.ndarray:
    """Adaptive impulse-noise (Salt & Pepper) removal filter."""
    if not config.enable_adaptive_median:
        return frame.copy()

    # Fast check: skip expensive median filter passes if frame has no S&P noise spikes
    has_sp_noise = np.any((frame == 0) | (frame == 255))
    if not has_sp_noise:
        return frame

    # Stage 1: 3×3 median — catches isolated single-pixel S&P spikes
    med3 = cv2.medianBlur(frame, 3)
    diff3 = cv2.absdiff(frame, med3)
    is_impulse = (diff3 > 40)
    denoised = np.where(is_impulse, med3, frame)

    # Stage 2: 5×5 check for dense 10% S&P clusters
    if config.max_median_window >= 5:
        med5 = cv2.medianBlur(denoised, 5)
        diff5 = cv2.absdiff(denoised, med5)
        rem_impulse = (denoised <= 5) | (denoised >= 245) | (diff5 > 30)
        denoised = np.where(rem_impulse, med5, denoised)

    return denoised.astype(np.uint8)


# ---------------------------------------------------------------------------
# 3.  Global Background Statistics (Robust MAD)
# ---------------------------------------------------------------------------

def estimate_background_statistics(frame: np.ndarray) -> Tuple[float, float]:
    """Robust global background level and noise-floor std via MAD.

    Sparse 4-pixel stride sampling prevents the small high-intensity beacon
    from biasing the background median.

    Returns:
        Tuple of (bg_median: float, noise_std_est: float)
    """
    sample = frame[::4, ::4].astype(np.float64)
    med = float(np.median(sample))
    mad = float(np.median(np.abs(sample - med)))
    # For Gaussian noise: σ ≈ 1.4826 × MAD
    noise_std = max(1.4826 * mad, 1.0)
    return med, noise_std


# ---------------------------------------------------------------------------
# 4.  Per-Candidate Adaptive Local Background Model
# ---------------------------------------------------------------------------

def estimate_local_background(
    frame: np.ndarray,
    cx: int,
    cy: int,
    inner_radius: int,
    outer_radius: int,
) -> Tuple[float, float, float]:
    """Estimate background statistics in an annular region around a candidate."""
    H, W = frame.shape

    # Clamp bounding box to image extents
    x0 = max(0, cx - outer_radius)
    y0 = max(0, cy - outer_radius)
    x1 = min(W, cx + outer_radius + 1)
    y1 = min(H, cy + outer_radius + 1)

    if x1 <= x0 or y1 <= y0:
        med, noise_std = estimate_background_statistics(frame)
        return med, noise_std ** 2, 0.0

    region = frame[y0:y1, x0:x1].astype(np.float32)
    gy, gx = np.ogrid[0: region.shape[0], 0: region.shape[1]]
    gy_f = (gy + y0 - cy).astype(np.float32)
    gx_f = (gx + x0 - cx).astype(np.float32)
    dist_sq = gx_f ** 2 + gy_f ** 2

    r_in2 = float(inner_radius ** 2)
    r_out2 = float(outer_radius ** 2)

    annulus_mask = (dist_sq >= r_in2) & (dist_sq <= r_out2)
    annulus_pixels = region[annulus_mask]

    if annulus_pixels.size < 4:
        med, noise_std = estimate_background_statistics(frame)
        return med, noise_std ** 2, 0.0

    bg_mean = float(np.mean(annulus_pixels))
    bg_variance = float(np.var(annulus_pixels))

    inner_mask = dist_sq < r_in2
    inner_pixels = region[inner_mask]
    peak_inner = float(np.max(inner_pixels)) if inner_pixels.size > 0 else bg_mean

    local_contrast = max(0.0, peak_inner - bg_mean)
    return bg_mean, bg_variance, local_contrast
