"""
HORIZON Research Foundation — Zenodo Dataset Ingestion & Metadata Parser
================================================================================
Ingests, verifies, and records dataset metadata for the reference BSD-3 licensed
Zenodo laser-spot dataset (ADVRHumanoids/nn_laser_spot_tracking).

Strict Invariant: No fabricated statistics. Reports empirical dataset metrics.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
import cv2
import numpy as np

logger = logging.getLogger(__name__)


def ingest_zenodo_dataset(
    data_dir: Path, output_manifest: Path
) -> Dict[str, Any]:
    """Ingest Zenodo laser-spot dataset files, validate images, and generate dataset metadata.

    Args:
        data_dir: Path to directory containing images and annotations.
        output_manifest: Path to save the dataset manifest JSON.

    Returns:
        Dict containing dataset metadata and empirical statistics.
    """
    data_dir = Path(data_dir)
    data_dir.mkdir(parents=True, exist_ok=True)

    image_files = sorted(list(data_dir.glob("*.jpg")) + list(data_dir.glob("*.png")))
    total_images = len(image_files)
    valid_images = 0
    invalid_images = 0
    total_annotations = 0

    dimensions_list: List[Dict[str, int]] = []
    bbox_widths: List[float] = []
    bbox_heights: List[float] = []

    for img_path in image_files:
        img = cv2.imread(str(img_path))
        if img is None:
            invalid_images += 1
            logger.warning("Failed to load image: %s", img_path)
            continue

        h, w = img.shape[:2]
        valid_images += 1
        dimensions_list.append({"width": w, "height": h})

        label_path = img_path.with_suffix(".txt")
        if label_path.exists():
            with open(label_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
                for line in lines:
                    parts = line.strip().split()
                    if len(parts) == 5:
                        total_annotations += 1
                        _, _, _, bw, bh = map(float, parts)
                        bbox_widths.append(bw)
                        bbox_heights.append(bh)

    stats: Dict[str, Any] = {
        "dataset_name": "ADVRHumanoids/nn_laser_spot_tracking (Zenodo)",
        "source": "https://github.com/ADVRHumanoids/nn_laser_spot_tracking",
        "license": "BSD-3-Clause",
        "total_images": total_images,
        "valid_images": valid_images,
        "invalid_images": invalid_images,
        "total_annotations": total_annotations,
        "class_names": ["beacon"],
        "mean_bbox_width_norm": float(np.mean(bbox_widths)) if bbox_widths else 0.0,
        "mean_bbox_height_norm": float(np.mean(bbox_heights)) if bbox_heights else 0.0,
    }

    output_manifest.parent.mkdir(parents=True, exist_ok=True)
    with open(output_manifest, "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2)

    logger.info("Ingested Zenodo dataset: %d images, %d annotations", valid_images, total_annotations)
    return stats


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    target_dir = Path("research/data/zenodo_laser_dataset")
    manifest_file = Path("research/data/zenodo_manifest.json")
    res = ingest_zenodo_dataset(target_dir, manifest_file)
    print(json.dumps(res, indent=2))
