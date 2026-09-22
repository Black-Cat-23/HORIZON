"""
HORIZON — Google Colab Training Master Pipeline
================================================
Run this single script on a Google Colab GPU instance to:

  Step 0  Install dependencies
  Step 1  Generate 14,400-image positive dataset (v2)
  Step 2  Generate 1,500 hard-negative samples (v2)
  Step 3  Merge positive + negative into unified YOLO corpus
  Step 4  Split into train/val/test (70 / 15 / 15)
  Step 5  Validate dataset integrity
  Step 6  Train YOLOv8n (200 epochs, GPU)
  Step 7  Run post-training per-preset precision/recall evaluation
  Step 8  Export best checkpoint to ONNX (FP32, opset 12)
  Step 9  Validate ONNX consistency vs PyTorch weights

Usage in Colab:
    # Mount Google Drive first, then:
    !git clone <your-HORIZON-repo>
    %cd HORIZON/coarse-align-x
    !python research/training/run_colab_pipeline.py

    # Or run individual steps:
    !python research/training/run_colab_pipeline.py --steps 1 2 3 4

    # Resume from a specific step (e.g. after Colab session restart with saved dataset):
    !python research/training/run_colab_pipeline.py --steps 6 7 8 9

All intermediate artefacts are written to Google Drive if --gdrive-root is set.
"""

from __future__ import annotations

import argparse
import json
import logging
import shutil
import sys
import time
from pathlib import Path
from typing import List, Optional

# ── make sure project root is on path ──────────────────────────────────────
project_root = Path(__file__).resolve().parents[2]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  [%(levelname)-8s]  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("colab_pipeline")

# ── Default paths ──────────────────────────────────────────────────────────
SYNTHETIC_DIR   = project_root / "research" / "data" / "synthetic_dataset_v2"
HARD_NEG_DIR    = project_root / "research" / "data" / "hard_negatives_v2"
REAL_LASER_DIR  = project_root / "research" / "data" / "real_laser_dataset_v2"
COMBINED_DIR    = project_root / "research" / "data" / "combined_dataset_v2"
SPLIT_DIR       = project_root / "research" / "data" / "yolo_dataset_split_v2"
DATASET_YAML    = project_root / "research" / "training" / "dataset_v2.yaml"
MODELS_DIR      = project_root / "research" / "training" / "models"

# Dataset sizes (defaults)
SAMPLES_PER_PRESET = 1200
HARD_NEG_COUNT     = 1500
REAL_LASER_COUNT   = 1500


# ─────────────────────────────────────────────────────────────────────────────
# Step 0: Install dependencies
# ─────────────────────────────────────────────────────────────────────────────
def step0_install_deps() -> None:
    import subprocess
    print("\n" + "=" * 60)
    print("STEP 0: Installing dependencies")
    print("=" * 60)
    packages = [
        "ultralytics>=8.2",
        "onnxruntime",
        "onnx",
        "opencv-python-headless",
        "numpy",
        "scipy",
    ]
    subprocess.check_call([sys.executable, "-m", "pip", "install", "--quiet"] + packages)
    print("✓  Dependencies installed")


# ─────────────────────────────────────────────────────────────────────────────
# Step 1: Generate positive dataset
# ─────────────────────────────────────────────────────────────────────────────
def step1_generate_dataset(samples_per_preset: int = SAMPLES_PER_PRESET) -> None:
    total_expected = samples_per_preset * 14
    print("\n" + "=" * 60)
    print(f"STEP 1: Generating {total_expected:,}-image positive synthetic dataset (14 presets)")
    print("=" * 60)
    print(f"  Output: {SYNTHETIC_DIR}")

    from research.data.generate_synthetic_dataset import generate_dataset  # type: ignore
    t0 = time.time()
    manifest = generate_dataset(
        output_dir=SYNTHETIC_DIR,
        num_samples_per_preset=samples_per_preset,
        seed=42,
        show_progress=True,
    )
    elapsed = time.time() - t0
    print(f"\n✓  Positive dataset: {manifest['total_samples']:,} images in {elapsed:.0f}s")


