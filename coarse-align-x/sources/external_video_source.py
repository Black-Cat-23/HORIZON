"""
HORIZON Dedicated External Video Source (SIH26169 Phase 1B)
============================================================
Dedicated sensor ingestion engine for external MP4 sensor recordings.

Responsibilities:
  - open MP4 files safely
  - validate video container, dimensions, and readability
  - decode video frames into 2D uint8 grayscale arrays
  - expose frame_id, timestamp, width, height, FPS, duration, frame_count, status
  - reset, pause, resume, seek, and detect end-of-stream (EOF)

Strict Invariants:
  - Zero perception / detection
  - Zero estimation / Kalman filtering
  - Zero PAT FSM logic
  - Zero camera control or actuator movement
  - Pure sensor / frame source.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
import time
from typing import Optional, Tuple
import cv2
import numpy as np

from sources.frame_packet import FramePacket
from sources.video_geometry import (
    CoordinatePoint,
    CoordinateSpace,
    TransformationMethod,
    TransformationParameters,
    VideoGeometryTransformer,
)
from sources.video_timebase import VideoFrameTiming, VideoTimebase

logger = logging.getLogger(__name__)


class ExternalVideoSource:
    """Dedicated External Video Source adapter for MP4 sensor recordings.

    Provides deterministic frame decoding, real metadata extraction, sequence
    controls (pause/resume/seek/reset), and end-of-stream detection.
    """

    def __init__(self, file_path: str | Path) -> None:
        self._file_path = Path(file_path).resolve()
        self._cap: Optional[cv2.VideoCapture] = None
        self._is_open: bool = False
        self._is_paused: bool = False
        self._is_eof: bool = False
        self._status: str = "NOT_OPENED"

        # Metadata
        self._native_width: int = 0
        self._native_height: int = 0
        self._fps: float = 0.0
        self._total_frames: int = 0
        self._duration_seconds: float = 0.0
        self._codec: str = "UNKNOWN"

        # Frame state
        self._frame_id: int = 0
        self._current_timestamp: float = 0.0
        self._last_packet: Optional[FramePacket] = None

        # Geometry transformer (Phase 2B)
        self._geometry_transformer: Optional[VideoGeometryTransformer] = None

        # Authoritative timebase engine (Phase 3B)
        self._timebase: Optional[VideoTimebase] = None

    # --------------------------------------------------------------------------
    # Public Properties
    # --------------------------------------------------------------------------
    @property
    def file_path(self) -> Path:
        return self._file_path

    @property
    def filename(self) -> str:
        return self._file_path.name

    def is_open(self) -> bool:
        """Return True if the video capture source is successfully opened."""
        return bool(self._is_open and self._cap is not None and self._cap.isOpened())

    @property
    def is_paused(self) -> bool:
        return self._is_paused

    @property
    def is_eof(self) -> bool:
        return self._is_eof

    @property
    def status(self) -> str:
        return self._status

    @property
    def frame_id(self) -> int:
        return self._frame_id

    @property
    def timestamp(self) -> float:
        return self._current_timestamp

    @property
    def width(self) -> int:
        return self._native_width

    @property
    def height(self) -> int:
        return self._native_height

    @property
    def fps(self) -> float:
        return self._fps

    @property
    def duration(self) -> float:
        return self._duration_seconds

    @property
    def frame_count(self) -> int:
        return self._total_frames

    @property
    def codec(self) -> str:
        return self._codec

    @property
    def geometry_transformer(self) -> Optional[VideoGeometryTransformer]:
        """Return the active VideoGeometryTransformer configured for the opened video stream."""
        return self._geometry_transformer

    @property
    def timebase(self) -> Optional[VideoTimebase]:
        """Return the authoritative VideoTimebase manager (Phase 3B)."""
        return self._timebase

    @property
    def dt(self) -> float:
        """Authoritative source-frame timestep in seconds."""
        if self._timebase is not None and self._timebase.last_timing is not None:
            return self._timebase.last_timing.dt
        return 1.0 / self._fps if self._fps > 0 else 0.033333

    def get_geometry_transformer(
        self,
        target_width: int = 640,
        target_height: int = 480,
        method: TransformationMethod = TransformationMethod.LETTERBOX,
    ) -> VideoGeometryTransformer:
        """Construct and return a geometry transformer with specified target dimensions and method."""
        w = self._native_width if self._native_width > 0 else target_width
        h = self._native_height if self._native_height > 0 else target_height
        return VideoGeometryTransformer(
            orig_width=w,
            orig_height=h,
            proc_width=target_width,
            proc_height=target_height,
            method=method,
        )

    def get_metadata(self):
        from sources.frame_source import VideoMetadata
        return VideoMetadata(
            source_type="VIDEO_FILE",
            file_path=str(self._file_path),
            native_width=self._native_width,
            native_height=self._native_height,
            fps=self._fps,
            total_frames=self._total_frames,
            duration_seconds=self._duration_seconds,
            codec=self._codec,
            normalized_width=self._native_width,
            normalized_height=self._native_height,
        )

    def get_total_frames(self) -> int:
        return self._total_frames

    def get_fps(self) -> float:
        return self._fps

    def read(self):
        """FrameSource-compatible read method returning (success, frame, timestamp, frame_index, metadata)."""
        packet = self.read_frame()
        meta = {
            "native_width": self._native_width,
            "native_height": self._native_height,
            "codec": self._codec,
            "status": self._status,
        }
        return packet.valid, packet.frame, packet.timestamp, packet.frame_id, meta

    # --------------------------------------------------------------------------
    # Lifecycle & Validation
    # --------------------------------------------------------------------------
    def validate(self) -> Tuple[bool, str]:
        """Validate whether the file exists, has a valid container, and can be decoded."""
        if not self._file_path.exists():
            return False, f"File does not exist: {self._file_path}"
        if not self._file_path.is_file():
            return False, f"Path is not a regular file: {self._file_path}"
        if self._file_path.stat().st_size == 0:
            return False, f"File is empty (0 bytes): {self._file_path}"

        test_cap = cv2.VideoCapture(str(self._file_path))
        if not test_cap.isOpened():
            test_cap.release()
            return False, f"OpenCV failed to open video container: {self._file_path}"

        w = int(test_cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        h = int(test_cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = float(test_cap.get(cv2.CAP_PROP_FPS))
        frames = int(test_cap.get(cv2.CAP_PROP_FRAME_COUNT))

        if w <= 0 or h <= 0:
            test_cap.release()
            return False, f"Invalid video dimensions: {w}x{h}"

        ret, test_frame = test_cap.read()
        test_cap.release()

        if not ret or test_frame is None:
            return False, "Failed to decode the first video frame."

        return True, "Valid video file."

    def open(self) -> bool:
        """Open and validate the video file, extracting dynamic metadata."""
        is_valid, msg = self.validate()
        if not is_valid:
            logger.error("Validation failed for %s: %s", self._file_path, msg)
            self._status = "ERROR"
            return False

        if self._cap is not None:
            self._cap.release()

        self._cap = cv2.VideoCapture(str(self._file_path))
        if not self._cap.isOpened():
            logger.error("Failed to open VideoCapture for %s", self._file_path)
            self._status = "ERROR"
            return False

        self._native_width = int(self._cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self._native_height = int(self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        raw_fps = float(self._cap.get(cv2.CAP_PROP_FPS))
        self._fps = raw_fps if (raw_fps > 0.0 and not np.isnan(raw_fps)) else 30.0

        raw_frames = int(self._cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self._total_frames = max(0, raw_frames)

        self._duration_seconds = (self._total_frames / self._fps) if (self._fps > 0 and self._total_frames > 0) else 0.0

        # Extract 4-character codec
        codec_int = int(self._cap.get(cv2.CAP_PROP_FOURCC))
        if codec_int > 0:
            self._codec = "".join([chr((codec_int >> 8 * i) & 0xFF) for i in range(4)]).strip()
        else:
            self._codec = "MP4V"

        self._is_open = True
        self._is_paused = False
        self._is_eof = False
        self._frame_id = 0
        self._current_timestamp = 0.0
        self._status = "READY"

        # Initialize Phase 2B geometry-preserving transformation engine
        self._geometry_transformer = VideoGeometryTransformer(
            orig_width=self._native_width,
            orig_height=self._native_height,
            proc_width=640,
            proc_height=480,
            method=TransformationMethod.LETTERBOX,
        )

        # Initialize Phase 3B authoritative timebase engine
        self._timebase = VideoTimebase(source_fps=self._fps, total_frames=self._total_frames)

        logger.info(
            "Opened ExternalVideoSource: %s [%dx%d @ %.2f FPS, %d frames, %.2fs, codec=%s]",
            self.filename,
            self._native_width,
            self._native_height,
            self._fps,
            self._total_frames,
            self._duration_seconds,
            self._codec,
        )
        return True

    # --------------------------------------------------------------------------
    # Frame Decoding & Ingestion
    # --------------------------------------------------------------------------
    def read_frame(self) -> FramePacket:
        """Decode and return the next frame as a standardized FramePacket.

        Returns:
            FramePacket with valid=True on success, or valid=False on EOF/error.
        """
        if not self.is_open or self._cap is None:
            self._status = "NOT_OPENED"
            return FramePacket(
                frame=None,
                frame_id=self._frame_id,
                timestamp=self._current_timestamp,
                width=self._native_width,
                height=self._native_height,
                source_type="EXTERNAL_VIDEO",
                source_fps=self._fps,
                valid=False,
                filename=self.filename,
                duration=self._duration_seconds,
                codec=self._codec,
                geometry=self._geometry_transformer.params if self._geometry_transformer else None,
                dt=self.dt,
                decode_latency_ms=0.0,
                dropped_frames=self._timebase.cumulative_dropped_frames if self._timebase else 0,
            )

        if self._is_paused and self._last_packet is not None:
            return self._last_packet

        t_avail = time.perf_counter()
        t_dec_start = time.perf_counter()
        ret, raw_frame = self._cap.read()

        if not ret or raw_frame is None:
            t_dec_end = time.perf_counter()
            dec_latency_ms = (t_dec_end - t_dec_start) * 1000.0
            self._is_eof = True
            self._status = "END_OF_STREAM"
            logger.info("Reached End of Stream for %s at frame %d", self.filename, self._frame_id)
            return FramePacket(
                frame=None,
                frame_id=self._frame_id,
                timestamp=self._current_timestamp,
                width=self._native_width,
                height=self._native_height,
                source_type="EXTERNAL_VIDEO",
                source_fps=self._fps,
                valid=False,
                filename=self.filename,
                duration=self._duration_seconds,
                codec=self._codec,
                geometry=self._geometry_transformer.params if self._geometry_transformer else None,
                dt=self.dt,
                decode_latency_ms=dec_latency_ms,
                dropped_frames=self._timebase.cumulative_dropped_frames if self._timebase else 0,
                frame_available_t=t_avail,
                decode_start_t=t_dec_start,
                decode_end_t=t_dec_end,
            )

        # Convert to single-channel uint8 grayscale
        if raw_frame.ndim == 3:
            if raw_frame.shape[2] == 3:
                gray_frame = cv2.cvtColor(raw_frame, cv2.COLOR_BGR2GRAY)
            elif raw_frame.shape[2] == 4:
                gray_frame = cv2.cvtColor(raw_frame, cv2.COLOR_BGRA2GRAY)
            else:
                gray_frame = raw_frame[:, :, 0]
        else:
            gray_frame = raw_frame

        if gray_frame.dtype != np.uint8:
            gray_frame = np.clip(gray_frame, 0, 255).astype(np.uint8)

        t_dec_end = time.perf_counter()
        dec_latency_ms = (t_dec_end - t_dec_start) * 1000.0

        current_id = self._frame_id
        pos_msec = float(self._cap.get(cv2.CAP_PROP_POS_MSEC))

        # Authoritative timebase derivation (Phase 3B)
        if self._timebase is not None:
            timing = self._timebase.compute_frame_timing(
                raw_frame_id=current_id,
                container_pos_msec=pos_msec,
                decode_duration_ms=dec_latency_ms,
            )
            timestamp_s = timing.timestamp
            dt_s = timing.dt
            dropped_cnt = timing.cumulative_dropped_frames
        else:
            timestamp_s = current_id / self._fps if self._fps > 0 else 0.0
            dt_s = 1.0 / self._fps if self._fps > 0 else 0.033333
            dropped_cnt = 0

        self._frame_id += 1
        self._current_timestamp = timestamp_s
        self._status = "PLAYING"

        packet = FramePacket(
            frame=gray_frame,
            frame_id=current_id,
            timestamp=timestamp_s,
            width=gray_frame.shape[1],
            height=gray_frame.shape[0],
            source_type="EXTERNAL_VIDEO",
            source_fps=self._fps,
            valid=True,
            filename=self.filename,
            duration=self._duration_seconds,
            codec=self._codec,
            geometry=self._geometry_transformer.params if self._geometry_transformer else None,
            dt=dt_s,
            decode_latency_ms=dec_latency_ms,
            dropped_frames=dropped_cnt,
            frame_available_t=t_avail,
            decode_start_t=t_dec_start,
            decode_end_t=t_dec_end,
        )
        self._last_packet = packet
        return packet

    def read_processing_frame(
        self,
        target_width: int = 640,
        target_height: int = 480,
        method: TransformationMethod = TransformationMethod.LETTERBOX,
        border_value: int = 0,
    ) -> Tuple[FramePacket, TransformationParameters]:
        """Decode next frame and apply geometry-preserving transformation.

        Returns:
            Tuple of (processing_packet, transformation_parameters) where processing_packet.frame
            has exact shape (target_height, target_width).
        """
        raw_packet = self.read_frame()
        transformer = self.get_geometry_transformer(target_width, target_height, method=method)

        if not raw_packet.valid or raw_packet.frame is None:
            empty_packet = FramePacket(
                frame=None,
                frame_id=raw_packet.frame_id,
                timestamp=raw_packet.timestamp,
                width=target_width,
                height=target_height,
                source_type="EXTERNAL_VIDEO",
                source_fps=self._fps,
                valid=False,
                filename=self.filename,
                duration=self._duration_seconds,
                codec=self._codec,
                geometry=transformer.params,
                frame_available_t=raw_packet.frame_available_t,
                decode_start_t=raw_packet.decode_start_t,
                decode_end_t=raw_packet.decode_end_t,
            )
            return empty_packet, transformer.params

        proc_frame = transformer.transform_frame(raw_packet.frame, border_value=border_value)
        proc_packet = FramePacket(
            frame=proc_frame,
            frame_id=raw_packet.frame_id,
            timestamp=raw_packet.timestamp,
            width=target_width,
            height=target_height,
            source_type="EXTERNAL_VIDEO",
            source_fps=self._fps,
            valid=True,
            filename=self.filename,
            duration=self._duration_seconds,
            codec=self._codec,
            geometry=transformer.params,
            dt=raw_packet.dt,
            decode_latency_ms=raw_packet.decode_latency_ms,
            dropped_frames=raw_packet.dropped_frames,
            frame_available_t=raw_packet.frame_available_t,
            decode_start_t=raw_packet.decode_start_t,
            decode_end_t=raw_packet.decode_end_t,
        )
        return proc_packet, transformer.params

    # --------------------------------------------------------------------------
    # Sequence Controls
    # --------------------------------------------------------------------------
    def pause(self) -> None:
        """Pause playback progression without closing the underlying stream."""
        if self._is_open:
            self._is_paused = True
            self._status = "PAUSED"
            logger.debug("Paused ExternalVideoSource: %s", self.filename)

    def resume(self) -> None:
        """Resume playback progression."""
        if self._is_open:
            self._is_paused = False
            self._status = "PLAYING"
            logger.debug("Resumed ExternalVideoSource: %s", self.filename)

    def reset(self) -> None:
        """Reset stream position back to frame 0."""
        if self._cap is not None and self._cap.isOpened():
            self._cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
        self._frame_id = 0
        self._current_timestamp = 0.0
        self._is_eof = False
        self._is_paused = False
        self._last_packet = None
        self._status = "READY"
        if self._timebase is not None:
            self._timebase.reset()
        logger.info("Reset ExternalVideoSource: %s to frame 0", self.filename)

    def seek(self, target_frame_idx: int) -> bool:
        """Seek stream to a specific 0-based frame index."""
        if not self.is_open or self._cap is None:
            return False

        clamped_idx = max(0, min(target_frame_idx, max(0, self._total_frames - 1)))
        success = bool(self._cap.set(cv2.CAP_PROP_POS_FRAMES, clamped_idx))
        if success:
            self._frame_id = clamped_idx
            self._current_timestamp = clamped_idx / self._fps if self._fps > 0 else 0.0
            self._is_eof = False
            self._last_packet = None
            if self._timebase is not None:
                self._timebase.seek(clamped_idx)
            logger.debug("Seeked %s to frame %d", self.filename, clamped_idx)
        return success

    def close(self) -> None:
        """Close and release all underlying video capture resources."""
        if self._cap is not None:
            self._cap.release()
            self._cap = None
        self._is_open = False
        self._geometry_transformer = None
        self._timebase = None
        self._status = "CLOSED"
        logger.info("Closed ExternalVideoSource: %s", self.filename)

    def __enter__(self) -> ExternalVideoSource:
        self.open()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    def __del__(self) -> None:
        self.close()
