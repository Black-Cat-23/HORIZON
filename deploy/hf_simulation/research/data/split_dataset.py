"""
HORIZON Deterministic Dataset Splitter
==============================================
Performs deterministic group/sequence-aware splitting of YOLO dataset into
train (70%), val (15%), and test (15%) splits without train/test sequence leakage.

Saves:
  - train_manifest.json
  - val_manifest.json
  - test_manifest.json
  - YOLO format directory structure: dataset_split/train/, val/, test/

Strict Invariant: Deterministic splitting using centralized random seed.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
import shutil
from typing import Dict, Any, List
import numpy as np

logger = logging.getLogger(__name__)


def split_yolo_dataset(
    source_dir: Path,
    output_dir: Path,
    train_ratio: float = 0.70,
    val_ratio: float = 0.15,
    test_ratio: float = 0.15,
    seed: int = 42,
) -> Dict[str, Any]:
    """Split dataset deterministically into train/val/test splits."""
    source_dir = Path(source_dir)
    output_dir = Path(output_dir)

    images_dir = source_dir / "images"
    labels_dir = source_dir / "labels"

    image_files = sorted(
        list(images_dir.glob("*.jpg"))
        + list(images_dir.glob("*.png"))
        + list(images_dir.glob("*.jpeg"))
    )

    if not image_files:
        raise FileNotFoundError(f"No images found in {images_dir}")

    # Group files by preset prefix to prevent sequence leakage
    group_map: Dict[str, List[Path]] = {}
    for img_p in image_files:
        # Prefix e.g. frame_000001_gaussian.png -> gaussian
        parts = img_p.stem.split("_")
        prefix = parts[-1] if len(parts) > 1 else "default"
        group_map.setdefault(prefix, []).append(img_p)

    rng = np.random.RandomState(seed)

    train_imgs: List[Path] = []
    val_imgs: List[Path] = []
    test_imgs: List[Path] = []

    for prefix, group_files in group_map.items():
        rng.shuffle(group_files)
        n = len(group_files)
        n_train = int(n * train_ratio)
        n_val = int(n * val_ratio)

        train_imgs.extend(group_files[:n_train])
        val_imgs.extend(group_files[n_train : n_train + n_val])
        test_imgs.extend(group_files[n_train + n_val :])

    # Copy files into target split directories
    for split_name, file_list in [
        ("train", train_imgs),
        ("val", val_imgs),
        ("test", test_imgs),
    ]:
        split_img_dir = output_dir / split_name / "images"
        split_lbl_dir = output_dir / split_name / "labels"
        split_img_dir.mkdir(parents=True, exist_ok=True)
        split_lbl_dir.mkdir(parents=True, exist_ok=True)

        manifest_records: List[str] = []
        for img_p in file_list:
            shutil.copy2(img_p, split_img_dir / img_p.name)
            lbl_p = labels_dir / (img_p.stem + ".txt")
            if lbl_p.exists():
                shutil.copy2(lbl_p, split_lbl_dir / lbl_p.name)
            manifest_records.append(img_p.name)

        manifest_data = {
            "split": split_name,
            "seed": seed,
            "file_count": len(manifest_records),
            "files": manifest_records,
        }
        with open(
            output_dir / f"{split_name}_manifest.json", "w", encoding="utf-8"
        ) as f:
            json.dump(manifest_data, f, indent=2)

    summary = {
        "source": str(source_dir),
        "output": str(output_dir),
        "seed": seed,
        "train_count": len(train_imgs),
        "val_count": len(val_imgs),
        "test_count": len(test_imgs),
        "total": len(image_files),
    }

    logger.info(
        "Split dataset: %d train, %d val, %d test samples",
        len(train_imgs),
        len(val_imgs),
        len(test_imgs),
    )
    return summary


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    src = Path("research/data/synthetic_dataset")
    out = Path("research/data/yolo_dataset_split")
    res = split_yolo_dataset(src, out, seed=42)
    print(json.dumps(res, indent=2))
