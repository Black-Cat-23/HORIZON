"""
HORIZON Phase 3B: External Video Authoritative Timebase & Pipeline Flow
========================================================================
Implements source-correct video timing where the external video's native
timebase is strictly authoritative.

Strict Invariants:
  - Source timestamp is authoritative (derived from container PTS / POS_MSEC or dynamic fallback).
  - UI render time, CPU execution time, and wall-clock speed are NEVER used as source-frame timestep.
  - For 30 FPS, dt = 1/30s is dynamically derived, never hard-coded.
  - Strict sequence per frame:
      video frame -> processing -> HYBRID -> estimator -> PAT -> controller output
  - Zero duplicate timestamps, zero silent duplication, zero hidden frame skipping.
  - Frame drops are explicitly detected, counted, and logged.
  - Full metrics: source FPS, processing FPS, frame ID, timestamp, dt, dropped frames,
                  decode latency, processing latency.
  - Zero modification to Virtual Camera timing.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
import logging
import time
from typing import Deque, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class VideoFrameTiming:
    """Authoritative timing and performance telemetry for a single video frame.

    Attributes:
        frame_id: Sequential 0-based frame index from source container.
        timestamp: Authoritative presentation timestamp in seconds.
        dt: True elapsed time in seconds since the previous frame (source timestep).
        source_fps: Nominal source frame rate (FPS).
        processing_fps: Real-time processing throughput frame rate (FPS).
        decode_latency_ms: Wall-clock duration taken to demux & decode the frame.
        processing_latency_ms: Wall-clock duration taken to execute pipeline.
        cumulative_dropped_frames: Total number of dropped frames detected so far.
        is_dropped: True if a gap in frame continuity was detected before this frame.
        dropped_count_step: Number of frames dropped immediately prior to this frame.
    """
    frame_id: int
    timestamp: float
    dt: float
    source_fps: float
    processing_fps: float
    decode_latency_ms: float
    processing_latency_ms: float
    cumulative_dropped_frames: int
    is_dropped: bool
    dropped_count_step: int = 0


class VideoTimebase:
    """Authoritative timebase manager for external video sensor streams.

    Enforces deterministic, source-correct temporal progression independent of
    UI rendering rates, display vsync, or operating system thread scheduling.
    """

    def __init__(self, source_fps: float = 30.0, total_frames: int = 0) -> None:
        self._source_fps = float(source_fps) if (source_fps > 0.0) else 30.0
        self._nominal_dt = 1.0 / self._source_fps
        self._total_frames = int(total_frames)

        # State tracking
        self._last_frame_id: Optional[int] = None
        self._last_timestamp: Optional[float] = None
        self._cumulative_dropped_frames: int = 0
        self._processed_frames_count: int = 0

        # Latency & throughput tracking
        self._decode_latencies: Deque[float] = deque(maxlen=60)
        self._proc_latencies: Deque[float] = deque(maxlen=60)
        self._proc_timestamps: Deque[float] = deque(maxlen=60)

        # Last computed timing
        self._last_timing: Optional[VideoFrameTiming] = None

    # --------------------------------------------------------------------------
    # Public Properties
    # --------------------------------------------------------------------------
    @property
    def source_fps(self) -> float:
        """Nominal source frame rate in frames per second."""
        return self._source_fps

    @property
    def nominal_dt(self) -> float:
        """Nominal timestep (1 / source_fps) in seconds."""
        return self._nominal_dt

    @property
    def cumulative_dropped_frames(self) -> int:
        """Total number of detected dropped frames since reset."""
        return self._cumulative_dropped_frames

    @property
    def processed_frames_count(self) -> int:
        """Total number of frames processed through the timebase."""
        return self._processed_frames_count

    @property
    def current_frame_id(self) -> int:
        return self._last_frame_id if self._last_frame_id is not None else 0

    @property
    def current_timestamp(self) -> float:
        return self._last_timestamp if self._last_timestamp is not None else 0.0

    @property
    def last_timing(self) -> Optional[VideoFrameTiming]:
        return self._last_timing

    def get_average_decode_latency_ms(self) -> float:
        """Average frame decode latency over recent window in milliseconds."""
        return (sum(self._decode_latencies) / len(self._decode_latencies)) if self._decode_latencies else 0.0

    def get_average_processing_latency_ms(self) -> float:
        """Average pipeline processing latency over recent window in milliseconds."""
        return (sum(self._proc_latencies) / len(self._proc_latencies)) if self._proc_latencies else 0.0

    def get_processing_fps(self) -> float:
        """Calculate real-time pipeline processing throughput in frames per second."""
        if len(self._proc_timestamps) < 2:
            avg_proc = self.get_average_processing_latency_ms()
            return (1000.0 / avg_proc) if (avg_proc > 0.0) else self._source_fps

        t_span = self._proc_timestamps[-1] - self._proc_timestamps[0]
        if t_span > 0.0:
            return float(len(self._proc_timestamps) - 1) / t_span
        return self._source_fps

    # --------------------------------------------------------------------------
    # Authoritative Step & Frame Drop Detection
    # --------------------------------------------------------------------------
    def compute_frame_timing(
        self,
        raw_frame_id: int,
        container_pos_msec: Optional[float] = None,
        decode_duration_ms: float = 0.0,
    ) -> VideoFrameTiming:
        """Compute authoritative timestamp and source dt for the current frame.

        Parameters:
            raw_frame_id: 0-based frame counter from the decoder.
            container_pos_msec: Optional hardware / demuxer presentation timestamp in milliseconds.
            decode_duration_ms: Wall-clock duration of the decode step in milliseconds.

        Returns:
            VideoFrameTiming containing authoritative frame_id, timestamp, dt, and telemetry.
        """
        self._decode_latencies.append(decode_duration_ms)

        # 1. Authoritative Timestamp Extraction
        # If container PTS is valid and strictly advancing, preserve it
        if container_pos_msec is not None and container_pos_msec > 0.0:
            candidate_t = container_pos_msec / 1000.0
        else:
            # Fallback to dynamic frame-rate derivation: t = k / FPS
            candidate_t = float(raw_frame_id) / self._source_fps if self._source_fps > 0 else 0.0

        # 2. Frame Drop Detection & Continuity Validation
        is_dropped = False
        dropped_in_step = 0
        if self._last_frame_id is not None:
            expected_id = self._last_frame_id + 1
            if raw_frame_id > expected_id:
                dropped_in_step = raw_frame_id - expected_id
                self._cumulative_dropped_frames += dropped_in_step
                is_dropped = True
                logger.warning(
                    "Video frame drop detected! Expected frame %d, got %d (%d dropped frames)",
                    expected_id,
                    raw_frame_id,
                    dropped_in_step,
                )
            elif raw_frame_id == self._last_frame_id:
                logger.warning("Duplicate frame index %d detected from video source!", raw_frame_id)

        # 3. Dynamic Source dt Computation
        # Guaranteed: dt is strictly derived from source video timebase, NEVER wall clock
        if self._last_timestamp is not None:
            computed_dt = candidate_t - self._last_timestamp
            if computed_dt <= 0.0:
                # Disallow duplicate or backwards timestamps: advance by nominal source dt
                computed_dt = self._nominal_dt
                authoritative_t = self._last_timestamp + computed_dt
            else:
                authoritative_t = candidate_t
        else:
            # First frame (k = 0): dt is nominal source dt
            computed_dt = self._nominal_dt
            authoritative_t = candidate_t

        self._last_frame_id = raw_frame_id
        self._last_timestamp = authoritative_t
        self._processed_frames_count += 1

        timing = VideoFrameTiming(
            frame_id=raw_frame_id,
            timestamp=authoritative_t,
            dt=computed_dt,
            source_fps=self._source_fps,
            processing_fps=self.get_processing_fps(),
            decode_latency_ms=decode_duration_ms,
            processing_latency_ms=0.0,
            cumulative_dropped_frames=self._cumulative_dropped_frames,
            is_dropped=is_dropped,
            dropped_count_step=dropped_in_step,
        )
        self._last_timing = timing
        return timing

    def record_processing_latency(self, latency_ms: float) -> None:
        """Record wall-clock duration taken to execute processing -> HYBRID -> estimator -> PAT -> controller."""
        self._proc_latencies.append(latency_ms)
        self._proc_timestamps.append(time.perf_counter())

        # Update last timing with updated processing latency & throughput
        if self._last_timing is not None:
            t = self._last_timing
            self._last_timing = VideoFrameTiming(
                frame_id=t.frame_id,
                timestamp=t.timestamp,
                dt=t.dt,
                source_fps=t.source_fps,
                processing_fps=self.get_processing_fps(),
                decode_latency_ms=t.decode_latency_ms,
                processing_latency_ms=latency_ms,
                cumulative_dropped_frames=t.cumulative_dropped_frames,
                is_dropped=t.is_dropped,
                dropped_count_step=t.dropped_count_step,
            )

    # --------------------------------------------------------------------------
    # Lifecycle
    # --------------------------------------------------------------------------
    def reset(self) -> None:
        """Reset timebase state back to frame 0."""
        self._last_frame_id = None
        self._last_timestamp = None
        self._cumulative_dropped_frames = 0
        self._processed_frames_count = 0
        self._decode_latencies.clear()
        self._proc_latencies.clear()
        self._proc_timestamps.clear()
        self._last_timing = None
        logger.info("VideoTimebase reset to frame 0")

    def seek(self, frame_id: int) -> None:
        """Notify timebase of an explicit seek to frame_id."""
        clamped_id = max(0, frame_id)
        self._last_frame_id = clamped_id
        self._last_timestamp = float(clamped_id) / self._source_fps if self._source_fps > 0 else 0.0
        self._decode_latencies.clear()
        self._proc_latencies.clear()
        self._proc_timestamps.clear()
        self._last_timing = None
        logger.debug("VideoTimebase seeked to frame %d (t=%.3fs)", clamped_id, self._last_timestamp)
