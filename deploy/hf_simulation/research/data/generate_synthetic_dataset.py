"""
HORIZON Synthetic Dataset Generation Pipeline
=====================================================
Generates domain-adapted training dataset from Phase 1–3 simulator
(WORLD -> VIRTUAL CAMERA -> DISTURBANCE ENGINE).

Generates annotated YOLO-format images (640×480 grayscale uint8 + bounding box labels [class_id cx cy w h])
across 8 disturbance configurations (Clean, Gaussian, S&P, Poisson, Fog, Rain, Low Light, Distractors)
and 4 target size classes (5×5, 10×10, 15×15, 20×20) with subpixel offsets.

Strict Invariant: Ground-truth bounding boxes are generated directly from simulator state.
"""

from __future__ import annotations

import json
import logging
import math
from pathlib import Path
import sys
from typing import Dict, Any, List, Tuple
import cv2
import numpy as np

project_root = Path(__file__).resolve().parents[2]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from simulator.core.seed_manager import SeedManager
from simulator.disturbances.atmosphere import apply_atmospheric_degradation
from simulator.disturbances.config import AtmosphereConfig
from simulator.disturbances.noise import (
    apply_gaussian_noise,
    apply_poisson_noise,
    apply_salt_and_pepper_noise,
)
from simulator.world.beacon import Beacon

logger = logging.getLogger(__name__)


def render_synthetic_sample(
    u_center: float,
    v_center: float,
    size_px: float,
    disturbance_preset: str = "NOMINAL",
    seed: int = 42,
    img_width: int = 640,
    img_height: int = 480,
) -> Tuple[np.ndarray, Optional[Tuple[float, float, float, float]]]:
    """Render a single synthetic camera frame with disturbance and derive exact YOLO bbox [cx, cy, w, h]."""
    rng = np.random.default_rng(seed)
    frame = np.zeros((img_height, img_width), dtype=np.uint8)

    # 1. Check if beacon is inside or touching the observation window
    in_fov = (0.0 <= u_center < img_width) and (0.0 <= v_center < img_height)

    bbox_yolo: Optional[Tuple[float, float, float, float]] = None

    if in_fov:
        b = Beacon(size_px=size_px, intensity=255, shape="square")
        b.render_into(frame, x=u_center, y=v_center, background_level=0)

        # Derive normalized YOLO bounding box [cx, cy, w, h] from true beacon dimensions
        # Bounding box width & height in normalized units with small margin
        margin = max(4.0, size_px * 0.4)
        w_px = min(img_width, size_px + margin)
        h_px = min(img_height, size_px + margin)

        cx_norm = float(u_center / img_width)
        cy_norm = float(v_center / img_height)
        w_norm = float(w_px / img_width)
        h_norm = float(h_px / img_height)

        bbox_yolo = (cx_norm, cy_norm, w_norm, h_norm)

    # 2. Apply Phase 3 Disturbances according to preset
    if disturbance_preset == "GAUSSIAN":
        frame = apply_gaussian_noise(frame, sigma=15.0, rng=rng)
    elif disturbance_preset == "SALT_PEPPER":
        frame = apply_salt_and_pepper_noise(frame, probability=0.05, rng=rng)
    elif disturbance_preset == "POISSON":
        frame = apply_poisson_noise(frame, peak_photons=200.0, rng=rng)
    elif disturbance_preset == "FOG":
        frame, _, _ = apply_atmospheric_degradation(
            frame, AtmosphereConfig(enabled=True, condition="fog", contrast_factor=0.35)
        )
    elif disturbance_preset == "RAIN":
        frame, _, _ = apply_atmospheric_degradation(
            frame, AtmosphereConfig(enabled=True, condition="rain", contrast_factor=0.70)
        )
    elif disturbance_preset == "LOW_LIGHT":
        frame, _, _ = apply_atmospheric_degradation(
            frame, AtmosphereConfig(enabled=True, condition="low_light", brightness_factor=-0.40)
        )
    elif disturbance_preset == "DISTRACTOR":
        # Add random non-beacon distractor noise spots
        frame = apply_gaussian_noise(frame, sigma=10.0, rng=rng)
        num_distractors = rng.integers(1, 4)
        for _ in range(num_distractors):
            dx = float(rng.uniform(20.0, img_width - 20.0))
            dy = float(rng.uniform(20.0, img_height - 20.0))
            if not in_fov or math.hypot(dx - u_center, dy - v_center) > 50.0:
                dist_size = float(rng.uniform(5.0, 8.0))
                dist_b = Beacon(size_px=dist_size, intensity=int(rng.integers(120, 200)), shape="square")
                dist_b.render_into(frame, x=dx, y=dy, background_level=0)
    elif disturbance_preset == "SEVERE":
        frame = apply_gaussian_noise(frame, sigma=20.0, rng=rng)
        frame = apply_salt_and_pepper_noise(frame, probability=0.08, rng=rng)
        frame, _, _ = apply_atmospheric_degradation(
            frame, AtmosphereConfig(enabled=True, condition="rain", contrast_factor=0.60)
        )

    return np.asarray(frame, dtype=np.uint8), bbox_yolo


