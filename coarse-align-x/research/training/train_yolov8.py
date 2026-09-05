"""
HORIZON YOLOv8n Single-Class Training Pipeline
=======================================================
Trains Ultralytics YOLOv8n single-class beacon detector on synthetic and domain-adapted datasets.

Saves:
  - Experiment directory: research/training/runs/exp_<id>/
  - Best checkpoint: best.pt
  - Last checkpoint: last.pt
  - Experiment metadata: experiment_metadata.json
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import logging
from pathlib import Path
import time
from typing import Dict, Any, Optional
from ultralytics import YOLO

logger = logging.getLogger(__name__)


@dataclass
class TrainingConfig:
    """Configurable hyperparameters for YOLOv8n beacon detector training."""

    dataset_yaml: str = "research/training/dataset.yaml"
    model_name: str = "yolov8n.pt"  # Pretrained base weights or yolov8n.yaml
    imgsz: int = 640
    epochs: int = 15
    batch: int = 16
    lr0: float = 0.01
    lrf: float = 0.01
    seed: int = 42
    device: str = "cpu"  # 'cpu' or '0' for GPU
    project: str = "research/training/runs"
    name: str = "yolov8n_beacon_exp"
    workers: int = 2
    single_cls: bool = True


def run_training(config: Optional[TrainingConfig] = None) -> Dict[str, Any]:
    """Execute YOLOv8n training pipeline and save experiment artifacts."""
    cfg = config or TrainingConfig()
    logger.info("Initializing YOLOv8n training with config: %s", cfg)

    exp_id = f"exp_{int(time.time())}"
    exp_dir = Path(cfg.project) / f"{cfg.name}_{exp_id}"
    exp_dir.mkdir(parents=True, exist_ok=True)

    # Load YOLOv8n model
    model = YOLO(cfg.model_name)

    # Train model
    results = model.train(
        data=cfg.dataset_yaml,
        epochs=cfg.epochs,
        imgsz=cfg.imgsz,
        batch=cfg.batch,
        seed=cfg.seed,
        device=cfg.device,
        project=str(exp_dir.parent),
        name=exp_dir.name,
        workers=cfg.workers,
        single_cls=cfg.single_cls,
        save=True,
        verbose=True,
    )

    best_pt = exp_dir / "weights" / "best.pt"
    last_pt = exp_dir / "weights" / "last.pt"

    metadata: Dict[str, Any] = {
        "experiment_id": exp_id,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "config": asdict(cfg),
        "best_checkpoint": str(best_pt),
        "last_checkpoint": str(last_pt),
        "checkpoint_exists": best_pt.exists(),
    }

    with open(exp_dir / "experiment_metadata.json", "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    logger.info("Training complete. Best checkpoint saved to %s", best_pt)
    return metadata


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    t_cfg = TrainingConfig(epochs=5, batch=16, imgsz=640, device="cpu")
    res = run_training(t_cfg)
    print(json.dumps(res, indent=2))