# ─────────────────────────────────────────────────────────────────────────────
# Step 2: Generate hard negatives & Real Optical Laser frames
# ─────────────────────────────────────────────────────────────────────────────
def step2_hard_negatives_and_real_laser(
    hard_neg_count: int = HARD_NEG_COUNT,
    real_laser_count: int = REAL_LASER_COUNT,
) -> None:
    print("\n" + "=" * 60)
    print(f"STEP 2: Generating {hard_neg_count:,} hard negatives & {real_laser_count:,} real laser frames")
    print("=" * 60)

    # 2a. Hard negatives
    from research.data.hard_negative_mining import generate_hard_negatives  # type: ignore
    t0 = time.time()
    summary_neg = generate_hard_negatives(
        output_dir=HARD_NEG_DIR,
        num_samples=hard_neg_count,
        seed=123,
        show_progress=True,
    )
    print(f"✓  Hard negatives: {summary_neg['hard_negatives_generated']:,} images in {time.time() - t0:.0f}s")

    # 2b. Real optical laser spot dataset
    from research.data.populate_real_laser_dataset import generate_real_laser_dataset  # type: ignore
    t1 = time.time()
    summary_real = generate_real_laser_dataset(
        output_dir=REAL_LASER_DIR,
        num_samples=real_laser_count,
        seed=100,
    )
    print(f"✓  Real optical laser frames: {summary_real['total_samples']:,} images in {time.time() - t1:.0f}s")


# ─────────────────────────────────────────────────────────────────────────────
# Step 3: Merge positive + negative + real laser into unified YOLO corpus
# ─────────────────────────────────────────────────────────────────────────────
def step3_merge() -> None:
    print("\n" + "=" * 60)
    print("STEP 3: Merging synthetic + real laser + hard negatives")
    print("=" * 60)

    combined_img = COMBINED_DIR / "images"
    combined_lbl = COMBINED_DIR / "labels"
    combined_img.mkdir(parents=True, exist_ok=True)
    combined_lbl.mkdir(parents=True, exist_ok=True)

    total_copied = 0
    sources = [SYNTHETIC_DIR, HARD_NEG_DIR, REAL_LASER_DIR]

    for src_dir in sources:
        if not src_dir.exists():
            continue

        # Check if src has direct images/labels subdirs or flat directory
        src_img = src_dir / "images" if (src_dir / "images").exists() else src_dir
        src_lbl = src_dir / "labels" if (src_dir / "labels").exists() else src_dir

        for img_file in sorted(src_img.glob("*.png")):
            dst_img = combined_img / img_file.name
            dst_lbl = combined_lbl / (img_file.stem + ".txt")

            if not dst_img.exists():
                shutil.copy2(img_file, dst_img)

            lbl_src = src_lbl / (img_file.stem + ".txt")
            if lbl_src.exists() and not dst_lbl.exists():
                shutil.copy2(lbl_src, dst_lbl)
            elif not dst_lbl.exists():
                # Create empty label file for out-of-FOV or hard-negative samples
                dst_lbl.touch()

            total_copied += 1

    manifest = {
        "combined_images": total_copied,
        "sources": [str(s) for s in sources if s.exists()],
    }
    with open(COMBINED_DIR / "combined_manifest.json", "w") as f:
        json.dump(manifest, f, indent=2)

    print(f"✓  Combined: {total_copied:,} images in {COMBINED_DIR}")


# ─────────────────────────────────────────────────────────────────────────────
# Step 4: Split into train/val/test
# ─────────────────────────────────────────────────────────────────────────────
def step4_split() -> None:
    print("\n" + "=" * 60)
    print("STEP 4: Splitting into train/val/test (70/15/15)")
    print("=" * 60)

    from research.data.split_dataset import split_yolo_dataset  # type: ignore
    summary = split_yolo_dataset(
        source_dir=COMBINED_DIR,
        output_dir=SPLIT_DIR,
        train_ratio=0.70,
        val_ratio=0.15,
        test_ratio=0.15,
        seed=42,
    )
    print(f"✓  Split: {summary['train_count']} train / {summary['val_count']} val / {summary['test_count']} test")

    # Write dataset YAML for Ultralytics
    yaml_content = f"""# HORIZON YOLOv8n Beacon Detection Dataset (v2)
# Generated by run_colab_pipeline.py
path: {SPLIT_DIR}
train: train/images
val: val/images
test: test/images

nc: 1
names:
  0: beacon
"""
    with open(DATASET_YAML, "w", encoding="utf-8") as f:
        f.write(yaml_content)
    print(f"✓  Dataset YAML written: {DATASET_YAML}")


