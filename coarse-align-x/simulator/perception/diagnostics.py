"""
HORIZON Perception Diagnostics & Visualization Artifacts
===============================================================
Generates visual diagnostic representations of the perception pipeline stages:
  - Raw input frame
  - Denoised preprocessed frame
  - Binary threshold mask
  - Candidate regions overlay
  - Centroid crop ROI
  - Annotated result frame
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple
import cv2
import numpy as np

from simulator.perception.candidate import BeaconCandidate


@dataclass
class DetectionDiagnostics:
    """Diagnostic image artifacts collected during detection."""
    raw_frame: np.ndarray
    preprocessed_frame: np.ndarray
    threshold_mask: np.ndarray
    annotated_frame: np.ndarray
    roi_crop: Optional[np.ndarray] = None


def create_annotated_frame(
    frame: np.ndarray,
    candidates: List[BeaconCandidate],
    selected_candidate: Optional[BeaconCandidate],
    centroid: Optional[Tuple[float, float]],
) -> np.ndarray:
    """Render annotated RGB visualization of perception detections.

    - Non-selected candidates: yellow bounding boxes.
    - Selected candidate: green bounding box.
    - Subpixel centroid: red reticle crosshair.
    """
    # Convert grayscale to BGR for color overlays
    annotated = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)

    # Draw all candidates in yellow
    for cand in candidates:
        if cand is not selected_candidate:
            x, y, w, h = cand.bbox
            cv2.rectangle(annotated, (x, y), (x + w, y + h), (0, 215, 255), 1)

    # Draw selected candidate in bright green
    if selected_candidate is not None:
        x, y, w, h = selected_candidate.bbox
        cv2.rectangle(annotated, (x, y), (x + w, y + h), (0, 255, 0), 2)
        label = f"Beacon ({selected_candidate.score:.2f})"
        cv2.putText(
            annotated,
            label,
            (x, max(y - 5, 12)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.4,
            (0, 255, 0),
            1,
            cv2.LINE_AA,
        )

    # Draw subpixel centroid in bright red
    if centroid is not None:
        u, v = centroid
        iu, iv = int(round(u)), int(round(v))
        cv2.drawMarker(
            annotated,
            (iu, iv),
            (0, 0, 255),
            markerType=cv2.MARKER_CROSS,
            markerSize=14,
            thickness=1,
            line_type=cv2.LINE_AA,
        )

    return annotated


def export_diagnostics_to_disk(
    diag: DetectionDiagnostics, output_dir: Path | str, prefix: str = "detection"
) -> dict[str, Path]:
    """Export all diagnostic images to disk as PNG files."""
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    files = {
        "raw": out_path / f"{prefix}_01_raw.png",
        "preprocessed": out_path / f"{prefix}_02_preprocessed.png",
        "threshold": out_path / f"{prefix}_03_threshold.png",
        "annotated": out_path / f"{prefix}_04_annotated.png",
    }

    cv2.imwrite(str(files["raw"]), diag.raw_frame)
    cv2.imwrite(str(files["preprocessed"]), diag.preprocessed_frame)
    cv2.imwrite(str(files["threshold"]), diag.threshold_mask)
    cv2.imwrite(str(files["annotated"]), diag.annotated_frame)

    if diag.roi_crop is not None:
        roi_file = out_path / f"{prefix}_05_roi.png"
        cv2.imwrite(str(roi_file), diag.roi_crop)
        files["roi"] = roi_file

    return files
