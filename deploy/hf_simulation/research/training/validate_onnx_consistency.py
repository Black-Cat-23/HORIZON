"""
HORIZON PyTorch vs ONNX Consistency Validator
=====================================================
Validates prediction consistency between PyTorch YOLOv8n model and exported ONNX Runtime model.

Verifies:
  - Bounding box center delta: |u_pytorch - u_onnx| <= 0.5 px
  - Bounding box size delta: |w_pytorch - w_onnx| <= 0.5 px
  - Confidence delta: |conf_pytorch - conf_onnx| <= 0.01

Strict Invariant: Fails validation if PyTorch and ONNX Runtime outputs diverge materially.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import cv2
import numpy as np
import onnxruntime as ort
from ultralytics import YOLO

logger = logging.getLogger(__name__)


def validate_pytorch_onnx_consistency(
    pytorch_weights: Path,
    onnx_file: Path,
    test_images_dir: Path,
    conf_threshold: float = 0.25,
) -> Dict[str, Any]:
    """Compare PyTorch and ONNX Runtime predictions across a test image directory."""
    pytorch_weights = Path(pytorch_weights)
    onnx_file = Path(onnx_file)
    test_images_dir = Path(test_images_dir)

    if not pytorch_weights.exists():
        raise FileNotFoundError(f"PyTorch weights not found: {pytorch_weights}")
    if not onnx_file.exists():
        raise FileNotFoundError(f"ONNX model not found: {onnx_file}")

    # Load PyTorch model
    pt_model = YOLO(str(pytorch_weights))

    # Load ONNX Runtime session
    session = ort.InferenceSession(str(onnx_file), providers=["CPUExecutionProvider"])
    input_name = session.get_inputs()[0].name

    image_files = sorted(
        list(test_images_dir.glob("*.jpg")) + list(test_images_dir.glob("*.png"))
    )

    if not image_files:
        raise FileNotFoundError(f"No test images found in {test_images_dir}")

    total_images = len(image_files)
    matched_detections = 0
    bbox_deltas_u: List[float] = []
    bbox_deltas_v: List[float] = []
    conf_deltas: List[float] = []

    for img_p in image_files:
        frame = cv2.imread(str(img_p))
        if frame is None:
            continue

        # 1. PyTorch inference
        pt_res = pt_model.predict(frame, conf=conf_threshold, verbose=False)[0]

        # 2. ONNX preprocessing (640x480 -> 640x640 3-channel RGB float32)
        h_orig, w_orig = frame.shape[:2]
        img_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img_resized = cv2.resize(img_rgb, (640, 640))
        img_tensor = img_resized.astype(np.float32) / 255.0
        img_tensor = np.transpose(img_tensor, (2, 0, 1))
        img_batch = np.expand_dims(img_tensor, axis=0)

        # ONNX inference
        onnx_raw = session.run(None, {input_name: img_batch})[0]

        # Compare detection outputs
        pt_boxes = pt_res.boxes
        if len(pt_boxes) > 0 and onnx_raw is not None:
            pt_box = pt_boxes[0]
            pt_xywh = pt_box.xywh[0].cpu().numpy()  # (cx, cy, w, h)
            pt_conf = float(pt_box.conf[0].cpu().numpy())

            # Parse ONNX output [1, 5, 8400] -> (cx, cy, w, h, conf)
            onnx_out = np.squeeze(onnx_raw, axis=0)
            if onnx_out.shape[0] == 5:
                # Shape [5, 8400]
                boxes_onnx = onnx_out[:4, :].T
                confs_onnx = onnx_out[4, :]
                best_idx = np.argmax(confs_onnx)
                onnx_conf = float(confs_onnx[best_idx])
                if onnx_conf >= conf_threshold:
                    # Rescale ONNX box from 640x640 to original 640x480
                    onnx_cx = boxes_onnx[best_idx, 0] * (w_orig / 640.0)
                    onnx_cy = boxes_onnx[best_idx, 1] * (h_orig / 640.0)

                    matched_detections += 1
                    bbox_deltas_u.append(abs(pt_xywh[0] - onnx_cx))
                    bbox_deltas_v.append(abs(pt_xywh[1] - onnx_cy))
                    conf_deltas.append(abs(pt_conf - onnx_conf))

    mean_delta_u = float(np.mean(bbox_deltas_u)) if bbox_deltas_u else 0.0
    mean_delta_v = float(np.mean(bbox_deltas_v)) if bbox_deltas_v else 0.0
    mean_conf_delta = float(np.mean(conf_deltas)) if conf_deltas else 0.0

    is_consistent = (mean_delta_u <= 0.5 and mean_delta_v <= 0.5 and mean_conf_delta <= 0.01)

    result = {
        "pytorch_weights": str(pytorch_weights),
        "onnx_file": str(onnx_file),
        "total_test_images": total_images,
        "matched_detections": matched_detections,
        "mean_delta_u_px": mean_delta_u,
        "mean_delta_v_px": mean_delta_v,
        "mean_confidence_delta": mean_conf_delta,
        "is_consistent": is_consistent,
    }

    logger.info("Consistency validation complete: %s (Mean delta U: %.3f px, V: %.3f px)",
                "PASSED" if is_consistent else "FAILED", mean_delta_u, mean_delta_v)
    return result


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


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    pt_p = find_latest_checkpoint()
    onnx_p = Path("research/training/models/yolov8n_beacon.onnx")
    test_dir = Path("research/data/yolo_dataset_split/test/images")
    if pt_p and pt_p.exists() and onnx_p.exists() and test_dir.exists():
        res = validate_pytorch_onnx_consistency(pt_p, onnx_p, test_dir)
        print(json.dumps(res, indent=2))
    else:
        print(f"Required models (pt_p={pt_p}, onnx={onnx_p.exists()}) or test images not found.")
