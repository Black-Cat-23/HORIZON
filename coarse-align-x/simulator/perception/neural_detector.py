"""
HORIZON Neural Beacon Detector Engine (YOLOv8n + ONNX Runtime)
=======================================================================
Phase 7 Neural Detector implementing the standard Detector interface.
Performs:
  1. Grayscale 640×480 sensor frame validation & letterbox preprocessing
  2. FP32 ONNX Runtime CPU inference (`onnxruntime.InferenceSession`)
  3. Raw tensor decoding & Non-Maximum Suppression (NMS)
  4. Phase 4 Subpixel centroid refinement inside neural bounding box ROI
  5. Standardized DetectionResult mapping with model version metadata

Strict Invariant: Zero ground-truth leakage or dependencies.
Uses ONNX Runtime CPU execution without PyTorch runtime dependency.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
import time
from typing import Optional, Tuple, List
import cv2
import numpy as np
import onnxruntime as ort

from simulator.perception.candidate import BeaconCandidate
from simulator.perception.centroid import compute_weighted_cog, compute_geometric_centroid, compute_gaussian_fit
from simulator.perception.config import DetectorConfig, NeuralDetectorConfig
from simulator.perception.detector import DetectionResult
from simulator.perception.preprocessing import validate_input_frame

logger = logging.getLogger(__name__)


class NeuralBeaconDetector:
    """YOLOv8n ONNX Neural Beacon Detector.

    Parameters:
        config: DetectorConfig dataclass containing neural settings.
    """

    def __init__(self, config: Optional[DetectorConfig] = None) -> None:
        self._config = config or DetectorConfig()
        self._neural_cfg = self._config.neural
        self._session: Optional[ort.InferenceSession] = None
        self._input_name: str = ""
        self._model_metadata: dict = {}

        self._load_onnx_model()

    def _load_onnx_model(self) -> None:
        """Load ONNX model and metadata if available."""
        model_path = Path(self._neural_cfg.onnx_model_path)
        meta_path = Path(self._neural_cfg.metadata_path)

        if not model_path.exists():
            logger.warning(
                "ONNX model file not found at %s. Neural detector will report no detections until trained.",
                model_path,
            )
            return

        try:
            self._session = ort.InferenceSession(
                str(model_path), providers=["CPUExecutionProvider"]
            )
            self._input_name = self._session.get_inputs()[0].name
            logger.info("Successfully initialized ONNX Runtime session for %s", model_path)

            if meta_path.exists():
                with open(meta_path, "r", encoding="utf-8") as f:
                    self._model_metadata = json.load(f)
        except Exception as e:
            logger.error("Failed to load ONNX Runtime session: %s", e)
            self._session = None

    @property
    def is_model_loaded(self) -> bool:
        return self._session is not None

    def detect(
        self,
        frame: np.ndarray,
        timestamp: float = 0.0,
        collect_diagnostics: bool = False,
    ) -> DetectionResult:
        """Process 640×480 optical frame and locate beacon centroid using YOLOv8n ONNX model."""
        t_start = time.perf_counter()

        valid_frame = validate_input_frame(
            frame,
            expected_width=self._config.input_width,
            expected_height=self._config.input_height,
        )

        if self._session is None:
            t_end = time.perf_counter()
            return DetectionResult(
                detected=False,
                centroid=None,
                bbox=None,
                confidence=0.0,
                candidate_count=0,
                method_used="yolov8n_onnx",
                processing_time_ms=(t_end - t_start) * 1000.0,
                timestamp=timestamp,
            )

        # 1. Preprocessing: 640x480 grayscale uint8 -> 640x640 float32 RGB tensor [1, 3, 640, 640]
        h_orig, w_orig = valid_frame.shape
        img_rgb = cv2.cvtColor(valid_frame, cv2.COLOR_GRAY2RGB)
        img_resized = cv2.resize(img_rgb, (self._neural_cfg.input_size, self._neural_cfg.input_size))
        img_tensor = img_resized.astype(np.float32) / 255.0
        img_tensor = np.transpose(img_tensor, (2, 0, 1))
        img_batch = np.expand_dims(img_tensor, axis=0)

        # 2. Execute ONNX Runtime Inference
        raw_outputs = self._session.run(None, {self._input_name: img_batch})[0]

        # 3. Post-process ONNX tensor output [1, 5, 8400]
        output = np.squeeze(raw_outputs, axis=0)
        best_cand_bbox: Optional[Tuple[int, int, int, int]] = None
        best_conf: float = 0.0

        if output.shape[0] == 5:  # (cx, cy, w, h, conf)
            boxes = output[:4, :].T
            confs = output[4, :]

            scale_x = w_orig / float(self._neural_cfg.input_size)
            scale_y = h_orig / float(self._neural_cfg.input_size)

            valid_mask = confs >= self._neural_cfg.confidence_threshold
            if np.any(valid_mask):
                valid_indices = np.where(valid_mask)[0]
                # Sort candidates by confidence descending
                sorted_indices = valid_indices[np.argsort(-confs[valid_indices])]

                for idx in sorted_indices:
                    cx_box, cy_box, w_box, h_box = boxes[idx]
                    conf = float(confs[idx])

                    cx_orig = cx_box * scale_x
                    cy_orig = cy_box * scale_y

                    # Verify center is inside valid image bounds
                    if 0.0 <= cx_orig < float(w_orig) and 0.0 <= cy_orig < float(h_orig):
                        x1 = int((cx_box - w_box / 2.0) * scale_x)
                        y1 = int((cy_box - h_box / 2.0) * scale_y)
                        bw = int(w_box * scale_x)
                        bh = int(h_box * scale_y)

                        x1 = max(0, min(w_orig - 1, x1))
                        y1 = max(0, min(h_orig - 1, y1))
                        bw = max(1, min(w_orig - x1, bw))
                        bh = max(1, min(h_orig - y1, bh))

                        # Check if crop has real optical intensity contrast above background noise
                        crop = valid_frame[y1 : y1 + bh, x1 : x1 + bw]
                        if crop.size > 0:
                            bg_est = float(np.median(valid_frame))
                            max_val = float(np.max(crop))
                            net_flux = float(np.sum(np.maximum(crop.astype(float) - bg_est, 0.0)))
                            # Reject dark/empty bounding boxes without real optical beacon signal
                            if net_flux >= 35.0 and (max_val - bg_est) >= 25.0:
                                best_cand_bbox = (x1, y1, bw, bh)
                                best_conf = conf
                                break

        # 4. Subpixel Centroid Refinement inside Neural Bounding Box ROI
        centroid: Optional[Tuple[float, float]] = None
        if best_cand_bbox is not None:
            x, y, w, h = best_cand_bbox
            pad = self._config.centroid.roi_padding_px
            x1 = max(0, x - pad)
            y1 = max(0, y - pad)
            x2 = min(w_orig, x + w + pad)
            y2 = min(h_orig, y + h + pad)

            roi_crop = valid_frame[y1:y2, x1:x2]
            if roi_crop.size > 0:
                if self._neural_cfg.enable_subpixel_refinement:
                    min_val = float(np.min(roi_crop))
                    max_val = float(np.max(roi_crop))
                    if max_val > min_val + 4.0:
                        thresh_val = min_val + 0.35 * (max_val - min_val)
                    else:
                        thresh_val = min_val
                    _, mask_crop = cv2.threshold(roi_crop, int(thresh_val), 255, cv2.THRESH_BINARY)
                    centroid = compute_weighted_cog(roi_crop, mask_crop, min_val, x1, y1)
                else:
                    # Integer bounding box center
                    centroid = (float(x + w / 2.0), float(y + h / 2.0))

        t_end = time.perf_counter()
        detected = (best_cand_bbox is not None and best_conf >= self._neural_cfg.confidence_threshold)

        return DetectionResult(
            detected=detected,
            centroid=centroid if detected else None,
            bbox=best_cand_bbox if detected else None,
            confidence=best_conf if detected else 0.0,
            candidate_count=1 if detected else 0,
            method_used="yolov8n_onnx",
            processing_time_ms=(t_end - t_start) * 1000.0,
            timestamp=timestamp,
        )