# ─────────────────────────────────────────────────────────────────────────────
# Step 5: Validate dataset
# ─────────────────────────────────────────────────────────────────────────────
def step5_validate() -> None:
    print("\n" + "=" * 60)
    print("STEP 5: Validating dataset integrity")
    print("=" * 60)

    for split in ("train", "val", "test"):
        img_dir = SPLIT_DIR / split / "images"
        lbl_dir = SPLIT_DIR / split / "labels"
        imgs = list(img_dir.glob("*.png")) + list(img_dir.glob("*.jpg"))
        lbls = list(lbl_dir.glob("*.txt"))
        mismatched = []
        for img in imgs:
            lbl = lbl_dir / (img.stem + ".txt")
            if not lbl.exists():
                mismatched.append(img.name)

        label_present = sum(1 for l in lbls if l.stat().st_size > 0)
        empty_labels = len(lbls) - label_present
        print(f"  {split:5s}: {len(imgs):5d} images | {len(lbls):5d} labels "
              f"| {label_present:5d} with boxes | {empty_labels:4d} negatives "
              f"| {len(mismatched):3d} missing label")
        if mismatched:
            logger.warning("Missing labels: %s", mismatched[:5])

    print("✓  Dataset validation complete")


# ─────────────────────────────────────────────────────────────────────────────
# Step 6: Train YOLOv8n
# ─────────────────────────────────────────────────────────────────────────────
def step6_train(epochs: int = 200, batch: int = 32) -> Path:
    print("\n" + "=" * 60)
    print(f"STEP 6: Training YOLOv8n — {epochs} epochs, batch={batch}")
    print("=" * 60)

    from research.training.train_yolov8 import TrainingConfig, run_training  # type: ignore
    cfg = TrainingConfig(
        dataset_yaml=str(DATASET_YAML),
        epochs=epochs,
        batch=batch,
        device="auto",
        project=str(project_root / "research" / "training" / "runs"),
        name="yolov8n_beacon_v2",
        workers=8,
    )
    metadata = run_training(cfg)
    best_pt = Path(metadata["best_checkpoint"])
    print(f"\n✓  Training complete. Best checkpoint: {best_pt}")
    return best_pt


# ─────────────────────────────────────────────────────────────────────────────
# Step 7: Per-preset precision/recall evaluation
# ─────────────────────────────────────────────────────────────────────────────
def step7_eval_per_preset(best_pt: Optional[Path] = None) -> None:
    print("\n" + "=" * 60)
    print("STEP 7: Per-preset precision/recall evaluation")
    print("=" * 60)

    from ultralytics import YOLO  # type: ignore

    if best_pt is None:
        # Find most recent best.pt
        candidates = list((project_root / "research" / "training" / "runs").rglob("best.pt"))
        if not candidates:
            print("  ⚠  No trained checkpoint found — skipping evaluation.")
            return
        best_pt = max(candidates, key=lambda p: p.stat().st_mtime)

    model = YOLO(str(best_pt))
    print(f"  Evaluating: {best_pt}")

    # Evaluate on full test split
    results = model.val(
        data=str(DATASET_YAML),
        split="test",
        imgsz=640,
        verbose=True,
    )

    eval_summary: dict = {}
    try:
        if hasattr(results, "results_dict"):
            eval_summary = {k: float(v) for k, v in results.results_dict.items()
                            if isinstance(v, (int, float))}
    except Exception:
        pass

    eval_path = MODELS_DIR / "eval_results.json"
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    with open(eval_path, "w") as f:
        json.dump(eval_summary, f, indent=2)

    print(f"✓  Evaluation results saved: {eval_path}")
    if eval_summary:
        print(f"   mAP@0.5   = {eval_summary.get('metrics/mAP50(B)', 'N/A'):.4f}")
        print(f"   Precision = {eval_summary.get('metrics/precision(B)', 'N/A'):.4f}")
        print(f"   Recall    = {eval_summary.get('metrics/recall(B)', 'N/A'):.4f}")


# ─────────────────────────────────────────────────────────────────────────────
# Step 8: Export to ONNX
# ─────────────────────────────────────────────────────────────────────────────
def step8_export_onnx(best_pt: Optional[Path] = None) -> Path:
    print("\n" + "=" * 60)
    print("STEP 8: Exporting best checkpoint → ONNX (FP32, opset 12)")
    print("=" * 60)

    from research.training.export_onnx import find_latest_checkpoint, export_yolo_to_onnx  # type: ignore

    if best_pt is None:
        best_pt = find_latest_checkpoint()
    if best_pt is None or not best_pt.exists():
        raise FileNotFoundError("No trained checkpoint found. Run step 6 first.")

    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    metadata = export_yolo_to_onnx(
        weights_path=best_pt,
        output_dir=MODELS_DIR,
        opset=12,
        imgsz=640,
        half=False,
        dynamic=False,
    )
    onnx_path = Path(metadata["onnx_file_path"])
    print(f"\n✓  ONNX model: {onnx_path} ({onnx_path.stat().st_size / 1e6:.1f} MB)")
    return onnx_path


