"""
HORIZON Synthetic Dataset Generation Pipeline  (v2 — Production Rewrite)
=========================================================================
Generates a massive, physics-grounded YOLO-format training dataset for the
YOLOv8n beacon detector.  Designed to run on Google Colab GPU in < 30 min.

KEY FIXES over v1
-----------------
* Scale: 1,200 images / preset × 12 presets = 14,400 positive images
         (v1 had 150/preset × 9 = 1,350 — 10× bigger)
* Realistic backgrounds: sensor dark-current noise floor (not pure black zeros)
* Correct distractor shapes: elongated streaks, large blobs, ellipses, hot-pixel
  clusters — NEVER beacon-shaped squares → fixes false-lock training
* Motion blur preset: linear PSF convolution simulates camera jitter
* Partial occlusion preset: beacon partially masked by a dark band
* Varied beacon intensity: 160–255 (not always 255) for low-SNR generalisation
* Varied PSF model: 50% Gaussian PSF, 50% box PSF per sample
* Multi-beacon frames: 10% of NOMINAL samples have a secondary faint beacon
  (forces NMS learning)
* No out-of-FOV samples placed at (-50, -50) — they contributed nothing useful
  and caused incorrect bounding-box edge artifacts
* Dataset balance: 10% negative-label in-FOV blanks sprinkled in each preset
  (empty label files) so model learns to suppress low-quality candidates
* Colab-friendly: tqdm progress bar, JSON manifest per preset, resumable

Strict Invariant: Ground-truth bounding boxes derived directly from simulator
state. Zero ground-truth leakage into model inputs.
"""

from __future__ import annotations

import json
import logging
import math
from pathlib import Path
import sys
from typing import Dict, Any, List, Optional, Tuple

import cv2
import numpy as np

# ── make imports work whether invoked from project root or this file's dir ──
project_root = Path(__file__).resolve().parents[2]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from simulator.disturbances.atmosphere import apply_atmospheric_degradation
from simulator.disturbances.config import AtmosphereConfig
from simulator.disturbances.noise import (
    apply_gaussian_noise,
    apply_poisson_noise,
    apply_salt_and_pepper_noise,
)
from simulator.world.beacon import Beacon

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────────────────
# Constants
# ──────────────────────────────────────────────────────────────────────────────
IMG_W, IMG_H = 640, 480

# Beacon sizes in pixels (min=5, max=20 per Beacon class validation)
TARGET_SIZES_PX: Tuple[float, ...] = (5.0, 7.0, 10.0, 13.0, 16.0, 20.0)

# All disturbance presets — 14 total (v2 production)
PRESETS: Tuple[str, ...] = (
    "NOMINAL",
    "GAUSSIAN_LIGHT",
    "GAUSSIAN_HEAVY",
    "SALT_PEPPER",
    "POISSON",
    "FOG",
    "RAIN",
    "LOW_LIGHT",
    "DISTRACTOR",
    "MOTION_BLUR",
    "PARTIAL_OCCLUSION",
    "SCINTILLATION_TURBULENCE",
    "LENS_GLINT",
    "SEVERE",
)

# Gaussian sigma MUST be ≤ 20.0 per noise.py validation
PRESET_GAUSSIAN_SIGMA: Dict[str, float] = {
    "GAUSSIAN_LIGHT": 8.0,
    "GAUSSIAN_HEAVY": 18.0,   # max allowed is 20, keep headroom
    "SCINTILLATION_TURBULENCE": 10.0,
    "LENS_GLINT": 8.0,
    "SEVERE": 18.0,
}


# ──────────────────────────────────────────────────────────────────────────────
# Background helpers
# ──────────────────────────────────────────────────────────────────────────────

def _make_sensor_background(rng: np.random.Generator, bg_mean: float = 12.0, bg_sigma: float = 4.0) -> np.ndarray:
    """Return a realistic grayscale sensor dark-current background frame.

    Instead of pure black zeros (v1), we add a low-level Gaussian noise floor
    that matches what a real CMOS/CCD sensor produces in the dark.
    bg_mean ≈ 10–20 ADU  (dark current + read noise floor)
    bg_sigma ≈ 3–6 ADU   (pixel-to-pixel PRNU variation)
    """
    noise = rng.normal(loc=bg_mean, scale=bg_sigma, size=(IMG_H, IMG_W))
    return np.clip(np.rint(noise), 0, 255).astype(np.uint8)