def generate_dataset(
    output_dir: Path,
    num_samples_per_preset: int = 150,
    seed: int = 42,
) -> Dict[str, Any]:
    """Generate complete synthetic training dataset in YOLO format."""
    output_dir = Path(output_dir)
    images_dir = output_dir / "images"
    labels_dir = output_dir / "labels"
    images_dir.mkdir(parents=True, exist_ok=True)
    labels_dir.mkdir(parents=True, exist_ok=True)

    presets = [
        "NOMINAL",
        "GAUSSIAN",
        "SALT_PEPPER",
        "POISSON",
        "FOG",
        "RAIN",
        "LOW_LIGHT",
        "DISTRACTOR",
        "SEVERE",
    ]
    target_sizes = [5.0, 10.0, 15.0, 20.0]

    sample_id = 0
    generated_counts: Dict[str, int] = {p: 0 for p in presets}
    annotated_boxes = 0

    seed_mgr = SeedManager(seed=seed)

    for preset in presets:
        for i in range(num_samples_per_preset):
            cur_seed = seed + (hash(preset) & 0xFFFF) + i
            rng = np.random.default_rng(cur_seed)

            # 90% in-FOV samples, 10% out-of-FOV samples
            in_fov = rng.random() < 0.90
            if in_fov:
                u = rng.uniform(30.0, 610.0)
                v = rng.uniform(30.0, 450.0)
                size = float(rng.choice(target_sizes))
            else:
                u = float(rng.choice([-50.0, 700.0]))
                v = float(rng.choice([-50.0, 520.0]))
                size = 10.0

            frame, bbox = render_synthetic_sample(
                u_center=u,
                v_center=v,
                size_px=size,
                disturbance_preset=preset,
                seed=cur_seed,
            )

            img_name = f"frame_{sample_id:06d}_{preset.lower()}.png"
            label_name = f"frame_{sample_id:06d}_{preset.lower()}.txt"

            cv2.imwrite(str(images_dir / img_name), frame)

            label_path = labels_dir / label_name
            with open(label_path, "w", encoding="utf-8") as f:
                if bbox is not None:
                    cx, cy, w, h = bbox
                    f.write(f"0 {cx:.6f} {cy:.6f} {w:.6f} {h:.6f}\n")
                    annotated_boxes += 1

            sample_id += 1
            generated_counts[preset] += 1

    manifest = {
        "dataset_type": "Synthetic Scenario Engine Dataset",
        "total_samples": sample_id,
        "annotated_samples": annotated_boxes,
        "class_names": ["beacon"],
        "num_classes": 1,
        "samples_per_preset": generated_counts,
        "image_width": 640,
        "image_height": 480,
    }

    with open(output_dir / "dataset_manifest.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    logger.info("Generated %d synthetic images (%d annotated) in %s", sample_id, annotated_boxes, output_dir)
    return manifest


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    out_path = Path("research/data/synthetic_dataset")
    res = generate_dataset(out_path, num_samples_per_preset=100, seed=42)
    print(json.dumps(res, indent=2))
