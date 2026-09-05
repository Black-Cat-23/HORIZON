"""
HORIZON Ground Truth Recorder
=====================================
Records exact ground-truth target kinematics and simulation metadata per frame.
Supports export to CSV and JSON formats.

Strict constraint: Ground truth only. No estimated or detector fields.
"""

from __future__ import annotations

import csv
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import List, Optional
from simulator.world.state import TargetState


@dataclass(frozen=True)
class GroundTruthRecord:
    """Per-frame ground truth record."""
    experiment_id: str
    seed: int
    frame: int
    timestamp: float
    target_id: int
    target_x: float
    target_y: float
    target_vx: float
    target_vy: float
    target_ax: float
    target_ay: float
    target_visible: bool
    trajectory_type: str
    world_width: int
    world_height: int
    target_size_px: float
    # Phase 2: Camera and projection ground truth
    camera_pan_deg: float = 0.0
    camera_tilt_deg: float = 0.0
    camera_pan_rate_deg_s: float = 0.0
    camera_tilt_rate_deg_s: float = 0.0
    target_theta_x_deg: float = 0.0
    target_theta_y_deg: float = 0.0
    target_pixel_u: float = 0.0
    target_pixel_v: float = 0.0
    target_in_fov: bool = False
    # Phase 3: Disturbance telemetry
    disturbance_enabled: bool = False
    salt_pepper_enabled: bool = False
    salt_pepper_probability: float = 0.0
    gaussian_enabled: bool = False
    gaussian_sigma: float = 0.0
    poisson_enabled: bool = False
    poisson_parameter: float = 0.0
    camera_jitter_enabled: bool = False
    camera_jitter_x: float = 0.0
    camera_jitter_y: float = 0.0
    platform_motion_enabled: bool = False
    platform_model: str = "linear"
    platform_offset_x: float = 0.0
    platform_offset_y: float = 0.0
    platform_velocity_x: float = 0.0
    platform_velocity_y: float = 0.0
    atmosphere_enabled: bool = False
    atmosphere_condition: str = "clear"
    contrast_factor: float = 1.0
    brightness_factor: float = 0.0


