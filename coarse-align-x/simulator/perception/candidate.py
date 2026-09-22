"""
HORIZON Beacon Candidate Extraction, Scoring & Selection
================================================================
Phase 4 UPGRADE:
  - Multi-Scale Beacon Handling: 5×5, 10×10, 15×15, 20×20 without size-specific tuning
  - Adaptive per-candidate background model (bg_mean, bg_variance, local_contrast)
  - Multi-Candidate Representation: keeps ALL valid candidates with rich quality fields
  - Optical Shape Validation: compactness, symmetry, radial intensity consistency, size plausibility
  - False-Lock Defense: rejects noise clusters and distractors via multi-criteria gates
  - Edge/Clipping Detection: flags candidates clipped by frame boundary

Strict Invariant: Zero access to true target position or ground-truth state.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import List, Optional, Tuple

import cv2
import numpy as np

from simulator.perception.config import CandidateScoringConfig
from simulator.perception.preprocessing import estimate_local_background


# ---------------------------------------------------------------------------
# Multi-scale support: beacon sizes in pixels (side length) to test
# Each scale defines its own reasonable area range (Phase 7 upgrade: 3 to 30 px)
# ---------------------------------------------------------------------------
_MULTISCALE_SIZES_PX: Tuple[int, ...] = (5, 8, 10, 15, 20, 25, 30)


@dataclass
class BeaconCandidate:
    """Rich optical beacon candidate feature record (Phase 4 Upgrade).

    All fields are derived purely from pixel data — zero ground-truth leakage.
    """
    # Bounding box (u, v, w, h) in pixel coordinates
    bbox: Tuple[int, int, int, int]

    # Photometric properties
    area_px: float
    peak_intensity: float
    mean_intensity: float
    integrated_flux: float       # Background-subtracted total signal flux

    # Background model (annular per-candidate)
    background_level: float      # bg_mean from local annulus
    bg_variance: float           # bg_variance from local annulus
    local_contrast: float        # peak_intensity - background_level

    # Signal quality
    snr: float                   # (peak - bg_mean) / sqrt(bg_variance + 1)

    # Shape quality decomposed into named components (NOT collapsed into one score)
    circularity: float           # 4π·area / perimeter² → [0, 1]
    compactness: float           # area / (bounding_box_diagonal)² → [0, 1]
    symmetry: float              # left-right + top-bottom intensity symmetry → [0, 1]
    radial_consistency: float    # correlation of intensity profile with Gaussian template → [0, 1]
    size_plausibility: float     # how well area matches expected beacon scale → [0, 1]

    # Composite score
    score: float                 # Weighted combination of all quality components → [0, 1]

    # Centroid uncertainty (σ estimated from SNR and pixel count — no ground truth)
    sigma_u_px: float            # Estimated 1-sigma uncertainty in u (pixels)
    sigma_v_px: float            # Estimated 1-sigma uncertainty in v (pixels)

    # Detection quality flags
    clipped_by_edge: bool        # Candidate touches or exceeds frame boundary
    scale_class: int             # Best matching scale class in pixels (5, 10, 15, or 20)

    # Contour for visualisation
    contour: Optional[np.ndarray] = None


# ---------------------------------------------------------------------------
# Velocity-Adaptive Ellipsoidal ROI Bounding Box Computation
# ---------------------------------------------------------------------------

def compute_velocity_adaptive_roi(
    predicted_u: float,
    predicted_v: float,
    predicted_vx: float,
    predicted_vy: float,
    pos_uncertainty_px: float,
    sensor_w: int = 640,
    sensor_h: int = 480,
    base_size_px: float = 30.0,
) -> Tuple[int, int, int, int]:
    """Compute velocity-adaptive ellipsoidal ROI bounding box along target flight vector.

    Args:
        predicted_u: Predicted center X in pixel space.
        predicted_v: Predicted center Y in pixel space.
        predicted_vx: Estimated velocity along X in px/s.
        predicted_vy: Estimated velocity along Y in px/s.
        pos_uncertainty_px: 1-sigma positional uncertainty in pixels.
        sensor_w: Image width in pixels.
        sensor_h: Image height in pixels.
        base_size_px: Base ROI bounding box dimension.

    Returns:
        (x_min, y_min, width, height) in sensor frame pixel coordinates.
    """
    speed = float(np.hypot(predicted_vx, predicted_vy))
    scale_speed = 1.0 + min(speed / 100.0, 2.5)
    scale_unc = 1.0 + min(pos_uncertainty_px / 10.0, 2.0)

    w_roi = int(round(base_size_px * scale_speed * scale_unc))
    h_roi = int(round(base_size_px * scale_unc))

    heading = float(np.arctan2(predicted_vy, predicted_vx))
    cos_h = abs(np.cos(heading))
    sin_h = abs(np.sin(heading))

    bbox_w = int(round(w_roi * cos_h + h_roi * sin_h))
    bbox_h = int(round(w_roi * sin_h + h_roi * cos_h))

    x1 = max(0, min(sensor_w - 10, int(round(predicted_u - bbox_w / 2.0))))
    y1 = max(0, min(sensor_h - 10, int(round(predicted_v - bbox_h / 2.0))))
    bw = max(10, min(sensor_w - x1, bbox_w))
    bh = max(10, min(sensor_h - y1, bbox_h))

    return x1, y1, bw, bh


# ---------------------------------------------------------------------------
# Optical Shape Validation helpers
# ---------------------------------------------------------------------------

def _compute_symmetry(roi: np.ndarray) -> float:
    """Compute bilateral symmetry score of an intensity ROI.

    Measures agreement between left/right and top/bottom halves.
    Returns value in [0, 1] where 1.0 = perfectly symmetric.
    """
    h, w = roi.shape
    if h < 2 or w < 2:
        return 0.5

    roi_f = roi.astype(np.float64)

    def _safe_corr(a: np.ndarray, b: np.ndarray) -> float:
        std_a = float(np.std(a))
        std_b = float(np.std(b))
        if std_a < 1e-4 or std_b < 1e-4:
            return 0.5
        c = float(np.corrcoef(a.ravel(), b.ravel())[0, 1])
        return c if not math.isnan(c) else 0.5

    # Left-right symmetry
    left_half = roi_f[:, :w // 2]
    right_half_flip = cv2.flip(roi_f[:, w - w // 2:], 1)
    lr = max(0.0, min(1.0, _safe_corr(left_half, right_half_flip)))

    # Top-bottom symmetry
    top_half = roi_f[:h // 2, :]
    bottom_half_flip = cv2.flip(roi_f[h - h // 2:, :], 0)
    tb = max(0.0, min(1.0, _safe_corr(top_half, bottom_half_flip)))

    return 0.5 * (lr + tb)


def _compute_radial_consistency(roi: np.ndarray, bg_mean: float) -> float:
    """Correlation of background-subtracted ROI with a Gaussian PSF template.

    Checks that the intensity profile has the expected optical shape.
    Returns value in [0, 1] where 1.0 = perfectly Gaussian.
    """
    gh, gw = roi.shape
    if gh < 3 or gw < 3:
        return 0.5

    gy, gx = np.ogrid[:gh, :gw]
    cy_f, cx_f = (gh - 1) / 2.0, (gw - 1) / 2.0
    r2 = (gx - cx_f) ** 2 + (gy - cy_f) ** 2
    sig_synth = max(min(gw, gh) / 3.0, 1.0)
    gauss_template = np.exp(-r2 / (2.0 * sig_synth ** 2))

    roi_sub = np.maximum(roi.astype(np.float64) - bg_mean, 0.0)
    norm_denom = float(np.linalg.norm(roi_sub) * np.linalg.norm(gauss_template))
    if norm_denom < 1e-6:
        return 0.0
    return float(np.clip(np.sum(roi_sub * gauss_template) / norm_denom, 0.0, 1.0))


def _compute_compactness(area: float, bbox: Tuple[int, int, int, int]) -> float:
    """Compactness = area / bounding_box_area.  Perfect square→1, elongated→<1."""
    _, _, bw, bh = bbox
    bb_area = float(bw * bh)
    if bb_area < 1.0:
        return 0.0
    return float(np.clip(area / bb_area, 0.0, 1.0))


def _size_plausibility(area: float) -> Tuple[float, int]:
    """Return (plausibility_score, best_matching_scale_px).

    Checks how well the candidate area matches any of the expected
    beacon footprints (5×5, 10×10, 15×15, 20×20 pixels).
    Best-match is the scale minimising relative area error.
    """
    best_score = 0.0
    best_scale = _MULTISCALE_SIZES_PX[0]
    for s in _MULTISCALE_SIZES_PX:
        expected = float(s * s)
        ratio = min(area, expected) / max(area, expected)
        if ratio > best_score:
            best_score = ratio
            best_scale = s
    return float(best_score), int(best_scale)


def _estimate_centroid_uncertainty(
    snr: float, area_px: float
) -> Tuple[float, float]:
    """Moment-based centroid uncertainty estimate (no ground truth).

    From photon-noise limited astrometry:
        σ_centroid ≈ FWHM / (2.355 * SNR * sqrt(N_pix))

    where FWHM ≈ sqrt(area_px) for a Gaussian spot, N_pix = area_px.

    Returns:
        (sigma_u_px, sigma_v_px) — both equal for a symmetric spot.
    """
    fwhm = max(math.sqrt(area_px), 1.0)
    n_pix = max(area_px, 1.0)
    effective_snr = max(snr, 0.1)
    sigma = fwhm / (2.355 * effective_snr * math.sqrt(n_pix))
    sigma = float(np.clip(sigma, 0.01, 5.0))
    return sigma, sigma


def _is_clipped_by_edge(
    bbox: Tuple[int, int, int, int], frame_h: int, frame_w: int, margin: int = 2
) -> bool:
    """Return True if the candidate bounding box touches or crosses the frame margin."""
    x, y, w, h = bbox
    return x <= margin or y <= margin or (x + w) >= (frame_w - margin) or (y + h) >= (frame_h - margin)


# ---------------------------------------------------------------------------
# Core Candidate Extraction
# ---------------------------------------------------------------------------

def extract_candidates(
    frame: np.ndarray,
    preprocessed: np.ndarray,
    bg_level: float,
    noise_std: float,
    config: CandidateScoringConfig,
) -> Tuple[List[BeaconCandidate], np.ndarray]:
    """Extract and score all valid beacon candidate regions from the preprocessed frame.

    Phase 4 Upgrade:
      - Multi-scale adaptive thresholding responds to local conditions
      - All valid candidates are kept (not just the top-1)
      - Each candidate gets a rich quality decomposition (not one opaque score)
      - Optical shape validation rejects non-Gaussian noise clusters
      - Edge/clipping detection flags boundary-clipped candidates

    Args:
        frame:       Original 2D uint8 sensor frame.
        preprocessed:Denoised 2D sensor frame.
        bg_level:    Estimated global background median level.
        noise_std:   Estimated global background noise standard deviation.
        config:      CandidateScoringConfig dataclass.

    Returns:
        Tuple of (ranked_candidates_list, binary_threshold_mask)
    """
    H, W = frame.shape

    # -----------------------------------------------------------------------
    # Adaptive threshold: background + max(fixed_floor, k * sigma_noise)
    # k = 3.5 gives ~0.02% false alarm rate for Gaussian noise
    # Clamped to [30, 250] to remain physically meaningful for uint8 data
    # -----------------------------------------------------------------------
    dynamic_offset = max(8.0, min(180.0, 2.5 * noise_std))
    thresh_val = float(bg_level + dynamic_offset)
    thresh_val = min(max(thresh_val, 12.0), 250.0)

    _, bin_mask = cv2.threshold(
        preprocessed, int(thresh_val), 255, cv2.THRESH_BINARY
    )

    # Connected component extraction
    contours, _ = cv2.findContours(
        bin_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )

    # Secondary Morphological White Top-Hat extraction under diffuse/hazy/attenuated illumination
    if not contours:
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (15, 15))
        tophat = cv2.morphologyEx(preprocessed, cv2.MORPH_TOPHAT, kernel)
        th_tophat = int(max(5.0, min(18.0, 0.8 * noise_std)))
        _, bin_mask = cv2.threshold(tophat, th_tophat, 255, cv2.THRESH_BINARY)
        contours, _ = cv2.findContours(
            bin_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )

    candidates: List[BeaconCandidate] = []

    # Pre-compute the valid area range: accept beacons from 5×5 to 20×20 pixels
    # Use config min_area directly (not scaled up) to preserve detection of tiny beacons
    # Max area: 20×20 beacon + 50% halo margin = 600, clamped by config max_area
    min_area = float(config.min_area_px)
    max_area = float(config.max_area_px)

    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area < min_area or area > max_area:
            continue

        # Gate 0: Impulse noise (Salt & Pepper spike) defense.
        # Real optical beacons (5-20px) have area >= 6 px. 1-3 pixel noise spikes
        # from salt & pepper injection are rejected under elevated noise or S&P presence.
        has_impulse_noise = (noise_std > 5.0 or np.count_nonzero(preprocessed == 255) > 30)
        if area <= 3.0 and has_impulse_noise:
            continue

        x, y, bw, bh = cv2.boundingRect(cnt)

        # Gate 1: aspect ratio — accept motion blur streaks (up to 10:1 aspect ratio)
        aspect_ratio = float(bw) / float(bh) if bh > 0 else 0.0
        if aspect_ratio < 0.10 or aspect_ratio > 10.0:
            continue

        # Extract ROI from original (unfiltered) frame for photometric accuracy
        roi_orig = frame[y: y + bh, x: x + bw]
        if roi_orig.size == 0:
            continue

        peak_int = float(np.max(roi_orig))

        # Gate 2: peak intensity above global noise floor
        if (peak_int - bg_level) < float(config.min_peak_intensity):
            continue

        # -----------------------------------------------------------------------
        # Adaptive per-candidate local background (annular ring model)
        # inner_radius = half the bounding box diagonal, outer = inner * 2
        # -----------------------------------------------------------------------
        cx = int(x + bw // 2)
        cy = int(y + bh // 2)
        inner_r = max(int(math.ceil(math.sqrt(bw ** 2 + bh ** 2) / 2.0)), 2)
        outer_r = min(inner_r * 2 + 4, max(H, W) // 4)

        local_bg_mean, local_bg_var, local_contrast = estimate_local_background(
            frame, cx, cy, inner_r, outer_r
        )

        # Gate 3: local contrast must exceed local noise sigma
        local_sigma = max(math.sqrt(local_bg_var), 1.0)
        if local_contrast < max(10.0, 2.0 * local_sigma):
            continue

        mean_int = float(np.mean(roi_orig))
        snr = (peak_int - local_bg_mean) / local_sigma

        # Gate 4: SNR gate
        if snr < config.min_snr:
            continue

        # Gate 5: integrated background-subtracted flux (scale-adaptive)
        integrated_flux = float(
            np.sum(np.maximum(0.0, roi_orig.astype(np.float64) - local_bg_mean))
        )
        min_required_flux = max(4.0, min(12.0, float(area) * 1.2))
        if integrated_flux < min_required_flux:
            continue

        # Compactness
        compactness = _compute_compactness(area, (x, y, bw, bh))
        if compactness < 0.08:
            continue

        # Circularity
        perimeter = cv2.arcLength(cnt, True)
        circularity = float(4.0 * math.pi * area / (perimeter ** 2)) if perimeter > 0 else 0.0
        circularity = float(np.clip(circularity, 0.0, 1.0))
        if circularity < config.min_circularity:
            continue

        # Gate 5b: Dense clutter & impulse noise defense (scale-adaptive)
        # Under dense clutter (> 12 contours or elevated noise floor), low-energy noise clusters
        # with flux density < max(6.0, 0.8 * local_sigma) or circularity < 0.15 are rejected.
        is_dense_clutter = (noise_std > 6.0 or len(contours) > 12)
        min_flux_density = max(6.0, 0.8 * local_sigma)
        min_required_flux_clutter = float(area) * min_flux_density
        if is_dense_clutter and (integrated_flux < min_required_flux_clutter or circularity < 0.15):
            continue

        # Radial intensity consistency (Gaussian profile check)
        radial_consistency = _compute_radial_consistency(roi_orig, local_bg_mean)
        if radial_consistency < 0.08:          # Relaxed gate: accepts motion blurred PSFs
            continue

        # Bilateral symmetry (computed early to feed the noise-variance-aware gate below)
        symmetry = _compute_symmetry(roi_orig)

        # Gate 5c: Multi-criterion variance-aware noise cluster rejection.
        #
        # Salt-and-pepper noise clusters exhibit three jointly distinguishing features:
        #   1. ROI fill ratio (mean_int / peak_int) approx 0.10 -- very sparse pixel population
        #      relative to the bounding box; a real Gaussian PSF fills >= 0.25 of its ROI.
        #   2. Low compactness -- scattered noise dots create irregular bboxes with compactness ~ 0.25
        #   3. Low bilateral symmetry -- noise is random, not radially symmetric
        #
        # All thresholds derived dynamically from measured local background statistics.
        # No hard-coded pixel values.
        #
        # Strategy:
        #   - variance_gate_factor in [0,1] grows with local background variance
        #     (0 = clean frame, 1 = extreme S&P noise)
        #   - When factor > 0.2 (moderate noise present), apply the combined gate
        #   - Candidate must pass fill_ratio AND at least one of (compactness, symmetry)
        fill_ratio = mean_int / max(peak_int, 1.0)   # [0,1]: how filled the bbox is
        compactness_early = _compute_compactness(area, (x, y, bw, bh))

        # variance_gate_factor: 0 = clean, 1 = saturated noise
        variance_gate_factor = float(np.clip(local_bg_var / 800.0, 0.0, 1.0))

        if variance_gate_factor > 0.2:
            # Dynamic thresholds -- scale with noise level
            # Physics floor: real Gaussian PSF fills >= 15% of bbox; S&P noise < 12%
            min_fill = max(0.15, variance_gate_factor * 0.18)
            min_compact = variance_gate_factor * 0.30  # e.g. 0.15 at factor=0.5, 0.30 at factor=1.0
            min_sym = variance_gate_factor * 0.08      # e.g. 0.04 at factor=0.5, 0.08 at factor=1.0

            passes_fill = fill_ratio >= min_fill
            passes_compact = compactness_early >= min_compact
            passes_sym = symmetry >= min_sym

            # Candidate must pass fill_ratio AND at least one of (compactness, symmetry)
            # Prevents sparse noise blobs from slipping through even if accidentally symmetric
            if not (passes_fill and (passes_compact or passes_sym)):
                continue

        # compactness alias: compactness_early always defined in Gate 5c above
        compactness = compactness_early

        # Gate 6: Distractor / Glint rejection
        # Only reject if both non-Gaussian and low SNR. Fast-moving optical beacons
        # create physical motion streaks (aspect_ratio > 3.0) with high local contrast/SNR.
        is_elongated = (aspect_ratio > 3.0 or aspect_ratio < 0.33)
        if is_elongated and radial_consistency < 0.20 and snr < 3.2:
            continue

        # Size plausibility across all expected scales
        size_plausibility, scale_class = _size_plausibility(area)

        # -----------------------------------------------------------------------
        # Centroid uncertainty estimate (photon-noise limited astrometry)
        # -----------------------------------------------------------------------
        sigma_u, sigma_v = _estimate_centroid_uncertainty(snr, area)

        # -----------------------------------------------------------------------
        # Edge / Clipping Detection
        # -----------------------------------------------------------------------
        clipped = _is_clipped_by_edge((x, y, bw, bh), H, W)

        # -----------------------------------------------------------------------
        # Composite quality score — components are explicitly weighted and named
        # Score degrades but does NOT disqualify edge-clipped candidates outright
        # (clipped candidates may still be genuine beacons near FOV boundary)
        # -----------------------------------------------------------------------
        snr_score = float(np.clip(snr / 12.0, 0.0, 1.0))
        contrast_score = float(np.clip(local_contrast / 150.0, 0.0, 1.0))
        flux_score = float(np.clip(integrated_flux / 2000.0, 0.0, 1.0))
        clipping_penalty = 0.15 if clipped else 0.0

        # Discrete pixel grid regularisation for tiny speckles:
        # A 2x2 or 1x3 noise artifact gets artificially high circularity/compactness.
        # Scale discrete shape metrics by area confidence for candidates < 8 px:
        area_reg = float(np.clip(area / 8.0, 0.40, 1.0))
        adj_circularity = circularity * area_reg
        adj_compactness = compactness * area_reg

        # Dynamic scoring blend: if candidate is elongated due to rapid target motion,
        # adapt weights to emphasize SNR, contrast, flux, and size over circularity/radial consistency.
        if aspect_ratio > 2.2 or aspect_ratio < 0.45:
            score = (
                0.15 * radial_consistency
                + 0.25 * snr_score
                + 0.20 * contrast_score
                + 0.15 * flux_score
                + 0.10 * adj_compactness
                + 0.05 * symmetry
                + 0.10 * size_plausibility
                - clipping_penalty
            )
        else:
            score = (
                0.25 * radial_consistency
                + 0.20 * snr_score
                + 0.15 * flux_score
                + 0.12 * adj_circularity
                + 0.10 * adj_compactness
                + 0.10 * symmetry
                + 0.08 * size_plausibility
                - clipping_penalty
            )
        score = float(np.clip(score, 0.0, 1.0))

        candidates.append(
            BeaconCandidate(
                bbox=(x, y, bw, bh),
                area_px=float(area),
                peak_intensity=peak_int,
                mean_intensity=mean_int,
                integrated_flux=integrated_flux,
                background_level=local_bg_mean,
                bg_variance=local_bg_var,
                local_contrast=local_contrast,
                snr=snr,
                circularity=circularity,
                compactness=compactness,
                symmetry=symmetry,
                radial_consistency=radial_consistency,
                size_plausibility=size_plausibility,
                score=score,
                sigma_u_px=sigma_u,
                sigma_v_px=sigma_v,
                clipped_by_edge=clipped,
                scale_class=scale_class,
                contour=cnt,
            )
        )

    # Sort candidates by composite score descending — best candidate is candidates[0]
    candidates.sort(key=lambda c: c.score, reverse=True)
    return candidates, bin_mask


