import numpy as np
from typing import Tuple, Dict, Any
from simulator.core.simulation import SimulationEngine
from .frame_source import FrameSource, VideoMetadata

class SyntheticFrameSource(FrameSource):
    """Adapter that presents the deterministic simulation as a FrameSource.

    It uses SimulationEngine to step the world and returns the disturbed
    camera observation (480×640 uint8 grayscale) on each read().
    """

    def __init__(self, config_path: str = None, yaml_override: str = None):
        # Load config (same as main CLI) and create engine
        from simulator.core.config import load_config, AppConfig
        if yaml_override:
            cfg = load_config(yaml_override)
        elif config_path:
            cfg = load_config(config_path)
        else:
            # default config
            cfg = AppConfig()
        self._engine = SimulationEngine(cfg)
        self._engine.initialize()
        self._frame_idx = 0
        self._metadata = VideoMetadata(
            source_type="SYNTHETIC",
            native_width=cfg.world.width,
            native_height=cfg.world.height,
            fps=cfg.simulation.frequency_hz,
            total_frames=cfg.simulation.total_frames,
            duration_seconds=cfg.simulation.duration_seconds,
        )
        self._open = False

    def open(self) -> bool:
        self._engine.initialize()
        self._open = True
        self._frame_idx = 0
        return True

    def read(self) -> Tuple[bool, Any, float, int, Dict[str, Any]]:
        if not self._open:
            raise RuntimeError("SyntheticFrameSource not opened")
        # Step simulation one frame and retrieve disturbed camera frame
        frame = self._engine.step()
        # Timestamp based on simulation time
        timestamp = self._engine.clock.current_time
        # Metadata per frame (ground truth can be fetched from recorder separately)
        metadata = {
            "frame_index": self._frame_idx,
            "timestamp": timestamp,
            "ground_truth": self._engine.recorder.get_current_record(),
        }
        self._frame_idx += 1
        return True, frame, timestamp, self._frame_idx - 1, metadata

    def seek(self, frame_index: int) -> bool:
        # Reset engine and step forward to desired frame
        self._engine.reset()
        self._frame_idx = 0
        while self._frame_idx < frame_index:
            self._engine.step()
            self._frame_idx += 1
        return True

    def reset(self) -> None:
        self._engine.reset()
        self._frame_idx = 0

    def close(self) -> None:
        self._open = False

    def get_metadata(self) -> VideoMetadata:
        return self._metadata

    def is_open(self) -> bool:
        return self._open

    def get_total_frames(self) -> int:
        return self._metadata.total_frames or -1

    def get_fps(self) -> float:
        return self._metadata.fps or 0.0

