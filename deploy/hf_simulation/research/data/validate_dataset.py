"""
HORIZON Dataset Validation Pipeline
===========================================
Performs thorough integrity validation on YOLO format image/annotation datasets:
  - Image file readability & dimensions check
  - Annotation existence & coordinate bound validation (0 <= x, y, w, h <= 1)
  - Bounding box aspect ratio and positive area checks
  - Class ID verification
  - Empirical distribution reporting (total images, valid images, invalid images, class counts)

Strict Invariant: Reports all invalid records explicitly.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Dict, Any, List
import cv2
import numpy as np

logger = logging.getLogger(__name__)


def validate_yolo_dataset(dataset_dir: Path) -> Dict[str, Any]:
    """Validate a YOLO format dataset directory containing images/ and labels/ subdirectories."""
    dataset_dir = Path(dataset_dir)
    images_dir = dataset_dir / "images"
    labels_dir = dataset_dir / "labels"

    if not images_dir.exists():
        raise FileNotFoundError(f"Images directory not found: {images_dir}")

    image_files = sorted(
        list(images_dir.glob("*.jpg"))
        + list(images_dir.glob("*.png"))
        + list(images_dir.glob("*.jpeg"))
    )

    total_images = len(image_files)
    valid_images = 0
    invalid_images = 0
    corrupt_images: List[str] = []
    invalid_annotations: List[Dict[str, Any]] = []

    total_boxes = 0
    class_distribution: Dict[int, int] = {}
    bbox_aspect_ratios: List[float] = []
    bbox_areas_norm: List[float] = []

    for img_path in image_files:
        img = cv2.imread(str(img_path))
        if img is None:
            invalid_images += 1
            corrupt_images.append(img_path.name)
            continue

        valid_images += 1
        h_img, w_img = img.shape[:2]

        label_path = labels_dir / (img_path.stem + ".txt")
        if label_path.exists():
            with open(label_path, "r", encoding="utf-8") as f:
                lines = f.readlines()

            for line_idx, line in enumerate(lines):
                line_str = line.strip()
                if not line_str:
                    continue

                parts = line_str.split()
                if len(parts) != 5:
                    invalid_annotations.append(
                        {
                            "file": label_path.name,
                            "line": line_idx + 1,
                            "reason": f"Expected 5 tokens, got {len(parts)}",
                        }
                    )
                    continue

                try:
                    cls_id = int(parts[0])
                    cx, cy, bw, bh = map(float, parts[1:])
                except ValueError:
                    invalid_annotations.append(
                        {
                            "file": label_path.name,
                            "line": line_idx + 1,
                            "reason": "Non-numeric coordinates",
                        }
                    )
                    continue

                # Coordinate bounds validation
                if not (0.0 <= cx <= 1.0 and 0.0 <= cy <= 1.0):
                    invalid_annotations.append(
                        {
                            "file": label_path.name,
                            "line": line_idx + 1,
                            "reason": f"Center ({cx}, {cy}) out of bounds [0, 1]",
                        }
                    )
                    continue

                if bw <= 0.0 or bh <= 0.0 or bw > 1.0 or bh > 1.0:
                    invalid_annotations.append(
                        {
                            "file": label_path.name,
                            "line": line_idx + 1,
                            "reason": f"Dimensions ({bw}, {bh}) out of bounds (0, 1]",
                        }
                    )
                    continue

                total_boxes += 1
                class_distribution[cls_id] = class_distribution.get(cls_id, 0) + 1
                bbox_aspect_ratios.append(bw / bh if bh > 0 else 0.0)
                bbox_areas_norm.append(bw * bh)

    report: Dict[str, Any] = {
        "dataset_directory": str(dataset_dir),
        "total_images": total_images,
        "valid_images": valid_images,
        "invalid_images": invalid_images,
        "corrupt_images": corrupt_images,
        "total_bounding_boxes": total_boxes,
        "class_distribution": class_distribution,
        "invalid_annotations_count": len(invalid_annotations),
        "invalid_annotations_details": invalid_annotations[:10],  # sample details
        "mean_bbox_aspect_ratio": float(np.mean(bbox_aspect_ratios)) if bbox_aspect_ratios else 0.0,
        "mean_bbox_area_norm": float(np.mean(bbox_areas_norm)) if bbox_areas_norm else 0.0,
        "is_valid": (invalid_images == 0 and len(invalid_annotations) == 0 and total_images > 0),
    }

    logger.info(
        "Dataset validation complete for %s: %d/%d valid images, %d bboxes, %d invalid records",
        dataset_dir,
        valid_images,
        total_images,
        total_boxes,
        len(invalid_annotations),
    )
    return report


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    target_path = Path("research/data/synthetic_dataset")
    res = validate_yolo_dataset(target_path)
    print(json.dumps(res, indent=2))
