"""
Coarse Raster Search Strategy.
HORIZON Phase 6
"""

from typing import Tuple, List
import math
from .base import SearchStrategy


class RasterSearchStrategy(SearchStrategy):
    """
    Coarse raster scan search strategy across camera coordinate space.
    Generates actual camera rate commands:
    left -> right -> row step -> right -> left -> row step...
    """

    def __init__(
        self,
        fov_pan_deg: float = 4.0,
        fov_tilt_deg: float = 3.0,
        scan_width_deg: float = 6.0,
        scan_height_deg: float = 4.5,
        scan_speed_deg_s: float = 2.0,
        overlap_fraction: float = 0.3,
    ):
        self.scan_width_deg = scan_width_deg
        self.scan_height_deg = scan_height_deg
        self.scan_speed_deg_s = scan_speed_deg_s
        self.row_step_deg = fov_tilt_deg * (1.0 - overlap_fraction)
        
        self.center_pan_deg = 0.0
        self.center_tilt_deg = 0.0
        
        self._current_row = 0
        self._row_progress_deg = 0.0
        self._direction = 1.0  # +1 = moving right, -1 = moving left
        self._stepping_row = False
        self._step_progress_deg = 0.0
        self._completed = False
        
        self._num_rows = max(1, math.ceil(self.scan_height_deg / self.row_step_deg))

    def reset(self, center_pan_deg: float = 0.0, center_tilt_deg: float = 0.0) -> None:
        self.center_pan_deg = center_pan_deg
        self.center_tilt_deg = center_tilt_deg
        self._current_row = 0
        self._row_progress_deg = -self.scan_width_deg / 2.0
        self._direction = 1.0
        self._stepping_row = False
        self._step_progress_deg = 0.0
        self._completed = False

    def is_complete(self) -> bool:
        return self._completed

    def next_command(self, dt: float, current_pan_deg: float, current_tilt_deg: float) -> Tuple[float, float]:
        if self._completed or dt <= 0.0:
            return (0.0, 0.0)

        # Target relative position in search grid
        min_pan = self.center_pan_deg - (self.scan_width_deg / 2.0)
        max_pan = self.center_pan_deg + (self.scan_width_deg / 2.0)
        start_tilt = self.center_tilt_deg - (self.scan_height_deg / 2.0)
        
        target_tilt = start_tilt + (self._current_row * self.row_step_deg)

        if self._stepping_row:
            # Vertical step to next row
            tilt_diff = target_tilt - current_tilt_deg
            if abs(tilt_diff) < 0.01:
                self._stepping_row = False
                return (0.0, 0.0)
            
            tilt_rate = self.scan_speed_deg_s if tilt_diff > 0 else -self.scan_speed_deg_s
            return (0.0, tilt_rate)

        # Horizontal scan along current row
        if self._direction > 0:
            target_pan = max_pan
            if current_pan_deg >= max_pan - 0.05:
                # Reach end of right sweep -> step row
                self._direction = -1.0
                self._current_row += 1
                if self._current_row >= self._num_rows:
                    self._completed = True
                    return (0.0, 0.0)
                self._stepping_row = True
                return (0.0, 0.0)
            return (self.scan_speed_deg_s, 0.0)
        else:
            target_pan = min_pan
            if current_pan_deg <= min_pan + 0.05:
                # Reach end of left sweep -> step row
                self._direction = 1.0
                self._current_row += 1
                if self._current_row >= self._num_rows:
                    self._completed = True
                    return (0.0, 0.0)
                self._stepping_row = True
                return (0.0, 0.0)
            return (-self.scan_speed_deg_s, 0.0)

    def get_trajectory_history(self) -> List[Tuple[float, float]]:
        pts = []
        min_pan = self.center_pan_deg - (self.scan_width_deg / 2.0)
        max_pan = self.center_pan_deg + (self.scan_width_deg / 2.0)
        start_tilt = self.center_tilt_deg - (self.scan_height_deg / 2.0)
        
        dir_flag = 1.0
        for r in range(self._num_rows):
            row_tilt = start_tilt + (r * self.row_step_deg)
            if dir_flag > 0:
                pts.append((min_pan, row_tilt))
                pts.append((max_pan, row_tilt))
            else:
                pts.append((max_pan, row_tilt))
                pts.append((min_pan, row_tilt))
            dir_flag *= -1.0
        return pts
