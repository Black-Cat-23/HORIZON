"""
HORIZON Hard-Negative Mining Pipeline
=============================================
Mines difficult false positive noise clusters, Salt & Pepper spikes, and distractor
bright artifacts to generate dedicated hard-negative training samples.

Hard-negative samples consist of:
  - 640×480 grayscale frames containing heavy noise or distractor artifacts
  - Empty YOLO label text files (0 bounding boxes)

This explicitly teaches YOLOv8n to suppress false locks on bright noise spikes.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
import sys
from typing import Dict, Any, List
import cv2
import numpy as np

project_root = Path(__file__).resolve().parents[2]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from simulator.disturbances.atmosphere import apply_atmospheric_degradation
from simulator.disturbances.config import AtmosphereConfig
from simulator.disturbances.noise import (
    apply_gaussian_noise,
    apply_salt_and_pepper_noise,
)
from simulator.world.beacon import Beacon

logger = logging.getLogger(__name__)


def generate_hard_negatives(
    output_dir: Path, num_samples: int = 150, seed: int = 123
) -> Dict[str, Any]:
    """Generate hard-negative training samples (noise/distractor frames with zero beacon targets)."""
    output_dir = Path(output_dir)
    images_dir = output_dir / "images"
    labels_dir = output_dir / "labels"
    images_dir.mkdir(parents=True, exist_ok=True)
    labels_dir.mkdir(parents=True, exist_ok=True)

    rng = np.random.default_rng(seed)
    negative_records: List[Dict[str, Any]] = []

    for i in range(num_samples):
        frame = np.zeros((480, 640), dtype=np.uint8)
        neg_type = rng.choice(["sp_cluster", "gaussian_spike", "reflection_spot", "severe_fog"])

        if neg_type == "sp_cluster":
            frame = apply_salt_and_pepper_noise(frame, probability=0.12, rng=rng)
        elif neg_type == "gaussian_spike":
            frame = apply_gaussian_noise(frame, sigma=20.0, rng=rng)
        elif neg_type == "reflection_spot":
            # Synthesize bright non-beacon glare/reflection spot
            frame = apply_gaussian_noise(frame, sigma=8.0, rng=rng)
            rx = float(rng.uniform(50.0, 590.0))
            ry = float(rng.uniform(50.0, 430.0))
            glare = Beacon(size_px=float(rng.uniform(12.0, 20.0)), intensity=int(rng.integers(180, 240)), shape="square")
            glare.render_into(frame, x=rx, y=ry, background_level=0)
        elif neg_type == "severe_fog":
            frame = apply_gaussian_noise(frame, sigma=12.0, rng=rng)
            frame, _, _ = apply_atmospheric_degradation(
                frame, AtmosphereConfig(enabled=True, condition="fog", contrast_factor=0.35)
            )

        img_name = f"hard_neg_{i:05d}_{neg_type}.png"
        lbl_name = f"hard_neg_{i:05d}_{neg_type}.txt"

        cv2.imwrite(str(images_dir / img_name), frame)
        # Create empty label file indicating zero valid beacon targets
        with open(labels_dir / lbl_name, "w", encoding="utf-8") as f:
            pass

        negative_records.append({"file": img_name, "type": neg_type})

    summary = {
        "hard_negatives_generated": num_samples,
        "directory": str(output_dir),
        "seed": seed,
        "sample_records": negative_records[:5],
    }

    with open(output_dir / "hard_negative_manifest.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    logger.info("Generated %d hard-negative samples in %s", num_samples, output_dir)
    return summary


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    out_dir = Path("research/data/hard_negatives")
    res = generate_hard_negatives(out_dir, num_samples=100, seed=123)
    print(json.dumps(res, indent=2))