class GroundTruthRecorder:
    """Collects and exports per-frame ground truth records.

    Parameters:
        experiment_id: Identifier for the experiment/run.
        seed: Simulation random seed.
        trajectory_type: Name of active trajectory.
        world_width: Simulation world width in pixels.
        world_height: Simulation world height in pixels.
        target_size_px: Beacon dimension in pixels.
    """

    def __init__(
        self,
        experiment_id: str,
        seed: int,
        trajectory_type: str,
        world_width: int = 2000,
        world_height: int = 2000,
        target_size_px: float = 10.0,
    ) -> None:
        self._experiment_id = experiment_id
        self._seed = seed
        self._trajectory_type = trajectory_type
        self._world_width = world_width
        self._world_height = world_height
        self._target_size_px = target_size_px
        self._records: List[GroundTruthRecord] = []

    @property
    def record_count(self) -> int:
        return len(self._records)

    @property
    def records(self) -> List[GroundTruthRecord]:
        return list(self._records)

    def record_frame(
        self,
        frame_index: int,
        state: TargetState,
        camera_pan_deg: float = 0.0,
        camera_tilt_deg: float = 0.0,
        camera_pan_rate_deg_s: float = 0.0,
        camera_tilt_rate_deg_s: float = 0.0,
        target_theta_x_deg: float = 0.0,
        target_theta_y_deg: float = 0.0,
        target_pixel_u: float = 0.0,
        target_pixel_v: float = 0.0,
        target_in_fov: bool = False,
        disturbance_telemetry: Optional[object] = None,
    ) -> None:
        """Record ground truth for a single simulation frame."""
        # Disturbance fields extraction
        d_enabled = getattr(disturbance_telemetry, "disturbance_enabled", False)
        sp_enabled = getattr(disturbance_telemetry, "salt_pepper_enabled", False)
        sp_prob = getattr(disturbance_telemetry, "salt_pepper_probability", 0.0)
        g_enabled = getattr(disturbance_telemetry, "gaussian_enabled", False)
        g_sigma = getattr(disturbance_telemetry, "gaussian_sigma", 0.0)
        p_enabled = getattr(disturbance_telemetry, "poisson_enabled", False)
        p_param = getattr(disturbance_telemetry, "poisson_parameter", 0.0)
        j_enabled = getattr(disturbance_telemetry, "camera_jitter_enabled", False)
        jx = getattr(disturbance_telemetry, "camera_jitter_x", 0.0)
        jy = getattr(disturbance_telemetry, "camera_jitter_y", 0.0)
        plat_enabled = getattr(disturbance_telemetry, "platform_motion_enabled", False)
        plat_model = getattr(disturbance_telemetry, "platform_model", "linear")
        plat_ox = getattr(disturbance_telemetry, "platform_offset_x", 0.0)
        plat_oy = getattr(disturbance_telemetry, "platform_offset_y", 0.0)
        plat_vx = getattr(disturbance_telemetry, "platform_velocity_x", 0.0)
        plat_vy = getattr(disturbance_telemetry, "platform_velocity_y", 0.0)
        atmos_enabled = getattr(disturbance_telemetry, "atmosphere_enabled", False)
        atmos_cond = getattr(disturbance_telemetry, "atmosphere_condition", "clear")
        contrast_f = getattr(disturbance_telemetry, "contrast_factor", 1.0)
        bright_f = getattr(disturbance_telemetry, "brightness_factor", 0.0)

        rec = GroundTruthRecord(
            experiment_id=self._experiment_id,
            seed=self._seed,
            frame=frame_index,
            timestamp=round(state.timestamp, 6),
            target_id=state.target_id,
            target_x=round(state.x, 6),
            target_y=round(state.y, 6),
            target_vx=round(state.vx, 6),
            target_vy=round(state.vy, 6),
            target_ax=round(state.ax, 6),
            target_ay=round(state.ay, 6),
            target_visible=state.visible,
            trajectory_type=self._trajectory_type,
            world_width=self._world_width,
            world_height=self._world_height,
            target_size_px=self._target_size_px,
            camera_pan_deg=round(camera_pan_deg, 6),
            camera_tilt_deg=round(camera_tilt_deg, 6),
            camera_pan_rate_deg_s=round(camera_pan_rate_deg_s, 6),
            camera_tilt_rate_deg_s=round(camera_tilt_rate_deg_s, 6),
            target_theta_x_deg=round(target_theta_x_deg, 6),
            target_theta_y_deg=round(target_theta_y_deg, 6),
            target_pixel_u=round(target_pixel_u, 6),
            target_pixel_v=round(target_pixel_v, 6),
            target_in_fov=target_in_fov,
            disturbance_enabled=d_enabled,
            salt_pepper_enabled=sp_enabled,
            salt_pepper_probability=round(sp_prob, 6),
            gaussian_enabled=g_enabled,
            gaussian_sigma=round(g_sigma, 6),
            poisson_enabled=p_enabled,
            poisson_parameter=round(p_param, 6),
            camera_jitter_enabled=j_enabled,
            camera_jitter_x=round(jx, 6),
            camera_jitter_y=round(jy, 6),
            platform_motion_enabled=plat_enabled,
            platform_model=plat_model,
            platform_offset_x=round(plat_ox, 6),
            platform_offset_y=round(plat_oy, 6),
            platform_velocity_x=round(plat_vx, 6),
            platform_velocity_y=round(plat_vy, 6),
            atmosphere_enabled=atmos_enabled,
            atmosphere_condition=atmos_cond,
            contrast_factor=round(contrast_f, 6),
            brightness_factor=round(bright_f, 6),
        )
        self._records.append(rec)

    def export_csv(self, filepath: Path | str) -> Path:
        """Export all recorded frames to CSV format."""
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)

        if not self._records:
            fieldnames = [f.name for f in GroundTruthRecord.__dataclass_fields__.values()]
        else:
            fieldnames = list(asdict(self._records[0]).keys())

        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for r in self._records:
                writer.writerow(asdict(r))

        return path

    def export_json(self, filepath: Path | str) -> Path:
        """Export all recorded frames and metadata to JSON format."""
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "metadata": {
                "experiment_id": self._experiment_id,
                "seed": self._seed,
                "trajectory_type": self._trajectory_type,
                "world_width": self._world_width,
                "world_height": self._world_height,
                "target_size_px": self._target_size_px,
                "total_frames": len(self._records),
            },
            "records": [asdict(r) for r in self._records],
        }

        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        return path

    def clear(self) -> None:
        """Clear all stored records."""
        self._records.clear()
