"""
HORIZON YOLOv8n Training Pipeline  (v2 — Colab GPU Production)
==============================================================
Trains Ultralytics YOLOv8n single-class beacon detector on the v2 synthetic
dataset (14,400 positive + 1,500 hard-negative images).

KEY FIXES over v1
-----------------
* epochs: 5 (CPU demo) → 200 (Colab GPU)
* device: 'cpu' → '0' (first CUDA GPU) with automatic CPU fallback
* batch: 16 → 32 (doubles throughput on Colab T4/A100)
* imgsz: 640 (already correct — keep)
* lr0: 0.01 → 0.005 (conservative start — beacon dataset is domain-specific)
* lrf: 0.01 → 0.001 (LR decays to 0.1% of lr0 over cosine schedule)
* cos_lr: False → True (smooth cosine annealing)
* warmup_epochs: 0 → 5 (prevents early loss spikes)
* mosaic: default → 1.0 (always-on mosaic 4-image augmentation)
* mixup: 0 → 0.10 (10% mixup teaches soft-boundary generalisation)
* degrees: 0 → 20 (rotation — beacon can appear at any orientation)
* translate: 0.1 → 0.2 (large translation for sub-FOV beacons)
* scale: 0.5 → 0.7 (aggressive scale jitter — beacon size varies 5–20 px)
* fliplr: 0.5 → 0.5 (keep)
* flipud: 0.0 → 0.3 (vertical flip also valid for satellite / aerial)
* hsv_v: 0.4 → 0.6 (grayscale value jitter for SNR variability)
* label_smoothing: 0.0 → 0.05 (prevents overconfident wrong predictions)
* patience: 50 → 30 (stop if no improvement for 30 epochs — efficient on GPU)
* save_period: 20 (checkpoint every 20 epochs — Colab session safety)
* workers: 2 → 8 (Colab has 2–4 vCPUs, DataLoader workers saturate GPU)
* close_mosaic: 10 (disable mosaic last 10 epochs for stable convergence)

Training artefact outputs
--------------------------
  research/training/runs/<exp_name>/
    weights/best.pt    ← use this for ONNX export
    weights/last.pt
    results.csv        ← precision / recall / mAP per epoch
    experiment_metadata.json
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path
import time
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


def _detect_device() -> str:
    """Return '0' if CUDA is available (Colab GPU), else 'cpu'."""
    try:
        import torch
        if torch.cuda.is_available():
            gpu_name = torch.cuda.get_device_name(0)
            logger.info("CUDA GPU detected: %s", gpu_name)
            print(f"[TRAIN] GPU detected: {gpu_name}")
            return "0"
    except ImportError:
        pass
    logger.info("No CUDA GPU found — falling back to CPU")
    print("[TRAIN] No GPU detected — using CPU (training will be slow)")
    return "cpu"


@dataclass
class TrainingConfig:
    """Full hyperparameter set for YOLOv8n beacon detector training.

    All values with PLACEHOLDER comment need human validation against
    a NEES/fitness sweep before finalising.  The learning rate and
    augmentation values below are motivated by published YOLOv8 small-object
    best practices but have NOT been independently verified on this dataset.
    """

    # ── Data ──────────────────────────────────────────────────────────────
    dataset_yaml: str = "research/training/dataset.yaml"
    model_name: str = "yolov8n.pt"          # pretrained COCO weights
    imgsz: int = 640
    single_cls: bool = True                  # single 'beacon' class

    # ── Training schedule ─────────────────────────────────────────────────
    epochs: int = 200                        # Colab GPU: ~2–3 h on T4
    batch: int = 32                          # Colab T4 VRAM: 15 GB → 32 safe
    workers: int = 8                         # DataLoader workers
    patience: int = 30                       # Early-stop patience (epochs)
    save_period: int = 20                    # Save checkpoint every N epochs
    close_mosaic: int = 10                   # Disable mosaic last N epochs

    # ── Learning rate (PLACEHOLDER — validate via LR sweep) ───────────────
    lr0: float = 0.005                       # initial LR
    lrf: float = 0.001                       # final LR = lr0 * lrf
    cos_lr: bool = True                      # cosine annealing schedule
    warmup_epochs: int = 5                   # linear LR warmup epochs
    warmup_momentum: float = 0.8
    momentum: float = 0.937
    weight_decay: float = 0.0005

    # ── Augmentation (PLACEHOLDER — validate on val mAP) ──────────────────
    mosaic: float = 1.0                      # 4-image mosaic (always on)
    mixup: float = 0.10                      # MixUp augmentation rate
    degrees: float = 20.0                    # rotation ±20° (beacon any orient)
    translate: float = 0.2                   # translation ±20% of image size
    scale: float = 0.7                       # scale jitter ±70%
    shear: float = 5.0                       # shear ±5°
    fliplr: float = 0.5                      # horizontal flip prob
    flipud: float = 0.3                      # vertical flip prob
    hsv_v: float = 0.6                       # value (brightness) jitter ±60%
    hsv_h: float = 0.0                       # no hue (grayscale → 3ch)
    hsv_s: float = 0.0                       # no saturation (grayscale)

    # ── Loss & regularisation ─────────────────────────────────────────────
    label_smoothing: float = 0.05           # prevent overconfident wrong boxes

    # ── Output ────────────────────────────────────────────────────────────
    project: str = "research/training/runs"
    name: str = "yolov8n_beacon_v2"
    device: str = "auto"                     # "auto" → detect GPU/CPU at runtime
    seed: int = 42
    verbose: bool = True


def run_training(config: Optional[TrainingConfig] = None) -> Dict[str, Any]:
    """Execute the full YOLOv8n training pipeline and save experiment artefacts.

    Returns:
        Experiment metadata dictionary (also written to experiment_metadata.json).
    """
    from ultralytics import YOLO

    cfg = config or TrainingConfig()

    # Resolve device at runtime
    resolved_device = _detect_device() if cfg.device == "auto" else cfg.device
    logger.info("Using device: %s", resolved_device)

    exp_id = f"exp_{int(time.time())}"
    exp_dir = Path(cfg.project) / f"{cfg.name}_{exp_id}"
    exp_dir.mkdir(parents=True, exist_ok=True)

    dataset_yaml = Path(cfg.dataset_yaml)
    if not dataset_yaml.exists():
        raise FileNotFoundError(
            f"Dataset YAML not found at {dataset_yaml}.\n"
            f"Run research/data/generate_synthetic_dataset.py and "
            f"research/data/split_dataset.py first."
        )

    logger.info("Starting YOLOv8n training — %d epochs, device=%s, batch=%d",
                cfg.epochs, resolved_device, cfg.batch)

    # ── Dataset statistics printout ───────────────────────────────────────────
    try:
        import yaml as _yaml
        with open(cfg.dataset_yaml, "r") as _yf:
            _ds = _yaml.safe_load(_yf)
        _split_root = Path(_ds.get("path", "."))
        for _split in ("train", "val", "test"):
            _img_dir = _split_root / _ds.get(_split, f"{_split}/images")
            _count = len(list(_img_dir.glob("*.png"))) + len(list(_img_dir.glob("*.jpg")))
            print(f"  [DATASET] {_split:5s}: {_count:6d} images  ({_img_dir})")
    except Exception as _e:
        logger.warning("Could not read dataset stats: %s", _e)

    # ── GPU memory info ───────────────────────────────────────────────────────
    if resolved_device != "cpu":
        try:
            import torch
            _vram_total = torch.cuda.get_device_properties(0).total_memory / 1e9
            _vram_free = (torch.cuda.get_device_properties(0).total_memory
                          - torch.cuda.memory_allocated(0)) / 1e9
            print(f"  [GPU]     VRAM total={_vram_total:.1f} GB  free={_vram_free:.1f} GB")
        except Exception:
            pass

    print(f"\n{'='*70}")
    print(f"  HORIZON YOLOv8n Training  —  v2 Production Config")
    print(f"{'='*70}")
    print(f"  epochs        = {cfg.epochs}")
    print(f"  batch         = {cfg.batch}")
    print(f"  device        = {resolved_device}")
    print(f"  imgsz         = {cfg.imgsz}")
    print(f"  lr0           = {cfg.lr0}  [PLACEHOLDER — validate via LR sweep]")
    print(f"  lrf           = {cfg.lrf}")
    print(f"  cos_lr        = {cfg.cos_lr}")
    print(f"  warmup_epochs = {cfg.warmup_epochs}")
    print(f"  mosaic        = {cfg.mosaic}")
    print(f"  mixup         = {cfg.mixup}")
    print(f"  degrees       = {cfg.degrees}")
    print(f"  scale         = {cfg.scale}")
    print(f"  label_smooth  = {cfg.label_smoothing}")
    print(f"  patience      = {cfg.patience}")
    print(f"  dataset       = {cfg.dataset_yaml}")
    model = YOLO(cfg.model_name)

    # Real-time backup callback to Google Drive if configured
    gdrive_backup = os.environ.get("HORIZON_GDRIVE_BACKUP")
    if gdrive_backup:
        backup_dir = Path(gdrive_backup) / "HORIZON_training_artefacts"
        backup_dir.mkdir(parents=True, exist_ok=True)

        def _on_train_epoch_end(trainer):
            # Sync best.pt and last.pt to Google Drive every 5 epochs and on best save
            try:
                import shutil
                cur_best = Path(trainer.save_dir) / "weights" / "best.pt"
                cur_last = Path(trainer.save_dir) / "weights" / "last.pt"
                if cur_best.exists():
                    shutil.copy2(cur_best, backup_dir / "best.pt")
                if cur_last.exists():
                    shutil.copy2(cur_last, backup_dir / "last.pt")
            except Exception as e:
                logger.debug("Drive sync warning: %s", e)

        model.add_callback("on_train_epoch_end", _on_train_epoch_end)
        print(f"  [BACKUP] Real-time Google Drive sync enabled -> {backup_dir}")

    results = model.train(
        data=cfg.dataset_yaml,
        epochs=cfg.epochs,
        imgsz=cfg.imgsz,
        batch=cfg.batch,
        device=resolved_device,
        workers=cfg.workers,
        project=str(exp_dir.parent),
        name=exp_dir.name,
        seed=cfg.seed,
        single_cls=cfg.single_cls,
        verbose=cfg.verbose,
        save=True,
        save_period=cfg.save_period,
        patience=cfg.patience,
        close_mosaic=cfg.close_mosaic,
        # Learning rate
        lr0=cfg.lr0,
        lrf=cfg.lrf,
        cos_lr=cfg.cos_lr,
        warmup_epochs=cfg.warmup_epochs,
        warmup_momentum=cfg.warmup_momentum,
        momentum=cfg.momentum,
        weight_decay=cfg.weight_decay,
        # Augmentation
        mosaic=cfg.mosaic,
        mixup=cfg.mixup,
        degrees=cfg.degrees,
        translate=cfg.translate,
        scale=cfg.scale,
        shear=cfg.shear,
        fliplr=cfg.fliplr,
        flipud=cfg.flipud,
        hsv_h=cfg.hsv_h,
        hsv_s=cfg.hsv_s,
        hsv_v=cfg.hsv_v,
        # Loss
        label_smoothing=cfg.label_smoothing,
    )

    best_pt = exp_dir / "weights" / "best.pt"
    last_pt = exp_dir / "weights" / "last.pt"

    metadata: Dict[str, Any] = {
        "experiment_id": exp_id,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "config": asdict(cfg),
        "resolved_device": resolved_device,
        "best_checkpoint": str(best_pt),
        "last_checkpoint": str(last_pt),
        "checkpoint_exists": best_pt.exists(),
    }

    # Capture final validation metrics from the training result object
    try:
        if hasattr(results, "results_dict"):
            final_metrics = results.results_dict
            metadata["final_metrics"] = {
                k: float(v) for k, v in final_metrics.items()
                if isinstance(v, (int, float))
            }
    except Exception as e:
        logger.warning("Could not extract training result metrics: %s", e)

    with open(exp_dir / "experiment_metadata.json", "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    logger.info(
        "Training complete. Best checkpoint: %s (exists=%s)",
        best_pt, best_pt.exists()
    )
    print(f"\n✓  Training complete!")
    print(f"   Best checkpoint: {best_pt}")
    print(f"   Next step: run research/training/export_onnx.py to export to ONNX")
    return metadata


if __name__ == "__main__":
    import argparse

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    ap = argparse.ArgumentParser(
        description="HORIZON YOLOv8n Beacon Detector Training v2 (Colab GPU)"
    )
    ap.add_argument("--epochs", type=int, default=200,
                    help="Training epochs (default: 200 for Colab GPU)")
    ap.add_argument("--batch", type=int, default=32,
                    help="Batch size (default: 32 for T4 GPU)")
    ap.add_argument("--device", default="auto",
                    help="Device: 'auto' (detect), '0' (GPU), 'cpu'")
    ap.add_argument("--dataset-yaml", default="research/training/dataset.yaml",
                    help="Path to YOLO dataset YAML")
    ap.add_argument("--lr0", type=float, default=0.005,
                    help="Initial learning rate (PLACEHOLDER — needs validation)")
    ap.add_argument("--workers", type=int, default=8,
                    help="DataLoader workers")
    args = ap.parse_args()

    cfg = TrainingConfig(
        epochs=args.epochs,
        batch=args.batch,
        device=args.device,
        dataset_yaml=args.dataset_yaml,
        lr0=args.lr0,
        workers=args.workers,
    )
    result = run_training(cfg)
    print(json.dumps(result, indent=2))
