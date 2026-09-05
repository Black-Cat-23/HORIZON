"""
HORIZON World Renderer
==============================
Generates full-resolution 2D monochrome virtual environment frames (2000×2000 uint8)
containing the background and rendered optical beacon.
"""

from __future__ import annotations

import cv2
import numpy as np
from simulator.world.beacon import Beacon


class WorldRenderer:
    """Monochrome world environment renderer.

    Parameters:
        width: World width in pixels (default 2000).
        height: World height in pixels (default 2000).
        background_level: Ambient background intensity (0–255, default 0).
    """

    def __init__(
        self,
        width: int = 2000,
        height: int = 2000,
        background_level: int = 0,
    ) -> None:
        if width <= 0 or height <= 0:
            raise ValueError(f"Dimensions must be positive: {width}x{height}")
        if not (0 <= background_level <= 255):
            raise ValueError(f"background_level must be 0–255, got {background_level}")

        self._width = int(width)
        self._height = int(height)
        self._bg_level = int(background_level)

        # Pre-allocate base background buffer
        self._base_frame = np.full(
            (self._height, self._width), self._bg_level, dtype=np.uint8
        )

    @property
    def width(self) -> int:
        return self._width

    @property
    def height(self) -> int:
        return self._height

    @property
    def background_level(self) -> int:
        return self._bg_level

    def render(
        self,
        beacon: Beacon,
        target_x: float,
        target_y: float,
        visible: bool = True,
        path_history: list[tuple[float, float]] | None = None,
    ) -> np.ndarray:
        """Render a full simulation frame.

        Args:
            beacon: Optical beacon instance to render.
            target_x: Continuous X position of target.
            target_y: Continuous Y position of target.
            visible: Whether the beacon is visible/emitting.
            path_history: Optional list of past (x, y) coordinates to render
                          as a faint debug trajectory overlay.

        Returns:
            A 2D NumPy array of shape (height, width), dtype uint8.
        """
        # Fast copy of base background
        frame = self._base_frame.copy()

        # Render optional debug path overlay
        if path_history and len(path_history) > 1:
            pts = np.array(path_history, dtype=np.int32).reshape((-1, 1, 2))
            # Draw path line with faint gray intensity (40)
            cv2.polylines(frame, [pts], isClosed=False, color=40, thickness=1, lineType=cv2.LINE_AA)

        # Render target beacon if visible
        if visible:
            beacon.render_into(frame, target_x, target_y, background_level=self._bg_level)

        return frame