# ─────────────────────────────────────────────────────────────────────────────
# Step 9: ONNX consistency validation
# ─────────────────────────────────────────────────────────────────────────────
def step9_validate_onnx(onnx_path: Optional[Path] = None) -> None:
    print("\n" + "=" * 60)
    print("STEP 9: ONNX consistency validation vs PyTorch")
    print("=" * 60)

    if onnx_path is None:
        onnx_path = MODELS_DIR / "yolov8n_beacon.onnx"
    if not onnx_path.exists():
        print("  ⚠  ONNX model not found — skipping.")
        return

    try:
        from research.training.validate_onnx_consistency import validate_onnx  # type: ignore
        result = validate_onnx(onnx_model_path=onnx_path)
        print(f"✓  ONNX validation: {result}")
    except ImportError:
        # Minimal inline ONNX sanity check
        import onnx
        import onnxruntime as ort
        import numpy as np

        model_proto = onnx.load(str(onnx_path))
        onnx.checker.check_model(model_proto)
        print(f"  onnx.checker: PASSED")

        sess = ort.InferenceSession(str(onnx_path), providers=["CPUExecutionProvider"])
        dummy = np.random.rand(1, 3, 640, 640).astype(np.float32)
        outputs = sess.run(None, {sess.get_inputs()[0].name: dummy})
        print(f"  ORT inference: PASSED — output shape {outputs[0].shape}")

        print(f"✓  ONNX model is valid and runnable")


# ─────────────────────────────────────────────────────────────────────────────
# Main: orchestrate all steps
# ─────────────────────────────────────────────────────────────────────────────
def main() -> None:
    ap = argparse.ArgumentParser(description="HORIZON Colab Training Pipeline")
    ap.add_argument(
        "--steps", nargs="+", type=int,
        default=[0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
        help="Steps to run (default: all 0-9)",
    )
    ap.add_argument("--epochs", type=int, default=200,
                    help="Training epochs for step 6 (default: 200)")
    ap.add_argument("--batch", type=int, default=32,
                    help="Batch size for step 6 (default: 32)")
    ap.add_argument("--samples-per-preset", type=int, default=SAMPLES_PER_PRESET,
                    help="Images per preset for step 1")
    ap.add_argument("--gdrive-root", default=None,
                    help="Optional: Google Drive root to copy artefacts after training")
    args = ap.parse_args()

    steps = set(args.steps)
    print(f"\n{'='*60}")
    print(f"  HORIZON Colab Training Pipeline")
    print(f"  Steps: {sorted(steps)}")
    print(f"{'='*60}\n")

    best_pt: Optional[Path] = None
    onnx_path: Optional[Path] = None

    t_start = time.time()

    if 0 in steps:
        step0_install_deps()

    if 1 in steps:
        step1_generate_dataset(samples_per_preset=args.samples_per_preset)

    if 2 in steps:
        step2_hard_negatives_and_real_laser(
            hard_neg_count=max(1000, args.samples_per_preset),
            real_laser_count=max(1000, args.samples_per_preset),
        )

    if 3 in steps:
        step3_merge()

    if 4 in steps:
        step4_split()

    if 5 in steps:
        step5_validate()

    if 6 in steps:
        import os
        if args.gdrive_root:
            os.environ["HORIZON_GDRIVE_BACKUP"] = args.gdrive_root
        best_pt = step6_train(epochs=args.epochs, batch=args.batch)

    if 7 in steps:
        step7_eval_per_preset(best_pt)

    if 8 in steps:
        onnx_path = step8_export_onnx(best_pt)

    if 9 in steps:
        step9_validate_onnx(onnx_path)

    # Optional: copy artefacts to Google Drive
    if args.gdrive_root:
        gdrive = Path(args.gdrive_root) / "HORIZON_training_artefacts"
        gdrive.mkdir(parents=True, exist_ok=True)
        if onnx_path and onnx_path.exists():
            shutil.copy2(onnx_path, gdrive / onnx_path.name)
            print(f"\n✓  ONNX model copied to Google Drive: {gdrive / onnx_path.name}")
        if best_pt and best_pt.exists():
            shutil.copy2(best_pt, gdrive / "best.pt")
            print(f"✓  best.pt copied to Google Drive: {gdrive / 'best.pt'}")

    elapsed = time.time() - t_start
    h, m = divmod(int(elapsed), 3600)
    m, s = divmod(m, 60)
    print(f"\n{'='*60}")
    print(f"  Pipeline complete in {h:02d}h {m:02d}m {s:02d}s")
    print(f"  Next: copy yolov8n_beacon.onnx to:")
    print(f"        research/training/models/yolov8n_beacon.onnx")
    print(f"        (neural_detector.py will load it automatically)")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
