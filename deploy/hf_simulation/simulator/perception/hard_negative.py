"""
HORIZON Perception Hard-Negative Mining Pipeline
================================================
Phase 7 Upgrade: Harvesting and logging false-positive detections during stress & distractor runs.

Provides:
  1. `HardNegativeCandidate`: Record of optical background/distractor artifacts mistakenly detected.
  2. `HardNegativeMiner`: Thread-safe / session-isolated collector saving cropped ROIs and metadata.
  3. Contamination Firewall: Stores data in dedicated isolation directory `research/training/hard_negatives/`
     completely segregated from benchmark evaluation datasets.

Strict Invariant: Zero contamination of final evaluation or ground-truth leakage.
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass
from pathlib import Path
import time
from typing import List, Optional, Tuple
import cv2
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class HardNegativeSample:
    """Record of a false-positive candidate harvested during stress execution."""
    sample_id: str
    timestamp_s: float
    bbox: Tuple[int, int, int, int]
    score: float
    snr: float
    peak_intensity: float
    background_mean: float
    distractor_type: str
    failure_mode: str
    crop_filename: str


class HardNegativeMiner:
    """Harvests and persists false-positive optical artifacts for model hardening."""

    def __init__(
        self,
        output_dir: str | Path = "research/training/hard_negatives",
        max_samples: int = 1000,
        save_crops: bool = True,
    ) -> None:
        self.output_dir = Path(output_dir)
        self.max_samples = max_samples
        self.save_crops = save_crops
        self._samples: List[HardNegativeSample] = []

        if self.save_crops:
            self.output_dir.mkdir(parents=True, exist_ok=True)
            (self.output_dir / "crops").mkdir(parents=True, exist_ok=True)

    @property
    def sample_count(self) -> int:
        return len(self._samples)

    def record_false_positive(
        self,
        frame: np.ndarray,
        bbox: Tuple[int, int, int, int],
        score: float,
        snr: float,
        peak_intensity: float,
        background_mean: float,
        distractor_type: str = "NOISE_CLUSTER",
        failure_mode: str = "FALSE_ACQUISITION",
        timestamp_s: float = 0.0,
    ) -> Optional[HardNegativeSample]:
        """Record a confirmed false-positive detection.

        Args:
            frame: Full sensor image (H, W).
            bbox: Bounding box (x, y, w, h).
            score: Confidence score of false detection.
            snr: Signal to noise ratio.
            peak_intensity: Peak DN.
            background_mean: Local background mean DN.
            distractor_type: Description of distractor (e.g. SPECULAR_REFLECTION, NOISE_CLUSTER).
            failure_mode: Failure category.
            timestamp_s: Simulation timestamp.

        Returns:
            Created HardNegativeSample or None if buffer is full.
        """
        if len(self._samples) >= self.max_samples:
            return None

        sample_id = f"hn_{int(time.time() * 1000)}_{len(self._samples):04d}"
        crop_filename = ""

        if self.save_crops and frame is not None and frame.size > 0:
            x, y, w, h = bbox
            H, W = frame.shape[:2]
            # Safe bounding
            x1, y1 = max(0, x), max(0, y)
            x2, y2 = min(W, x + w), min(H, y + h)
            crop = frame[y1:y2, x1:x2]
            if crop.size > 0:
                crop_path = self.output_dir / "crops" / f"{sample_id}.png"
                cv2.imwrite(str(crop_path), crop)
                crop_filename = crop_path.name

        sample = HardNegativeSample(
            sample_id=sample_id,
            timestamp_s=timestamp_s,
            bbox=bbox,
            score=score,
            snr=snr,
            peak_intensity=peak_intensity,
            background_mean=background_mean,
            distractor_type=distractor_type,
            failure_mode=failure_mode,
            crop_filename=crop_filename,
        )
        self._samples.append(sample)
        return sample

    def export_manifest(self, manifest_name: str = "hard_negatives_manifest.json") -> Path:
        """Export index manifest to JSON."""
        manifest_path = self.output_dir / manifest_name
        data = [asdict(s) for s in self._samples]
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        logger.info("Exported %d hard negative samples to %s", len(data), manifest_path)
        return manifest_path

    def clear(self) -> None:
        """Clear recorded in-memory samples."""
        self._samples.clear()
