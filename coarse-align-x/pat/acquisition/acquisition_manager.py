"""
Acquisition Confirmation Manager.
HORIZON Phase 6
"""

from typing import Optional, Tuple
import math
from ..thresholds import PATThresholds


class AcquisitionManager:
    """
    Manages candidate confirmation criteria before transitioning from ACQUIRE to TRACK.
    Requires N valid consecutive detections with acceptable confidence, innovation,
    and spatial consistency (centroid displacement <= max_acquisition_drift_px).
    """

    def __init__(self, thresholds: Optional[PATThresholds] = None, max_acquisition_drift_px: float = 30.0):
        self.thresholds = thresholds or PATThresholds()
        self.max_acquisition_drift_px = max_acquisition_drift_px
        self.consecutive_valid_frames = 0
        self.candidate_active = False
        self.last_candidate_pos: Optional[Tuple[float, float]] = None

    def reset(self) -> None:
        self.consecutive_valid_frames = 0
        self.candidate_active = False
        self.last_candidate_pos = None

    def process_frame(
        self,
        detection_valid: bool,
        confidence: float,
        mahalanobis_distance: float,
        candidate_pos: Optional[Tuple[float, float]] = None,
    ) -> bool:
        """
        Processes a frame detection result and updates acquisition status.
        
        Returns:
            True if target acquisition is confirmed (ready for TRACK state), False otherwise.
        """
        if not detection_valid or confidence < self.thresholds.min_acquisition_confidence:
            self.reset()
            return False

        if mahalanobis_distance > self.thresholds.max_mahalanobis_gate:
            self.reset()
            return False

        # Enforce spatial consistency across candidate confirmation frames
        if candidate_pos is not None and self.last_candidate_pos is not None:
            dx = candidate_pos[0] - self.last_candidate_pos[0]
            dy = candidate_pos[1] - self.last_candidate_pos[1]
            dist = math.hypot(dx, dy)
            if dist > self.max_acquisition_drift_px:
                # Candidate jumped across frame (random noise spike) - reset confirmation!
                self.reset()
                self.candidate_active = True
                self.consecutive_valid_frames = 1
                self.last_candidate_pos = candidate_pos
                return False

        self.candidate_active = True
        self.consecutive_valid_frames += 1
        if candidate_pos is not None:
            self.last_candidate_pos = candidate_pos

        return self.consecutive_valid_frames >= self.thresholds.acquire_required_frames
