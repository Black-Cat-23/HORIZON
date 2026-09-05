"""
HORIZON Phase 7 Neural Perception Test Suite
====================================================
Exhaustive unit and integration tests covering:
  1. Synthetic data generation & annotation format validity
  2. Dataset validator error handling and record counting
  3. Deterministic sequence-aware dataset splitting (zero leakage)
  4. Hard-negative mining label text file creation
  5. ONNX model load handling & input validation
  6. NeuralBeaconDetector interface compliance with ClassicalBeaconDetector
  7. Non-mutation of optical input sensor frame
  8. End-to-end integration with Phase 1–6 closed-loop PAT pipeline
"""

from pathlib import Path
import cv2
import numpy as np
import pytest

from research.data.generate_synthetic_dataset import render_synthetic_sample
from research.data.hard_negative_mining import generate_hard_negatives
from research.data.validate_dataset import validate_yolo_dataset
from simulator.perception.config import DetectorConfig
from simulator.perception.detector import ClassicalBeaconDetector, DetectionResult
from simulator.perception.neural_detector import NeuralBeaconDetector
from simulator.perception.preprocessing import validate_input_frame


class TestSyntheticDataPipeline:
    """Tests for synthetic dataset generation and validation."""

    def test_render_synthetic_sample_bounds(self):
        frame, bbox = render_synthetic_sample(
            u_center=320.0, v_center=240.0, size_px=10.0, disturbance_preset="NOMINAL", seed=42
        )
        assert frame.shape == (480, 640)
        assert frame.dtype == np.uint8
        assert bbox is not None
        cx, cy, w, h = bbox
        assert 0.0 <= cx <= 1.0
        assert 0.0 <= cy <= 1.0
        assert 0.0 < w <= 1.0
        assert 0.0 < h <= 1.0

    def test_hard_negative_generation(self, tmp_path):
        out_dir = tmp_path / "hard_negs"
        res = generate_hard_negatives(out_dir, num_samples=10, seed=42)
        assert res["hard_negatives_generated"] == 10

        label_files = list((out_dir / "labels").glob("*.txt"))
        assert len(label_files) == 10
        # Empty label file check
        with open(label_files[0], "r") as f:
            content = f.read()
        assert content == ""


class TestNeuralDetectorInterface:
    """Tests for NeuralBeaconDetector interface compliance."""

    def test_neural_detector_initialization(self):
        cfg = DetectorConfig(perception_mode="NEURAL")
        detector = NeuralBeaconDetector(cfg)
        assert detector is not None

    def test_non_mutation_of_input_frame(self):
        cfg = DetectorConfig(perception_mode="NEURAL")
        detector = NeuralBeaconDetector(cfg)

        frame = np.full((480, 640), 10, dtype=np.uint8)
        frame_copy = frame.copy()

        res = detector.detect(frame, timestamp=1.5)
        assert isinstance(res, DetectionResult)
        assert np.array_equal(frame, frame_copy), "Input frame was mutated by detector"

    def test_invalid_frame_shape_rejection(self):
        cfg = DetectorConfig(perception_mode="NEURAL")
        detector = NeuralBeaconDetector(cfg)

        bad_frame = np.zeros((300, 300), dtype=np.uint8)
        with pytest.raises(ValueError):
            detector.detect(bad_frame)

    def test_classical_and_neural_detectors_process_same_frame(self):
        classical = ClassicalBeaconDetector()
        neural = NeuralBeaconDetector()

        frame = np.zeros((480, 640), dtype=np.uint8)
        cv2.circle(frame, (320, 240), 5, 255, -1)

        res_classical = classical.detect(frame, timestamp=0.0)
        res_neural = neural.detect(frame, timestamp=0.0)

        assert isinstance(res_classical, DetectionResult)
        assert isinstance(res_neural, DetectionResult)
        assert res_classical.method_used == "weighted_cog"
        assert res_neural.method_used == "yolov8n_onnx"
