"""
HORIZON ONNX Export Pipeline
====================================
Exports trained PyTorch YOLOv8n checkpoint to FP32 ONNX format for ONNX Runtime inference.

Outputs:
  - ONNX graph: research/training/models/yolov8n_beacon.onnx
  - Model metadata: research/training/models/model_metadata.json
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
import shutil
import time
from typing import Dict, Any, List, Optional
from ultralytics import YOLO

logger = logging.getLogger(__name__)


def find_latest_checkpoint() -> Optional[Path]:
    """Find the most recently created best.pt checkpoint in project runs."""
    search_dirs = [Path("research/training/runs"), Path("runs/detect"), Path("runs")]
    candidates: List[Path] = []
    for sdir in search_dirs:
        if sdir.exists():
            candidates.extend(sdir.rglob("best.pt"))
    if not candidates:
        return None
    return max(candidates, key=lambda p: p.stat().st_mtime)


def export_yolo_to_onnx(
    weights_path: Path,
    output_dir: Path,
    opset: int = 12,
    imgsz: int = 640,
    half: bool = False,
    dynamic: bool = False,
) -> Dict[str, Any]:
    """Export PyTorch YOLO weights to ONNX format."""
    weights_path = Path(weights_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    if not weights_path.exists():
        raise FileNotFoundError(f"PyTorch weights not found at: {weights_path}")

    logger.info("Loading PyTorch model from %s for ONNX export...", weights_path)
    model = YOLO(str(weights_path))

    # Export using Ultralytics export API
    exported_onnx_path = model.export(
        format="onnx",
        opset=opset,
        imgsz=imgsz,
        half=half,
        dynamic=dynamic,
        simplify=True,
    )

    # Copy / move exported model to standard output path
    target_onnx_file = output_dir / "yolov8n_beacon.onnx"
    shutil.move(str(exported_onnx_path), str(target_onnx_file))

    metadata: Dict[str, Any] = {
        "model_name": "YOLOv8n-Beacon",
        "model_family": "YOLOv8",
        "export_format": "ONNX",
        "opset_version": opset,
        "input_width": imgsz,
        "input_height": imgsz,
        "input_channels": 3,
        "precision": "FP32" if not half else "FP16",
        "class_names": ["beacon"],
        "num_classes": 1,
        "onnx_file_path": str(target_onnx_file),
        "export_timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
    }

    metadata_path = output_dir / "model_metadata.json"
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    logger.info("Exported ONNX model successfully to %s", target_onnx_file)
    return metadata


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    latest_ckpt = find_latest_checkpoint()
    out_dir = Path("research/training/models")
    if latest_ckpt and latest_ckpt.exists():
        res = export_yolo_to_onnx(latest_ckpt, out_dir)
        print(json.dumps(res, indent=2))
    else:
        print("No trained checkpoint found. Run training script first.")
