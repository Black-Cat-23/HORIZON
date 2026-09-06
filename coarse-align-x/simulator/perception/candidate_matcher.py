"""
HORIZON Perception Candidate Matching Engine
=====================================================
Phase 8 spatial overlap (IoU) and subpixel centroid distance candidate matcher.
Matches classical candidates with neural detector proposals without ground-truth information.

Strict Invariant: Zero ground-truth leakage.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import math
from typing import List, Optional, Tuple, Dict, Any

from simulator.perception.hybrid_candidate import CandidateSource, UnifiedCandidate


class MatchState(str, Enum):
    """Candidate match status classification."""
    MATCHED = "MATCHED"
    CLASSICAL_ONLY = "CLASSICAL_ONLY"
    NEURAL_ONLY = "NEURAL_ONLY"


def compute_iou(
    bbox_a: Tuple[int, int, int, int], bbox_b: Tuple[int, int, int, int]
) -> float:
    """Compute Intersection over Union (IoU) between two bounding boxes (x, y, w, h).

    Returns:
        float IoU score in range [0.0, 1.0].
    """
    xa1, ya1, wa, ha = bbox_a
    xa2, ya2 = xa1 + wa, ya1 + ha

    xb1, yb1, wb, hb = bbox_b
    xb2, yb2 = xb1 + wb, yb1 + hb

    # Intersection rectangle coordinates
    xi1 = max(xa1, xb1)
    yi1 = max(ya1, yb1)
    xi2 = min(xa2, xb2)
    yi2 = min(ya2, yb2)

    inter_width = max(0, xi2 - xi1)
    inter_height = max(0, yi2 - yi1)
    inter_area = float(inter_width * inter_height)

    area_a = float(wa * ha)
    area_b = float(wb * hb)
    union_area = area_a + area_b - inter_area

    if union_area <= 0.0:
        return 0.0

    return float(np_clip(inter_area / union_area, 0.0, 1.0))


def compute_centroid_distance(
    c_a: Tuple[float, float], c_b: Tuple[float, float]
) -> float:
    """Compute Euclidean distance between two centroids (u, v)."""
    return math.hypot(c_a[0] - c_b[0], c_a[1] - c_b[1])


def np_clip(val: float, low: float, high: float) -> float:
    return max(low, min(high, val))


@dataclass(frozen=True)
class MatchedPair:
    """Container for a matched classical-neural candidate pair."""
    classical: UnifiedCandidate
    neural: UnifiedCandidate
    iou: float
    centroid_distance: float
    fused_candidate: UnifiedCandidate


class CandidateMatcher:
    """Matches Classical and Neural proposals based on spatial overlap and distance.

    Parameters:
        max_centroid_distance_px: Maximum allowed centroid distance in pixels for matching.
        min_iou_threshold: Minimum IoU for bounding box matching if IoU available.
    """

    def __init__(
        self,
        max_centroid_distance_px: float = 25.0,
        min_iou_threshold: float = 0.10,
    ) -> None:
        self.max_distance = max_centroid_distance_px
        self.min_iou = min_iou_threshold

    def match_candidates(
        self,
        classical_candidates: List[UnifiedCandidate],
        neural_candidates: List[UnifiedCandidate],
    ) -> Tuple[List[MatchedPair], List[UnifiedCandidate], List[UnifiedCandidate]]:
        """Match lists of classical and neural candidates.

        Returns:
            Tuple of (matched_pairs, unmatched_classical, unmatched_neural)
        """
        matched_pairs: List[MatchedPair] = []
        unmatched_classical: List[UnifiedCandidate] = list(classical_candidates)
        unmatched_neural: List[UnifiedCandidate] = list(neural_candidates)

        if not classical_candidates or not neural_candidates:
            return matched_pairs, unmatched_classical, unmatched_neural

        used_neural_indices = set()
        used_classical_indices = set()

        # Score pairs based on combined distance and IoU metric
        candidate_pairs = []
        for i, c_cand in enumerate(classical_candidates):
            for j, n_cand in enumerate(neural_candidates):
                dist = compute_centroid_distance(c_cand.centroid, n_cand.centroid)
                iou = compute_iou(c_cand.bbox, n_cand.bbox)

                # Match criteria: centroid distance <= max_distance OR IoU >= min_iou
                if dist <= self.max_distance or iou >= self.min_iou:
                    # Preference score: higher IoU and lower distance
                    match_score = (1.0 - min(dist / max(self.max_distance, 1.0), 1.0)) * 0.6 + iou * 0.4
                    candidate_pairs.append((match_score, i, j, dist, iou))

        # Greedy match sorting by match_score descending
        candidate_pairs.sort(key=lambda x: x[0], reverse=True)

        for match_score, i, j, dist, iou in candidate_pairs:
            if i in used_classical_indices or j in used_neural_indices:
                continue

            used_classical_indices.add(i)
            used_neural_indices.add(j)

            c_cand = classical_candidates[i]
            n_cand = neural_candidates[j]

            # Merge features into unified BOTH candidate
            fused_candidate = UnifiedCandidate(
                candidate_id=f"H_M_{c_cand.candidate_id}_{n_cand.candidate_id}",
                centroid_x=c_cand.centroid_x,  # Refined optical centroid takes priority
                centroid_y=c_cand.centroid_y,
                bbox_x=n_cand.bbox_x,          # Neural bbox provides object extents
                bbox_y=n_cand.bbox_y,
                bbox_width=n_cand.bbox_width,
                bbox_height=n_cand.bbox_height,
                area=c_cand.area,
                peak_intensity=c_cand.peak_intensity,
                mean_intensity=c_cand.mean_intensity,
                background_estimate=c_cand.background_estimate,
                local_contrast=c_cand.local_contrast,
                classical_confidence=c_cand.classical_confidence,
                neural_confidence=n_cand.neural_confidence,
                source=CandidateSource.BOTH,
                valid=True,
                raw_classical_candidate=c_cand.raw_classical_candidate,
                raw_neural_bbox=n_cand.raw_neural_bbox,
                contour=c_cand.contour,
            )

            matched_pairs.append(
                MatchedPair(
                    classical=c_cand,
                    neural=n_cand,
                    iou=iou,
                    centroid_distance=dist,
                    fused_candidate=fused_candidate,
                )
            )

        # Remaining unmatched candidates
        rem_classical = [
            c for i, c in enumerate(classical_candidates) if i not in used_classical_indices
        ]
        rem_neural = [
            n for j, n in enumerate(neural_candidates) if j not in used_neural_indices
        ]

        return matched_pairs, rem_classical, rem_neural
