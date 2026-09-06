"""
HORIZON Unified Perception Candidate Representation
==========================================================
Phase 8 unified candidate structure representing proposals from classical,
neural, or fused hybrid perception detectors.

Strict Invariant: Zero ground-truth access or leakage.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional, Tuple, Any
import numpy as np


class CandidateSource(str, Enum):
    """Source origin of a perception candidate."""
    CLASSICAL = "CLASSICAL"
    NEURAL = "NEURAL"
    BOTH = "BOTH"


@dataclass(frozen=True)
class UnifiedCandidate:
    """Unified representation of a beacon candidate region across classical and neural detectors.

    Fields:
        candidate_id: Unique string identifier for candidate tracking.
        centroid_x: Horizontal centroid coordinate in sensor pixels (u).
        centroid_y: Vertical centroid coordinate in sensor pixels (v).
        bbox_x: Bounding box top-left horizontal coordinate (x).
        bbox_y: Bounding box top-left vertical coordinate (y).
        bbox_width: Bounding box width (w).
        bbox_height: Bounding box height (h).
        area: Area of candidate region in square pixels.
        peak_intensity: Maximum pixel intensity inside candidate ROI.
        mean_intensity: Mean pixel intensity inside candidate ROI.
        background_estimate: Estimated local background floor.
        local_contrast: Contrast above surrounding background (peak - bg).
        classical_confidence: Raw confidence score from classical detector [0.0, 1.0] if present.
        neural_confidence: Raw confidence score from neural YOLOv8n model [0.0, 1.0] if present.
        source: CandidateSource enum (CLASSICAL, NEURAL, BOTH).
        valid: Boolean flag indicating if candidate passes validity gates.
        raw_classical_candidate: Reference to source classical candidate object if applicable.
        raw_neural_bbox: Reference to raw neural bounding box tuple if applicable.
        contour: Optional contour numpy array for classical candidates.
    """
    candidate_id: str
    centroid_x: float
    centroid_y: float
    bbox_x: int
    bbox_y: int
    bbox_width: int
    bbox_height: int
    area: float
    peak_intensity: Optional[float] = None
    mean_intensity: Optional[float] = None
    background_estimate: Optional[float] = None
    local_contrast: Optional[float] = None
    classical_confidence: Optional[float] = None
    neural_confidence: Optional[float] = None
    source: CandidateSource = CandidateSource.CLASSICAL
    valid: bool = True
    raw_classical_candidate: Optional[Any] = None
    raw_neural_bbox: Optional[Tuple[int, int, int, int]] = None
    contour: Optional[np.ndarray] = None

    @property
    def centroid(self) -> Tuple[float, float]:
        """Return (u, v) centroid tuple."""
        return (self.centroid_x, self.centroid_y)

    @property
    def bbox(self) -> Tuple[int, int, int, int]:
        """Return (x, y, w, h) bounding box tuple."""
        return (self.bbox_x, self.bbox_y, self.bbox_width, self.bbox_height)
