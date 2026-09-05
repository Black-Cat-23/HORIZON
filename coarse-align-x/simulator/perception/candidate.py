"""
HORIZON Beacon Candidate Extraction, Scoring & Selection
================================================================
Extracts candidate regions, filters false alarms/distractors, and computes
confidence metrics without ground-truth information.

Strict Invariant: Zero access to true target position or ground-truth state.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import List, Optional, Tuple
import cv2
import numpy as np

from simulator.perception.config import CandidateScoringConfig


@dataclass(frozen=True)
class BeaconCandidate:
    """Extracted beacon candidate feature record."""
    bbox: Tuple[int, int, int, int]  # (x, y, w, h)
    area_px: float
    peak_intensity: float
    mean_intensity: float
    background_level: float
    snr: float
    circularity: float
    score: float
    contour: np.ndarray


def extract_candidates(
    frame: np.ndarray,
    preprocessed: np.ndarray,
    bg_level: float,
    noise_std: float,
    config: CandidateScoringConfig,
) -> Tuple[List[BeaconCandidate], np.ndarray]:
    """Extract and score candidate beacon regions from the preprocessed frame.

    Args:
        frame: Original 2D sensor frame.
        preprocessed: Denoised 2D sensor frame.
        bg_level: Estimated background median level.
        noise_std: Estimated background noise standard deviation.
        config: CandidateScoringConfig dataclass.

    Returns:
        Tuple of (ranked_candidates_list, binary_threshold_mask)
    """
    # 1. Dynamic adaptive thresholding
    # Signal threshold: background + max(offset, 3.2 * noise_std)
    thresh_val = float(bg_level + max(15.0, 3.2 * noise_std))
    thresh_val = min(max(thresh_val, 30.0), 250.0)

    _, bin_mask = cv2.threshold(
        preprocessed, int(thresh_val), 255, cv2.THRESH_BINARY
    )

    # 2. Find connected components / contours
    contours, _ = cv2.findContours(
        bin_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )

    candidates: List[BeaconCandidate] = []
    expected_area = (config.expected_size_px) ** 2

    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area < config.min_area_px or area > config.max_area_px:
            continue

        x, y, w, h = cv2.boundingRect(cnt)
        aspect_ratio = float(w) / float(h) if h > 0 else 0.0
        # Reject extreme aspect ratios (lines, streaks)
        if aspect_ratio < 0.25 or aspect_ratio > 4.0:
            continue

        # Extract ROI statistics
        roi_orig = frame[y : y + h, x : x + w]
        if roi_orig.size == 0:
            continue

        peak_int = float(np.max(roi_orig))
        if (peak_int - bg_level) < config.min_peak_intensity:
            continue

        mean_int = float(np.mean(roi_orig))
        snr = (peak_int - bg_level) / max(noise_std, 1.0)
        if snr < config.min_snr:
            continue

        # Calculate local surrounding ring background
        y1_ring = max(0, y - 3)
        y2_ring = min(frame.shape[0], y + h + 3)
        x1_ring = max(0, x - 3)
        x2_ring = min(frame.shape[1], x + w + 3)
        roi_env = frame[y1_ring:y2_ring, x1_ring:x2_ring]

        # Surround ring mask = environment minus candidate bbox
        ring_mask = np.ones(roi_env.shape, dtype=bool)
        ry1, ry2 = y - y1_ring, y - y1_ring + h
        rx1, rx2 = x - x1_ring, x - x1_ring + w
        ring_mask[ry1:ry2, rx1:rx2] = False

        ring_pixels = roi_env[ring_mask]
        ring_mean = float(np.mean(ring_pixels)) if ring_pixels.size > 0 else bg_level
        ring_std = float(np.std(ring_pixels)) if ring_pixels.size > 0 else max(noise_std, 1.0)

        # Reject local noise spikes lacking contrast above local surrounding background
        local_contrast = peak_int - ring_mean
        if local_contrast < max(15.0, 2.5 * noise_std):
            continue

        # Reject noise clusters lacking sufficient integrated signal flux
        integrated_flux = float(np.sum(np.maximum(0.0, roi_orig.astype(float) - ring_mean)))
        if integrated_flux < 15.0:
            continue

        # 2D Gaussian spatial correlation check
        # Synthesize expected 2D Gaussian template matching ROI dimensions
        gh, gw = roi_orig.shape
        gy, gx = np.ogrid[:gh, :gw]
        cy_f, cx_f = (gh - 1) / 2.0, (gw - 1) / 2.0
        r2 = (gx - cx_f) ** 2 + (gy - cy_f) ** 2
        sig_synth = max(min(gw, gh) / 3.0, 1.0)
        gauss_template = np.exp(-r2 / (2.0 * sig_synth ** 2))

        # Normalized cross-correlation coefficient between ROI and Gaussian template
        roi_norm = (roi_orig.astype(float) - ring_mean)
        roi_norm = np.maximum(roi_norm, 0.0)
        norm_denom = (np.linalg.norm(roi_norm) * np.linalg.norm(gauss_template))
        gauss_corr = float(np.sum(roi_norm * gauss_template) / norm_denom) if norm_denom > 0 else 0.0

        # Reject candidates with poor spatial Gaussian correlation (random noise clusters)
        if gauss_corr < 0.20:
            continue

        # Compute circularity: 4 * pi * Area / Perimeter^2
        perimeter = cv2.arcLength(cnt, True)
        if perimeter > 0:
            circularity = float(4.0 * math.pi * area / (perimeter ** 2))
        else:
            circularity = 0.0

        circularity = min(max(circularity, 0.0), 1.0)
        if circularity < config.min_circularity:
            continue

        # Composite candidate score in [0, 1] incorporating Gaussian shape fidelity
        area_ratio = min(area, expected_area) / max(area, expected_area)
        snr_score = min(snr / 10.0, 1.0)
        peak_score = min(local_contrast / 180.0, 1.0)

        score = (
            0.35 * gauss_corr
            + 0.25 * snr_score
            + 0.20 * area_ratio
            + 0.10 * peak_score
            + 0.10 * circularity
        )
        score = float(np.clip(score, 0.0, 1.0))

        candidates.append(
            BeaconCandidate(
                bbox=(x, y, w, h),
                area_px=float(area),
                peak_intensity=peak_int,
                mean_intensity=mean_int,
                background_level=bg_level,
                snr=snr,
                circularity=circularity,
                score=score,
                contour=cnt,
            )
        )

    # Sort candidates by composite score descending
    candidates.sort(key=lambda c: c.score, reverse=True)
    return candidates, bin_mask
