"""
HORIZON Schema-Agnostic PCHIP Spline-Interpolated Ground-Truth CSV Aligner
===========================================================================
Parses arbitrary ground-truth CSV trajectories and performs 1D PCHIP cubic spline
time interpolation to align ground-truth positions/velocities with sensor frame timestamps.

Supported Column Schemas:
  - 'u', 'v' / 'x', 'y' / 'px', 'py' / 'true_u', 'true_v' / 'true_x', 'true_y' / 'centroid_x', 'centroid_y'
  - 'timestamp', 'time', 't_s', 't', 'frame'

Strict Invariant: Ground truth is used STRICTLY for post-hoc metric evaluation.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union
import numpy as np

try:
    from scipy.interpolate import PchipInterpolator
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False


@dataclass(frozen=True)
class GroundTruthSample:
    """Aligned ground-truth state sample."""
    timestamp: float
    u: float
    v: float
    vx: float
    vy: float


class GroundTruthCSVAligner:
    """Parses ground-truth CSV files and performs PCHIP spline interpolation to arbitrary sensor timestamps."""

    def __init__(self, csv_path: Optional[Union[str, Path]] = None) -> None:
        self.timestamps: np.ndarray = np.array([], dtype=np.float64)
        self.u_coords: np.ndarray = np.array([], dtype=np.float64)
        self.v_coords: np.ndarray = np.array([], dtype=np.float64)
        self.vx_coords: np.ndarray = np.array([], dtype=np.float64)
        self.vy_coords: np.ndarray = np.array([], dtype=np.float64)
        self.is_loaded = False
        self._u_spline = None
        self._v_spline = None
        self._du_spline = None
        self._dv_spline = None

        if csv_path is not None:
            self.load_csv(csv_path)

    def load_csv(self, csv_path: Union[str, Path]) -> bool:
        """Parse CSV file and populate internal coordinate arrays and splines."""
        path = Path(csv_path)
        if not path.exists():
            raise FileNotFoundError(f"Ground-truth CSV file not found: {path}")

        ts_list: List[float] = []
        u_list: List[float] = []
        v_list: List[float] = []

        with open(path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            if not reader.fieldnames:
                return False

            ts_col = next((h for h in reader.fieldnames if h.strip().lower() in ("timestamp", "time", "t_s", "t", "time_s", "timestamp_s", "time_seconds")), None)
            u_col = next((h for h in reader.fieldnames if h.strip().lower() in ("u", "x", "px", "true_u", "true_x", "centroid_x", "ground_truth_u", "gt_u")), None)
            v_col = next((h for h in reader.fieldnames if h.strip().lower() in ("v", "y", "py", "true_v", "true_y", "centroid_y", "ground_truth_v", "gt_v")), None)

            if u_col is None or v_col is None:
                raise ValueError(f"Could not identify position columns in CSV header: {reader.fieldnames}")

            idx = 0
            for row in reader:
                try:
                    u_val = float(row[u_col])
                    v_val = float(row[v_col])
                    if ts_col is not None and row[ts_col]:
                        t_val = float(row[ts_col])
                    else:
                        t_val = float(idx * 0.03333333333333333)  # Default 30 FPS fallback

                    ts_list.append(t_val)
                    u_list.append(u_val)
                    v_list.append(v_val)
                    idx += 1
                except (ValueError, KeyError):
                    continue

        if len(ts_list) < 2:
            return False

        self.timestamps = np.array(ts_list, dtype=np.float64)
        self.u_coords = np.array(u_list, dtype=np.float64)
        self.v_coords = np.array(v_list, dtype=np.float64)

        # Build PCHIP Splines for smooth derivatives
        if HAS_SCIPY and len(self.timestamps) >= 3:
            # Ensure strictly increasing timestamps for PCHIP
            unique_mask = np.diff(self.timestamps, prepend=self.timestamps[0] - 1.0) > 1e-9
            t_clean = self.timestamps[unique_mask]
            u_clean = self.u_coords[unique_mask]
            v_clean = self.v_coords[unique_mask]

            if len(t_clean) >= 3:
                self._u_spline = PchipInterpolator(t_clean, u_clean)
                self._v_spline = PchipInterpolator(t_clean, v_clean)
                self._du_spline = self._u_spline.derivative()
                self._dv_spline = self._v_spline.derivative()

        # Fallback numerical velocity derivatives
        dt = np.diff(self.timestamps)
        dt = np.where(dt <= 0, 1e-4, dt)
        du = np.diff(self.u_coords) / dt
        dv = np.diff(self.v_coords) / dt

        self.vx_coords = np.append(du, du[-1])
        self.vy_coords = np.append(dv, dv[-1])

        self.is_loaded = True
        return True

    def get_aligned_sample(self, timestamp: float) -> GroundTruthSample:
        """Interpolate ground-truth position and velocity at specific timestamp using PCHIP Splines."""
        if not self.is_loaded or len(self.timestamps) == 0:
            return GroundTruthSample(timestamp=float(timestamp), u=0.0, v=0.0, vx=0.0, vy=0.0)

        t_val = float(timestamp)

        if self._u_spline is not None and self._v_spline is not None:
            # Clamp to range to avoid extrapolation error
            t_clamped = float(np.clip(t_val, self.timestamps[0], self.timestamps[-1]))
            u_interp = float(self._u_spline(t_clamped))
            v_interp = float(self._v_spline(t_clamped))
            vx_interp = float(self._du_spline(t_clamped))
            vy_interp = float(self._dv_spline(t_clamped))
        else:
            # Linear fallback
            u_interp = float(np.interp(t_val, self.timestamps, self.u_coords))
            v_interp = float(np.interp(t_val, self.timestamps, self.v_coords))
            vx_interp = float(np.interp(t_val, self.timestamps, self.vx_coords))
            vy_interp = float(np.interp(t_val, self.timestamps, self.vy_coords))

        return GroundTruthSample(
            timestamp=t_val,
            u=u_interp,
            v=v_interp,
            vx=vx_interp,
            vy=vy_interp,
        )