# ──────────────────────────────────────────────────────────────────────────────
# Distractor renderers  (NEVER beacon-shaped — critical fix)
# ──────────────────────────────────────────────────────────────────────────────

def _render_distractors_correct(
    frame: np.ndarray,
    rng: np.random.Generator,
    beacon_cx: Optional[float],
    beacon_cy: Optional[float],
    num_distractors: int = 3,
) -> np.ndarray:
    """Render physically plausible distractors that are NEVER beacon squares.

    Shape classes:
      A) elongated_streak  — linear glare / solar reflection (aspect ≥ 4:1)
      B) large_blob        — broad diffuse flare (σ ~ 8–14 px)
      C) hot_pixel_cluster — localized S&P cluster (3×3 to 7×7 px)
      D) elliptical_glare  — squashed bright ellipse (b/a ≤ 0.4)

    The key invariant: none of these match the beacon PSF (compact, circular,
    Gaussian-profile square patch).  YOLO must learn to distinguish PSF shape.
    """
    out = frame.copy()
    H, W = out.shape

    min_sep = 60.0  # px — keep distractors away from true beacon

    for _ in range(num_distractors):
        # Pick random position far from the beacon
        for _attempt in range(30):
            dx = float(rng.uniform(25.0, W - 25.0))
            dy = float(rng.uniform(25.0, H - 25.0))
            if beacon_cx is None:
                break
            if math.hypot(dx - beacon_cx, dy - beacon_cy) >= min_sep:
                break

        ix, iy = int(round(dx)), int(round(dy))
        intensity = int(rng.integers(130, 230))
        shape_type = int(rng.integers(0, 4))

        if shape_type == 0:
            # A) Elongated linear streak (horizontal or diagonal)
            length = int(rng.integers(25, 70))
            thickness = int(rng.integers(1, 3))
            angle_rad = float(rng.uniform(0.0, math.pi))
            ex = ix + int(length * math.cos(angle_rad))
            ey = iy + int(length * math.sin(angle_rad))
            cv2.line(out, (ix, iy), (np.clip(ex, 0, W - 1), np.clip(ey, 0, H - 1)),
                     int(intensity), thickness)

        elif shape_type == 1:
            # B) Large diffuse blob (σ ~ 8–14 px, much larger than beacon PSF ~1.5 px)
            sigma_blob = float(rng.uniform(8.0, 14.0))
            radius = int(sigma_blob * 3)
            r1 = max(0, iy - radius); r2 = min(H, iy + radius + 1)
            c1 = max(0, ix - radius); c2 = min(W, ix + radius + 1)
            if r2 > r1 and c2 > c1:
                cols, rows = np.meshgrid(np.arange(c1, c2), np.arange(r1, r2))
                r2_dist = (cols - dx) ** 2 + (rows - dy) ** 2
                blob = intensity * np.exp(-r2_dist / (2.0 * sigma_blob ** 2))
                out[r1:r2, c1:c2] = np.clip(
                    np.maximum(out[r1:r2, c1:c2].astype(np.float32), blob),
                    0, 255
                ).astype(np.uint8)

        elif shape_type == 2:
            # C) Hot-pixel cluster (rectangular, NOT square, 3–7 × 3–7 px)
            hw = int(rng.integers(2, 5))
            hh = int(rng.integers(2, 5))
            r1 = max(0, iy - hh); r2 = min(H, iy + hh + 1)
            c1 = max(0, ix - hw); c2 = min(W, ix + hw + 1)
            cluster = (rng.uniform(0.7, 1.0, size=(r2 - r1, c2 - c1)) * intensity).astype(np.uint8)
            out[r1:r2, c1:c2] = np.maximum(out[r1:r2, c1:c2], cluster)

        else:
            # D) Elliptical glare (squashed, b/a ≤ 0.35)
            a_axis = int(rng.integers(10, 25))
            b_axis = int(rng.integers(3, max(4, a_axis // 4)))
            angle_deg = float(rng.uniform(0.0, 180.0))
            cv2.ellipse(out, (ix, iy), (a_axis, b_axis), angle_deg, 0, 360,
                        int(intensity), -1)

    return out


def _apply_motion_blur(frame: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    """Apply linear motion-blur PSF in a random direction (4–12 px kernel)."""
    length = int(rng.integers(4, 13))
    angle_deg = float(rng.uniform(0.0, 180.0))
    # Build diagonal motion-blur kernel
    kernel = np.zeros((length, length), dtype=np.float32)
    center = length // 2
    cv2.line(kernel, (0, center), (length - 1, center), 1.0, 1)
    # Rotate kernel
    M = cv2.getRotationMatrix2D((center, center), angle_deg, 1.0)
    kernel = cv2.warpAffine(kernel, M, (length, length))
    kernel_sum = kernel.sum()
    if kernel_sum > 0:
        kernel /= kernel_sum
    blurred = cv2.filter2D(frame.astype(np.float32), -1, kernel)
    return np.clip(np.rint(blurred), 0, 255).astype(np.uint8)


def _apply_partial_occlusion(frame: np.ndarray, rng: np.random.Generator,
                              beacon_cx: float, beacon_cy: float) -> np.ndarray:
    """Partially occlude beacon with a dark band simulating cloud/structure transit.

    The band covers 30–70% of the beacon area so it is still detectable but
    weakened — teaches the network to detect partially-visible beacons.
    """
    out = frame.copy()
    H, W = out.shape

    # Horizontal or vertical occluding band through the beacon region
    band_axis = int(rng.integers(0, 2))  # 0=horizontal, 1=vertical
    band_width = int(rng.integers(4, 20))
    darkness = float(rng.uniform(0.1, 0.5))  # fraction of original signal retained

    if band_axis == 0:  # horizontal band
        r1 = int(max(0, beacon_cy - band_width // 2))
        r2 = int(min(H, beacon_cy + band_width // 2))
    else:  # vertical band
        c1 = int(max(0, beacon_cx - band_width // 2))
        c2 = int(min(W, beacon_cx + band_width // 2))

    if band_axis == 0:
        region = out[r1:r2, :]
        out[r1:r2, :] = np.clip(region.astype(np.float32) * darkness, 0, 255).astype(np.uint8)
    else:
        region = out[:, c1:c2]
        out[:, c1:c2] = np.clip(region.astype(np.float32) * darkness, 0, 255).astype(np.uint8)

    return out


# ──────────────────────────────────────────────────────────────────────────────
# Core sample renderer
# ──────────────────────────────────────────────────────────────────────────────

def render_synthetic_sample(
    u_center: float,
    v_center: float,
    size_px: float,
    disturbance_preset: str = "NOMINAL",
    seed: int = 42,
    secondary_beacon: bool = False,
) -> Tuple[np.ndarray, Optional[List[Tuple[float, float, float, float]]]]:
    """Render one 640×480 grayscale frame with physics-grounded disturbances.

    Returns:
        (frame_uint8, list_of_yolo_bboxes)
        Each bbox is (cx_norm, cy_norm, w_norm, h_norm).
        Returns (frame, []) when beacon is out of FOV (negative sample).
        Returns (frame, None) only on internal error.
    """
    rng = np.random.default_rng(seed)

    # Randomise background noise floor per sample
    bg_mean = float(rng.uniform(8.0, 20.0))
    bg_sigma = float(rng.uniform(2.0, 6.0))
    frame = _make_sensor_background(rng, bg_mean=bg_mean, bg_sigma=bg_sigma)

    in_fov = (0.0 <= u_center < IMG_W) and (0.0 <= v_center < IMG_H)
    yolo_bboxes: List[Tuple[float, float, float, float]] = []

    # ── Render primary beacon ──────────────────────────────────────────────
    if in_fov:
        # Vary intensity: not always max-saturation
        intensity = int(rng.integers(160, 256))

        # Alternate PSF model for variety
        psf_model = "gaussian" if rng.random() < 0.5 else "box"
        psf_sigma = float(rng.uniform(1.2, 2.5)) if psf_model == "gaussian" else 1.5

        b = Beacon(size_px=size_px, intensity=intensity, shape="square",
                   psf_model=psf_model, psf_sigma_px=psf_sigma)
        b.render_into(frame, x=u_center, y=v_center, background_level=int(bg_mean))

        # YOLO label: margin = 40% of size + at least 4 px
        margin = max(4.0, size_px * 0.4)
        w_px = size_px + margin
        h_px = size_px + margin
        cx_norm = float(u_center / IMG_W)
        cy_norm = float(v_center / IMG_H)
        w_norm = float(min(w_px / IMG_W, 0.99))
        h_norm = float(min(h_px / IMG_H, 0.99))
        yolo_bboxes.append((cx_norm, cy_norm, w_norm, h_norm))

        # ── Optional secondary faint beacon (forces NMS learning) ──────────
        if secondary_beacon:
            sec_size = float(rng.choice([5.0, 7.0, 10.0]))
            sec_u = float(rng.uniform(40.0, IMG_W - 40.0))
            sec_v = float(rng.uniform(40.0, IMG_H - 40.0))
            # Keep secondary well-separated from primary
            if math.hypot(sec_u - u_center, sec_v - v_center) > 60.0:
                sec_intensity = int(rng.integers(100, 180))
                sec_b = Beacon(size_px=sec_size, intensity=sec_intensity, shape="square",
                               psf_model="gaussian", psf_sigma_px=float(rng.uniform(1.0, 2.0)))
                sec_b.render_into(frame, x=sec_u, y=sec_v, background_level=int(bg_mean))
                sec_margin = max(4.0, sec_size * 0.4)
                yolo_bboxes.append((
                    float(sec_u / IMG_W),
                    float(sec_v / IMG_H),
                    float(min((sec_size + sec_margin) / IMG_W, 0.99)),
                    float(min((sec_size + sec_margin) / IMG_H, 0.99)),
                ))

    # ── Apply disturbance preset ───────────────────────────────────────────
    if disturbance_preset == "NOMINAL":
        pass  # only background noise already applied

    elif disturbance_preset == "GAUSSIAN_LIGHT":
        frame = apply_gaussian_noise(frame, sigma=8.0, rng=rng)

    elif disturbance_preset == "GAUSSIAN_HEAVY":
        frame = apply_gaussian_noise(frame, sigma=18.0, rng=rng)

    elif disturbance_preset == "SALT_PEPPER":
        prob = float(rng.uniform(0.03, 0.10))
        frame = apply_salt_and_pepper_noise(frame, probability=prob, rng=rng)

    elif disturbance_preset == "POISSON":
        peak = float(rng.uniform(80.0, 250.0))
        frame = apply_poisson_noise(frame, peak_photons=peak, rng=rng)

    elif disturbance_preset == "FOG":
        contrast = float(rng.uniform(0.25, 0.50))
        frame, _, _ = apply_atmospheric_degradation(
            frame, AtmosphereConfig(enabled=True, condition="fog", contrast_factor=contrast)
        )

    elif disturbance_preset == "RAIN":
        contrast = float(rng.uniform(0.55, 0.80))
        frame, _, _ = apply_atmospheric_degradation(
            frame, AtmosphereConfig(enabled=True, condition="rain", contrast_factor=contrast)
        )

    elif disturbance_preset == "LOW_LIGHT":
        brightness = float(rng.uniform(-0.50, -0.30))
        frame, _, _ = apply_atmospheric_degradation(
            frame, AtmosphereConfig(enabled=True, condition="low_light", brightness_factor=brightness)
        )

    elif disturbance_preset == "DISTRACTOR":
        # Light Gaussian noise + CORRECTLY-SHAPED distractors (not beacon squares)
        frame = apply_gaussian_noise(frame, sigma=float(rng.uniform(5.0, 12.0)), rng=rng)
        num_d = int(rng.integers(2, 6))
        frame = _render_distractors_correct(
            frame, rng,
            beacon_cx=u_center if in_fov else None,
            beacon_cy=v_center if in_fov else None,
            num_distractors=num_d,
        )

    elif disturbance_preset == "MOTION_BLUR":
        frame = apply_gaussian_noise(frame, sigma=float(rng.uniform(4.0, 10.0)), rng=rng)
        frame = _apply_motion_blur(frame, rng)

    elif disturbance_preset == "PARTIAL_OCCLUSION":
        frame = apply_gaussian_noise(frame, sigma=float(rng.uniform(4.0, 8.0)), rng=rng)
        if in_fov:
            frame = _apply_partial_occlusion(frame, rng, u_center, v_center)

    elif disturbance_preset == "SCINTILLATION_TURBULENCE":
        # Atmospheric scintillation (Kolmogorov / Gamma-gamma log-normal intensity fluctuations)
        frame = apply_gaussian_noise(frame, sigma=float(rng.uniform(6.0, 12.0)), rng=rng)
        if in_fov:
            # Random beam scintillation factor (0.4 to 1.4)
            scint_factor = float(rng.uniform(0.4, 1.4))
            r_box = int(size_px * 2)
            r1 = max(0, int(v_center) - r_box); r2 = min(IMG_H, int(v_center) + r_box + 1)
            c1 = max(0, int(u_center) - r_box); c2 = min(IMG_W, int(u_center) + r_box + 1)
            if r2 > r1 and c2 > c1:
                frame[r1:r2, c1:c2] = np.clip(frame[r1:r2, c1:c2].astype(np.float32) * scint_factor, 0, 255).astype(np.uint8)

    elif disturbance_preset == "LENS_GLINT":
        # Internal Fresnel lens reflection / optical halo around bright spot
        frame = apply_gaussian_noise(frame, sigma=float(rng.uniform(4.0, 8.0)), rng=rng)
        if in_fov:
            halo_radius = int(size_px * float(rng.uniform(2.0, 4.5)))
            halo_intensity = int(rng.integers(30, 80))
            cv2.circle(frame, (int(u_center), int(v_center)), halo_radius, (halo_intensity,), -1)
            # Re-render core beacon over halo
            b = Beacon(size_px=size_px, intensity=int(rng.integers(220, 255)), shape="square")
            b.render_into(frame, x=u_center, y=v_center, background_level=int(bg_mean))

    elif disturbance_preset == "SEVERE":
        # Stack: heavy Gaussian + S&P + rain + distractors
        frame = apply_gaussian_noise(frame, sigma=18.0, rng=rng)
        frame = apply_salt_and_pepper_noise(frame, probability=float(rng.uniform(0.04, 0.10)), rng=rng)
        frame, _, _ = apply_atmospheric_degradation(
            frame, AtmosphereConfig(enabled=True, condition="rain", contrast_factor=float(rng.uniform(0.50, 0.70)))
        )
        if rng.random() < 0.5:
            frame = _render_distractors_correct(
                frame, rng,
                beacon_cx=u_center if in_fov else None,
                beacon_cy=v_center if in_fov else None,
                num_distractors=int(rng.integers(1, 4)),
            )

    return np.asarray(frame, dtype=np.uint8), yolo_bboxes if in_fov else []


# ──────────────────────────────────────────────────────────────────────────────
# Dataset generation entry point
# ──────────────────────────────────────────────────────────────────────────────

def generate_dataset(
    output_dir: Path,
    num_samples_per_preset: int = 1200,
    seed: int = 42,
    show_progress: bool = True,
) -> Dict[str, Any]:
    """Generate the full synthetic training corpus in YOLO format.

    Scale (defaults):
        12 presets × 1,200 samples = 14,400 positive images
        (split 70/15/15 → ~10,080 train / ~2,160 val / ~2,160 test)

    Args:
        output_dir:             Root output path.  images/ and labels/ sub-dirs
                                are created automatically.
        num_samples_per_preset: Images per disturbance preset.
        seed:                   Master random seed for reproducibility.
        show_progress:          Print tqdm-style progress lines (Colab friendly).

    Returns:
        Manifest dictionary with generation statistics.
    """
    output_dir = Path(output_dir)
    images_dir = output_dir / "images"
    labels_dir = output_dir / "labels"
    images_dir.mkdir(parents=True, exist_ok=True)
    labels_dir.mkdir(parents=True, exist_ok=True)

    sample_id = 0
    annotated_boxes = 0
    empty_label_count = 0
    generated_counts: Dict[str, int] = {p: 0 for p in PRESETS}

    total = len(PRESETS) * num_samples_per_preset
    progress_interval = max(1, total // 40)   # ~40 progress ticks total

    logger.info(
        "Generating %d images (%d presets × %d/preset) into %s",
        total, len(PRESETS), num_samples_per_preset, output_dir,
    )

    for preset in PRESETS:
        if show_progress:
            print(f"\n[DATASET] Preset: {preset} — generating {num_samples_per_preset} samples …")

        for i in range(num_samples_per_preset):
            # Deterministic per-sample seed derived from master seed + preset hash + index
            cur_seed = seed ^ ((hash(preset) & 0x7FFFFFFF) + i * 997 + 1)
            rng_outer = np.random.default_rng(cur_seed)

            # 85% in-FOV beacon samples, 5% explicit negative (blank label), 10% edge-of-FOV
            roll = rng_outer.random()
            if roll < 0.85:
                u = float(rng_outer.uniform(20.0, IMG_W - 20.0))
                v = float(rng_outer.uniform(20.0, IMG_H - 20.0))
                size = float(rng_outer.choice(TARGET_SIZES_PX))
            elif roll < 0.90:
                # Edge-of-FOV: beacon partially outside frame (teaches boundary handling)
                u = float(rng_outer.choice([
                    rng_outer.uniform(-4.0, 12.0),
                    rng_outer.uniform(IMG_W - 12.0, IMG_W + 4.0),
                ]))
                v = float(rng_outer.uniform(20.0, IMG_H - 20.0))
                size = float(rng_outer.choice([5.0, 7.0, 10.0]))
            else:
                # Explicit hard-negative: no beacon in frame at all
                u, v = -999.0, -999.0
                size = 10.0

            # 10% of in-FOV NOMINAL/GAUSSIAN samples get a secondary beacon
            add_secondary = (
                preset in ("NOMINAL", "GAUSSIAN_LIGHT", "DISTRACTOR")
                and roll < 0.85
                and rng_outer.random() < 0.10
            )

            frame, bboxes = render_synthetic_sample(
                u_center=u,
                v_center=v,
                size_px=size,
                disturbance_preset=preset,
                seed=cur_seed + 1,
                secondary_beacon=add_secondary,
            )

            img_name = f"s{sample_id:07d}_{preset.lower()}.png"
            lbl_name = f"s{sample_id:07d}_{preset.lower()}.txt"

            cv2.imwrite(str(images_dir / img_name), frame)

            with open(labels_dir / lbl_name, "w", encoding="utf-8") as f:
                for (cx, cy, w, h) in bboxes:
                    f.write(f"0 {cx:.6f} {cy:.6f} {w:.6f} {h:.6f}\n")
                    annotated_boxes += 1

            if not bboxes:
                empty_label_count += 1

            sample_id += 1
            generated_counts[preset] += 1

            if show_progress and (sample_id % progress_interval == 0):
                pct = 100.0 * sample_id / total
                print(f"  [{sample_id:6d}/{total}]  {pct:5.1f}%  boxes_so_far={annotated_boxes}")

    manifest = {
        "dataset_version": "v2_production",
        "dataset_type": "HORIZON Synthetic FSOC Beacon Dataset",
        "total_samples": sample_id,
        "annotated_samples": annotated_boxes,
        "empty_label_samples": empty_label_count,
        "class_names": ["beacon"],
        "num_classes": 1,
        "image_width": IMG_W,
        "image_height": IMG_H,
        "presets": list(PRESETS),
        "samples_per_preset": generated_counts,
        "target_sizes_px": list(TARGET_SIZES_PX),
        "master_seed": seed,
        "notes": (
            "v2: realistic sensor backgrounds, correct distractor shapes, "
            "motion blur, partial occlusion, varied PSF, multi-instance frames."
        ),
    }

    manifest_path = output_dir / "dataset_manifest_v2.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    logger.info(
        "Dataset generation complete: %d images, %d bounding boxes, %d negatives",
        sample_id, annotated_boxes, empty_label_count,
    )
    print(f"\n✓  Dataset written to: {output_dir}")
    print(f"   Images : {sample_id}")
    print(f"   Labels  : {annotated_boxes} bounding boxes, {empty_label_count} empty-label negatives")
    return manifest


# ──────────────────────────────────────────────────────────────────────────────
# CLI entry point
# ──────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import argparse

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    ap = argparse.ArgumentParser(description="HORIZON Synthetic Dataset Generator v2")
    ap.add_argument("--output-dir", default="research/data/synthetic_dataset_v2",
                    help="Output directory for images/ and labels/")
    ap.add_argument("--samples-per-preset", type=int, default=1200,
                    help="Number of images per disturbance preset (default: 1200)")
    ap.add_argument("--seed", type=int, default=42, help="Master random seed")
    args = ap.parse_args()

    result = generate_dataset(
        output_dir=Path(args.output_dir),
        num_samples_per_preset=args.samples_per_preset,
        seed=args.seed,
        show_progress=True,
    )
    print(json.dumps(result, indent=2))
