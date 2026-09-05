# Model Card — YOLOv8n Beacon Detector (ONNX FP32)

## Model Details
- **Model Name**: YOLOv8n-Beacon
- **Architecture**: Ultralytics YOLOv8 Nano (Single-Class Object Detection)
- **Target Class**: `beacon` (`class_id: 0`)
- **Export Format**: FP32 ONNX (`opset 12`)
- **Runtime Engine**: ONNX Runtime CPU (`onnxruntime`)
- **Input Dimensions**: $1 \times 3 \times 640 \times 640$ normalized float32 tensor
- **Primary Task**: Optical beacon candidate localization for FSOC mobile terminal coarse alignment

## Training & Domain Adaptation Data
1. **Pre-training Data**: BSD-3 Zenodo Laser-Spot Dataset (`ADVRHumanoids/nn_laser_spot_tracking`).
2. **Domain Adaptation Data**: Synthetic renders from Phase 1–3 scenario engine across 8 disturbance configurations.
3. **Hard-Negative Mining Data**: Mined Salt & Pepper noise clusters and bright reflection spots.

## Limitations & Known Failure Modes
- Subpixel accuracy requires Phase 4 centroid refinement on the neural ROI.
- Extreme low light ($< 5\%$ signal contrast) relies on Kalman filter state estimation coasting.
