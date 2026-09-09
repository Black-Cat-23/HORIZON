"""
Failure Timeline Module
======================
Reconstructs per-frame event sequences for failed trials.
"""

from __future__ import annotations
from typing import Any, Dict, List


class FailureTimeline:
    """Reconstructs frame-by-frame event timeline for diagnostic analysis."""

    @staticmethod
    def reconstruct_timeline(telemetry_stream: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        events = []
        for frame_data in telemetry_stream:
            t = frame_data.get("timestamp", 0.0)
            mode = frame_data.get("pat_mode", "")
            err = frame_data.get("tracking_error_px", 0.0)
            if mode in ["LOST", "REACQUIRE"] or err > 50.0:
                events.append({
                    "timestamp": t,
                    "event": f"Degraded tracking (mode={mode}, err={err:.2f}px)",
                })
        return events
