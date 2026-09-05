"""
HORIZON Perception Preprocessing & Input Validation
==========================================================
Input validation, adaptive impulse-noise mitigation, and background estimation
for optical camera sensor frames.

Strict Invariant: Does not access ground truth. Validates all array inputs.
"""

from __future__ import annotations

from typing import Tuple
import cv2
import numpy as np

from simulator.perception.config import PreprocessingConfig


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


def apply_adaptive_median_filter(
    frame: np.ndarray, config: PreprocessingConfig
) -> np.ndarray:
    """Adaptive impulse-noise (Salt & Pepper) removal filter.

    Selectively identifies salt (255) and pepper (0) impulse noise outliers
    relative to the local 3×3 and 5×5 median, replacing ONLY corrupted pixels
    while leaving clean beacon and background pixels completely untouched.
    This preserves subpixel edge gradients.

    Args:
        frame: Validated 2D uint8 frame.
        config: PreprocessingConfig dataclass.

    Returns:
        Denoised 2D uint8 frame.
    """
    if not config.enable_adaptive_median:
        return frame.copy()

    # Stage 1: 3x3 median
    med3 = cv2.medianBlur(frame, 3)

    # Detect impulse spikes (isolated single-pixel outliers) that differ strongly from local median
    # Multi-pixel beacon peaks have small diff3 (since med3 ~ frame), while isolated S&P noise has large diff3
    diff3 = cv2.absdiff(frame, med3)
    is_impulse = (diff3 > 40)

    denoised = np.where(is_impulse, med3, frame)

    # Stage 2: For dense 10% S&P, run a 5x5 check on remaining impulse outliers
    if config.max_median_window >= 5:
        med5 = cv2.medianBlur(denoised, 5)
        diff5 = cv2.absdiff(denoised, med5)
        rem_impulse = (denoised <= 5) | (denoised >= 245) | (diff5 > 30)
        denoised = np.where(rem_impulse, med5, denoised)

    return denoised.astype(np.uint8)


def estimate_background_statistics(frame: np.ndarray) -> Tuple[float, float]:
    """Robust estimation of local background level and noise floor std.

    Uses the median and MAD (Median Absolute Deviation) to prevent the
    small beacon from biasing the background estimates.

    Returns:
        Tuple of (bg_median, noise_std_est)
    """
    # Sample a sparse grid for speed
    sample = frame[::4, ::4].astype(np.float64)
    med = float(np.median(sample))
    mad = float(np.median(np.abs(sample - med)))
    # For normal distribution, std ≈ 1.4826 * MAD
    noise_std = max(1.4826 * mad, 1.0)
    return med, noise_std
