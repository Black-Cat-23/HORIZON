"""
HORIZON False Optical Target Distractor Generator Engine
=========================================================
Generates physically and visually plausible false optical target distractors in sensor frames.

Supported Distractor Types:
  - "small_spot"     : High-intensity compact Gaussian spot mimicking false beacon
  - "large_blob"     : Broad spatial optical flare / solar reflection
  - "multiple_spots" : Multi-target distractor constellation (testing false lock)
  - "reflection_like": Elongated linear optics reflection / internal flare streak
  - "noise_cluster"  : Regional hot-pixel cluster

Zero ground-truth state contamination — distractor geometry is rasterized purely into the sensor frame.
"""

from __future__ import annotations

import math
from typing import List, Tuple
import numpy as np

from simulator.disturbances.config import DistractorConfig


class FalseTargetDistractorEngine:
    """Generates false optical targets / distractors on sensor frames.

    Parameters:
        config: DistractorConfig dataclass.
        rng: Deterministic NumPy Random Generator stream.
        sensor_width: Sensor image width in pixels (default 640).
        sensor_height: Sensor image height in pixels (default 480).
    """

    def __init__(
        self,
        config: DistractorConfig,
        rng: np.random.Generator,
        sensor_width: int = 640,
        sensor_height: int = 480,
    ) -> None:
        self._config = config
        self._rng = rng
        self._w = sensor_width
        self._h = sensor_height

        # Initialize distractor positions and velocities
        self._positions: List[Tuple[float, float]] = []
        self._velocities: List[Tuple[float, float]] = []
        self._initialize_distractors()

    def _initialize_distractors(self) -> None:
        if not self._config.enabled or self._config.count < 1:
            return

        count = self._config.count
        margin = 50.0
        for _ in range(count):
            # Place distractors deterministically within sensor bounds
            x = float(self._rng.uniform(margin, self._w - margin))
            y = float(self._rng.uniform(margin, self._h - margin))
            self._positions.append((x, y))

            if self._config.movement_model == "linear":
                angle = float(self._rng.uniform(0.0, 2.0 * math.pi))
                speed = self._config.speed_px_s
                vx = speed * math.cos(angle)
                vy = speed * math.sin(angle)
            else:
                vx, vy = 0.0, 0.0
            self._velocities.append((vx, vy))

    def step(self, sim_dt: float) -> None:
        """Advance distractor positions by sim_dt."""
        if not self._config.enabled or not self._positions:
            return

        updated_pos = []
        for (x, y), (vx, vy) in zip(self._positions, self._velocities):
            nx = x + vx * sim_dt
            ny = y + vy * sim_dt

            # Bounce off image boundaries
            if nx < 30.0 or nx > self._w - 30.0:
                vx = -vx
                nx = max(30.0, min(self._w - 30.0, nx))
            if ny < 30.0 or ny > self._h - 30.0:
                vy = -vy
                ny = max(30.0, min(self._h - 30.0, ny))

            updated_pos.append((nx, ny))

        self._positions = updated_pos

    def apply(self, frame: np.ndarray, sim_dt: float = 0.033) -> Tuple[np.ndarray, int]:
        """Rasterize distractor shapes into sensor frame.

        Args:
            frame: 2D uint8 sensor image (640×480).
            sim_dt: Simulation timestep in seconds.

        Returns:
            Tuple of (frame_with_distractors, active_distractor_count).
        """
        if not self._config.enabled or not self._positions:
            return frame.copy(), 0

        self.step(sim_dt)
        out = frame.copy()
        h, w = out.shape[:2]
        intensity = float(self._config.intensity)
        d_type = self._config.type.lower()

        for px, py in self._positions:
            ix, iy = int(round(px)), int(round(py))

            if d_type == "small_spot":
                # Compact Gaussian spot (sigma = 1.5 px)
                radius = 6
                r1, r2 = max(0, iy - radius), min(h, iy + radius + 1)
                c1, c2 = max(0, ix - radius), min(w, ix + radius + 1)
                cols, rows = np.meshgrid(np.arange(c1, c2), np.arange(r1, r2))
                r2_dist = (cols - px) ** 2 + (rows - py) ** 2
                spot = intensity * np.exp(-r2_dist / (2.0 * 1.5 ** 2))
                out[r1:r2, c1:c2] = np.clip(np.maximum(out[r1:r2, c1:c2], spot), 0, 255).astype(np.uint8)

            elif d_type == "large_blob":
                # Broad spatial optical flare (sigma = 8.0 px)
                radius = 25
                r1, r2 = max(0, iy - radius), min(h, iy + radius + 1)
                c1, c2 = max(0, ix - radius), min(w, ix + radius + 1)
                cols, rows = np.meshgrid(np.arange(c1, c2), np.arange(r1, r2))
                r2_dist = (cols - px) ** 2 + (rows - py) ** 2
                blob = intensity * np.exp(-r2_dist / (2.0 * 8.0 ** 2))
                out[r1:r2, c1:c2] = np.clip(np.maximum(out[r1:r2, c1:c2], blob), 0, 255).astype(np.uint8)

            elif d_type == "reflection_like":
                # Linear glare streak (length = 30 px)
                r1, r2 = max(0, iy - 2), min(h, iy + 3)
                c1, c2 = max(0, ix - 15), min(w, ix + 16)
                out[r1:r2, c1:c2] = np.clip(out[r1:r2, c1:c2].astype(np.float64) + intensity * 0.7, 0, 255).astype(np.uint8)

            elif d_type == "noise_cluster":
                # Dense 5x5 regional hot pixels
                r1, r2 = max(0, iy - 2), min(h, iy + 3)
                c1, c2 = max(0, ix - 2), min(w, ix + 3)
                cluster = (self._rng.uniform(0.6, 1.0, size=(r2 - r1, c2 - c1)) * intensity).astype(np.uint8)
                out[r1:r2, c1:c2] = np.maximum(out[r1:r2, c1:c2], cluster)

            else:  # multiple_spots / default
                radius = 5
                r1, r2 = max(0, iy - radius), min(h, iy + radius + 1)
                c1, c2 = max(0, ix - radius), min(w, ix + radius + 1)
                cols, rows = np.meshgrid(np.arange(c1, c2), np.arange(r1, r2))
                r2_dist = (cols - px) ** 2 + (rows - py) ** 2
                spot = intensity * np.exp(-r2_dist / (2.0 * 2.0 ** 2))
                out[r1:r2, c1:c2] = np.clip(np.maximum(out[r1:r2, c1:c2], spot), 0, 255).astype(np.uint8)

        return out, len(self._positions)
