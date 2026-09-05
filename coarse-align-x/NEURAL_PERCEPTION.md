# Phase 7 — Neural Perception & ONNX Inference Engine Documentation

## 1. Architecture Overview

Phase 7 introduces the **YOLOv8n Neural Perception & ONNX Runtime Inference Engine** into HORIZON. It operates in parallel with the verified Phase 4 classical perception detector (`perception_mode: "CLASSICAL"` / `"NEURAL"`).

```
640×480 Optical Sensor Frame
           ↓
   Neural Preprocessing (640×640 float32 RGB tensor)
           ↓
   ONNX Runtime CPU Engine (`yolov8n_beacon.onnx`)
           ↓
   NMS Bounding Box & Confidence Decoding
           ↓
   Phase 4 Subpixel Centroid Refinement (Weighted CoG / Gaussian Fit on ROI)
           ↓
   DetectionResult → Phase 5 Association / Estimator → Phase 6 Closed-Loop PAT
```

---

## 2. Data Strategy & 3-Stage Training Pipeline

Following Section 6.3 of the Architecture Specification:

1. **Pre-training Starting Point**: Ingestion and verification of the BSD-3 licensed Zenodo laser-spot dataset (`ADVRHumanoids/nn_laser_spot_tracking`).
2. **Synthetic Domain Adaptation**: Generation of domain-matched synthetic renders using the Phase 1–3 scenario engine (`WORLD -> VIRTUAL CAMERA -> DISTURBANCE ENGINE`) across 8 disturbance presets and 4 beacon sizes ($5\times 5$ to $20\times 20$).
3. **Hard-Negative Mining**: Explicit rendering of non-beacon distractors (Salt & Pepper noise clumps, reflections) with empty label files (`.txt` files with 0 lines) to train the model to suppress false locks.

---

## 3. Deployment & ONNX Runtime

* **Inference Backend**: `onnxruntime.InferenceSession` on CPU (`CPUExecutionProvider`).
* **Graph Format**: FP32 static ONNX graph (`yolov8n_beacon.onnx`).
* **Subpixel Refinement**: YOLO provides the robust spatial ROI; the Phase 4 subpixel centroid engine computes continuous subpixel centroids ($(u, v)$ with $< 0.1\text{ px}$ accuracy).
