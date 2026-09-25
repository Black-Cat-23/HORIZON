"""
HORIZON Phase 2B: External Video Geometry & Reversible Coordinate Systems
=========================================================================
Implements geometry-preserving transformations (Letterbox, Crop, Fit) and
rigorous bidirectional coordinate mappings between:
  1. Original Video Coordinates (u_orig, v_orig)
  2. Processing Coordinates     (u_proc, v_proc)
  3. HYBRID Coordinates         (u_hyb, v_hyb)
  4. Normalized Coordinates     (x_norm, y_norm) [unit [0,1] or centered [-1,1]]

Strict Invariants:
  - Zero modification to Virtual Camera.
  - Zero modification to HYBRID detector math or internal logic.
  - Zero hard-coded scaling factors (dynamically computed from actual dimensions).
  - Geometry is preserved (isotropic scaling, no direct non-uniform stretching).
  - Every transformation is invertible and mathematically traceable across spaces.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import math
from typing import Any, Dict, Optional, Tuple
import cv2
import numpy as np


class TransformationMethod(str, Enum):
    """Supported geometry-preserving transformation algorithms."""
    LETTERBOX = "LETTERBOX"      # Aspect-preserving scale + symmetric black border padding
    CROP = "CROP"                # Aspect-preserving scale filling canvas + center crop
    RESIZE_FIT = "RESIZE_FIT"    # Aspect-preserving scale matching canvas dimension
    IDENTITY = "IDENTITY"        # 1:1 direct passthrough (no transformation needed)


class CoordinateSpace(str, Enum):
    """The four explicit coordinate representations in the HORIZON tracking pipeline."""
    ORIGINAL_VIDEO = "ORIGINAL_VIDEO"    # [0, W_orig] x [0, H_orig] pixel coordinates of input MP4
    PROCESSING = "PROCESSING"            # [0, W_proc] x [0, H_proc] pixel coordinates of canvas fed to detector
    HYBRID = "HYBRID"                    # Coordinates in HYBRID perception space (processing canvas frame)
    NORMALIZED_UNIT = "NORMALIZED_UNIT"  # [0.0, 1.0] x [0.0, 1.0] unit box coordinates
    NORMALIZED_CENTERED = "NORMALIZED_CENTERED"  # [-1.0, +1.0] x [-1.0, +1.0] boresight-centered coordinates


@dataclass(frozen=True)
class TransformationParameters:
    """Explicit mathematical representation of a geometry-preserving transformation.

    Attributes:
        orig_width: Original video pixel width.
        orig_height: Original video pixel height.
        proc_width: Target processing canvas pixel width (default: 640).
        proc_height: Target processing canvas pixel height (default: 480).
        scale_x: Horizontal scaling factor from original to processing space.
        scale_y: Vertical scaling factor from original to processing space.
        offset_x: Horizontal offset (pad/crop) on the processing canvas in pixels.
        offset_y: Vertical offset (pad/crop) on the processing canvas in pixels.
        method: The transformation algorithm utilized.
        aspect_ratio_orig: Aspect ratio (width / height) of the original video.
        aspect_ratio_proc: Aspect ratio (width / height) of the processing canvas.
        content_width: Scaled active video width on the processing canvas in pixels.
        content_height: Scaled active video height on the processing canvas in pixels.
        pad_left: Left padding in pixels.
        pad_top: Top padding in pixels.
        pad_right: Right padding in pixels.
        pad_bottom: Bottom padding in pixels.
    """
    orig_width: int
    orig_height: int
    proc_width: int
    proc_height: int
    scale_x: float
    scale_y: float
    offset_x: float
    offset_y: float
    method: TransformationMethod
    aspect_ratio_orig: float
    aspect_ratio_proc: float
    content_width: float
    content_height: float
    pad_left: float
    pad_top: float
    pad_right: float
    pad_bottom: float

    @property
    def is_isotropic(self) -> bool:
        """True if horizontal and vertical scaling factors are identical (geometry-preserving)."""
        return math.isclose(self.scale_x, self.scale_y, rel_tol=1e-5, abs_tol=1e-7)

    @property
    def is_identity(self) -> bool:
        """True if the transformation is an exact 1:1 identity mapping."""
        return (
            self.orig_width == self.proc_width
            and self.orig_height == self.proc_height
            and math.isclose(self.scale_x, 1.0, abs_tol=1e-7)
            and math.isclose(self.scale_y, 1.0, abs_tol=1e-7)
            and math.isclose(self.offset_x, 0.0, abs_tol=1e-7)
            and math.isclose(self.offset_y, 0.0, abs_tol=1e-7)
        )


@dataclass(frozen=True)
class CoordinatePoint:
    """Immutable coordinate point tagged with its explicit CoordinateSpace."""
    x: float
    y: float
    space: CoordinateSpace
    metadata: Optional[Dict[str, Any]] = None

    def as_tuple(self) -> Tuple[float, float]:
        return (self.x, self.y)


class VideoGeometryTransformer:
    """Geometry-preserving transformation and bidirectional coordinate mapping engine.

    Dynamically calculates scaling and offsets from actual video dimensions.
    Never hard-codes scaling factors or assumes 640x480 native input.
    """

    def __init__(
        self,
        orig_width: int,
        orig_height: int,
        proc_width: int = 640,
        proc_height: int = 480,
        method: TransformationMethod = TransformationMethod.LETTERBOX,
    ) -> None:
        if orig_width <= 0 or orig_height <= 0:
            raise ValueError(f"Original dimensions must be positive integers, got {orig_width}x{orig_height}")
        if proc_width <= 0 or proc_height <= 0:
            raise ValueError(f"Processing dimensions must be positive integers, got {proc_width}x{proc_height}")

        self._orig_width = int(orig_width)
        self._orig_height = int(orig_height)
        self._proc_width = int(proc_width)
        self._proc_height = int(proc_height)
        self._method = method

        self._params = self._compute_transformation_parameters()

    @property
    def params(self) -> TransformationParameters:
        """Return the explicit immutable transformation parameters."""
        return self._params

    @property
    def orig_width(self) -> int:
        return self._orig_width

    @property
    def orig_height(self) -> int:
        return self._orig_height

    @property
    def proc_width(self) -> int:
        return self._proc_width

    @property
    def proc_height(self) -> int:
        return self._proc_height

    @property
    def scale_x(self) -> float:
        return self._params.scale_x

    @property
    def scale_y(self) -> float:
        return self._params.scale_y

    @property
    def offset_x(self) -> float:
        return self._params.offset_x

    @property
    def offset_y(self) -> float:
        return self._params.offset_y

    @property
    def method(self) -> TransformationMethod:
        return self._method

    # --------------------------------------------------------------------------
    # Dynamic Transformation Computation
    # --------------------------------------------------------------------------
    def _compute_transformation_parameters(self) -> TransformationParameters:
        """Dynamically compute scale and offset values from actual dimensions."""
        ar_orig = float(self._orig_width) / float(self._orig_height)
        ar_proc = float(self._proc_width) / float(self._proc_height)

        if self._orig_width == self._proc_width and self._orig_height == self._proc_height:
            # 1:1 Identity
            scale = 1.0
            return TransformationParameters(
                orig_width=self._orig_width,
                orig_height=self._orig_height,
                proc_width=self._proc_width,
                proc_height=self._proc_height,
                scale_x=1.0,
                scale_y=1.0,
                offset_x=0.0,
                offset_y=0.0,
                method=TransformationMethod.IDENTITY,
                aspect_ratio_orig=ar_orig,
                aspect_ratio_proc=ar_proc,
                content_width=float(self._orig_width),
                content_height=float(self._orig_height),
                pad_left=0.0,
                pad_top=0.0,
                pad_right=0.0,
                pad_bottom=0.0,
            )

        if self._method == TransformationMethod.LETTERBOX:
            # Isotropic fit preserving 100% of FOV inside canvas with symmetric padding
            scale = min(self._proc_width / float(self._orig_width), self._proc_height / float(self._orig_height))
            scale_x = scale
            scale_y = scale
            content_w = float(self._orig_width) * scale
            content_h = float(self._orig_height) * scale
            offset_x = (float(self._proc_width) - content_w) / 2.0
            offset_y = (float(self._proc_height) - content_h) / 2.0
            pad_left = offset_x
            pad_top = offset_y
            pad_right = float(self._proc_width) - (offset_x + content_w)
            pad_bottom = float(self._proc_height) - (offset_y + content_h)

        elif self._method == TransformationMethod.CROP:
            # Isotropic fill covering entire canvas, cropping excess symmetrically
            scale = max(self._proc_width / float(self._orig_width), self._proc_height / float(self._orig_height))
            scale_x = scale
            scale_y = scale
            content_w = float(self._orig_width) * scale
            content_h = float(self._orig_height) * scale
            offset_x = (float(self._proc_width) - content_w) / 2.0  # <= 0
            offset_y = (float(self._proc_height) - content_h) / 2.0  # <= 0
            pad_left = 0.0
            pad_top = 0.0
            pad_right = 0.0
            pad_bottom = 0.0

        elif self._method == TransformationMethod.RESIZE_FIT:
            # Aspect-preserving scale without extra padding (used when canvas adapts to content)
            scale = min(self._proc_width / float(self._orig_width), self._proc_height / float(self._orig_height))
            scale_x = scale
            scale_y = scale
            content_w = float(self._orig_width) * scale
            content_h = float(self._orig_height) * scale
            offset_x = 0.0
            offset_y = 0.0
            pad_left = 0.0
            pad_top = 0.0
            pad_right = 0.0
            pad_bottom = 0.0

        else:
            raise ValueError(f"Unsupported TransformationMethod: {self._method}")

        return TransformationParameters(
            orig_width=self._orig_width,
            orig_height=self._orig_height,
            proc_width=self._proc_width,
            proc_height=self._proc_height,
            scale_x=scale_x,
            scale_y=scale_y,
            offset_x=offset_x,
            offset_y=offset_y,
            method=self._method,
            aspect_ratio_orig=ar_orig,
            aspect_ratio_proc=ar_proc,
            content_width=content_w,
            content_height=content_h,
            pad_left=pad_left,
            pad_top=pad_top,
            pad_right=pad_right,
            pad_bottom=pad_bottom,
        )

    # --------------------------------------------------------------------------
    # Reversible Coordinate Transformations
    # --------------------------------------------------------------------------

    # 1. Original Video <-> Processing Space
    def original_to_processing(self, u_orig: float, v_orig: float) -> Tuple[float, float]:
        """Map a point from Original Video Coordinates to Processing Coordinates.

        u_proc = u_orig * scale_x + offset_x
        v_proc = v_orig * scale_y + offset_y
        """
        u_proc = float(u_orig) * self._params.scale_x + self._params.offset_x
        v_proc = float(v_orig) * self._params.scale_y + self._params.offset_y
        return (u_proc, v_proc)

    def processing_to_original(
        self, u_proc: float, v_proc: float, clamp: bool = False
    ) -> Tuple[float, float]:
        """Map a point from Processing Coordinates back to Original Video Coordinates.

        u_orig = (u_proc - offset_x) / scale_x
        v_orig = (v_proc - offset_y) / scale_y
        """
        u_orig = (float(u_proc) - self._params.offset_x) / self._params.scale_x
        v_orig = (float(v_proc) - self._params.offset_y) / self._params.scale_y

        if clamp:
            u_orig = max(0.0, min(float(self._orig_width), u_orig))
            v_orig = max(0.0, min(float(self._orig_height), v_orig))

        return (u_orig, v_orig)

    # 2. Processing Space <-> HYBRID Space
    def processing_to_hybrid(self, u_proc: float, v_proc: float) -> Tuple[float, float]:
        """Map Processing Coordinates to HYBRID Perception Coordinates.

        In HORIZON, HYBRID operates directly on the processing frame canvas:
        (u_hyb, v_hyb) == (u_proc, v_proc).
        """
        return (float(u_proc), float(v_proc))

    def hybrid_to_processing(self, u_hyb: float, v_hyb: float) -> Tuple[float, float]:
        """Map HYBRID Perception Coordinates to Processing Coordinates."""
        return (float(u_hyb), float(v_hyb))

    def hybrid_boresight_offset(self, u_hyb: float, v_hyb: float) -> Tuple[float, float]:
        """Compute optical displacement relative to processing canvas center (boresight).

        Delta_u = u_hyb - proc_width / 2.0
        Delta_v = v_hyb - proc_height / 2.0
        """
        center_u = float(self._proc_width) / 2.0
        center_v = float(self._proc_height) / 2.0
        return (float(u_hyb) - center_u, float(v_hyb) - center_v)

    # 3. HYBRID Space <-> Normalized Coordinates
    def hybrid_to_normalized(
        self, u_hyb: float, v_hyb: float, mode: str = "unit"
    ) -> Tuple[float, float]:
        """Map HYBRID pixel coordinates to Normalized Coordinates.

        Modes:
          'unit':     x in [0, 1], y in [0, 1] where (0,0) is top-left, (1,1) is bottom-right.
          'centered': x in [-1, +1], y in [-1, +1] where (0,0) is center (boresight).
        """
        if mode == "unit":
            x_norm = float(u_hyb) / float(self._proc_width)
            y_norm = float(v_hyb) / float(self._proc_height)
        elif mode == "centered":
            c_u = float(self._proc_width) / 2.0
            c_v = float(self._proc_height) / 2.0
            x_norm = (float(u_hyb) - c_u) / c_u
            y_norm = (float(v_hyb) - c_v) / c_v
        else:
            raise ValueError(f"Unknown normalized mode: '{mode}'. Expected 'unit' or 'centered'.")

        return (x_norm, y_norm)

    def normalized_to_hybrid(
        self, x_norm: float, y_norm: float, mode: str = "unit"
    ) -> Tuple[float, float]:
        """Map Normalized Coordinates back to HYBRID pixel coordinates."""
        if mode == "unit":
            u_hyb = float(x_norm) * float(self._proc_width)
            v_hyb = float(y_norm) * float(self._proc_height)
        elif mode == "centered":
            c_u = float(self._proc_width) / 2.0
            c_v = float(self._proc_height) / 2.0
            u_hyb = float(x_norm) * c_u + c_u
            v_hyb = float(y_norm) * c_v + c_v
        else:
            raise ValueError(f"Unknown normalized mode: '{mode}'. Expected 'unit' or 'centered'.")

        return (u_hyb, v_hyb)

    # 4. End-to-End Traceable Chains
    def original_to_normalized(
        self, u_orig: float, v_orig: float, mode: str = "unit"
    ) -> Tuple[float, float]:
        """Traceable pipeline: Original Video -> Processing -> HYBRID -> Normalized."""
        u_proc, v_proc = self.original_to_processing(u_orig, v_orig)
        u_hyb, v_hyb = self.processing_to_hybrid(u_proc, v_proc)
        return self.hybrid_to_normalized(u_hyb, v_hyb, mode=mode)

    def normalized_to_original(
        self, x_norm: float, y_norm: float, mode: str = "unit", clamp: bool = False
    ) -> Tuple[float, float]:
        """Traceable pipeline: Normalized -> HYBRID -> Processing -> Original Video."""
        u_hyb, v_hyb = self.normalized_to_hybrid(x_norm, y_norm, mode=mode)
        u_proc, v_proc = self.hybrid_to_processing(u_hyb, v_hyb)
        return self.processing_to_original(u_proc, v_proc, clamp=clamp)

    def trace_point(
        self,
        point: CoordinatePoint,
        target_space: CoordinateSpace,
        clamp: bool = False,
    ) -> CoordinatePoint:
        """Arbitrary bidirectional coordinate conversion across all 4 coordinate spaces."""
        if point.space == target_space:
            return point

        # 1. Convert source point to Original Video space
        if point.space == CoordinateSpace.ORIGINAL_VIDEO:
            u_orig, v_orig = point.x, point.y
        elif point.space == CoordinateSpace.PROCESSING:
            u_orig, v_orig = self.processing_to_original(point.x, point.y, clamp=clamp)
        elif point.space == CoordinateSpace.HYBRID:
            u_proc, v_proc = self.hybrid_to_processing(point.x, point.y)
            u_orig, v_orig = self.processing_to_original(u_proc, v_proc, clamp=clamp)
        elif point.space == CoordinateSpace.NORMALIZED_UNIT:
            u_orig, v_orig = self.normalized_to_original(point.x, point.y, mode="unit", clamp=clamp)
        elif point.space == CoordinateSpace.NORMALIZED_CENTERED:
            u_orig, v_orig = self.normalized_to_original(point.x, point.y, mode="centered", clamp=clamp)
        else:
            raise ValueError(f"Unsupported source CoordinateSpace: {point.space}")

        # 2. Convert from Original Video space to target space
        if target_space == CoordinateSpace.ORIGINAL_VIDEO:
            tgt_x, tgt_y = u_orig, v_orig
        elif target_space == CoordinateSpace.PROCESSING:
            tgt_x, tgt_y = self.original_to_processing(u_orig, v_orig)
        elif target_space == CoordinateSpace.HYBRID:
            u_proc, v_proc = self.original_to_processing(u_orig, v_orig)
            tgt_x, tgt_y = self.processing_to_hybrid(u_proc, v_proc)
        elif target_space == CoordinateSpace.NORMALIZED_UNIT:
            tgt_x, tgt_y = self.original_to_normalized(u_orig, v_orig, mode="unit")
        elif target_space == CoordinateSpace.NORMALIZED_CENTERED:
            tgt_x, tgt_y = self.original_to_normalized(u_orig, v_orig, mode="centered")
        else:
            raise ValueError(f"Unsupported target CoordinateSpace: {target_space}")

        return CoordinatePoint(x=tgt_x, y=tgt_y, space=target_space, metadata=point.metadata)

    # --------------------------------------------------------------------------
    # Region & Validity Checks
    # --------------------------------------------------------------------------
    def is_in_original_bounds(self, u_orig: float, v_orig: float) -> bool:
        """Check if coordinates lie within the original video bounds [0, W] x [0, H]."""
        return 0.0 <= u_orig <= float(self._orig_width) and 0.0 <= v_orig <= float(self._orig_height)

    def is_in_processing_bounds(self, u_proc: float, v_proc: float) -> bool:
        """Check if coordinates lie within the processing canvas [0, W_proc] x [0, H_proc]."""
        return 0.0 <= u_proc <= float(self._proc_width) and 0.0 <= v_proc <= float(self._proc_height)

    def is_in_content_region(self, u_proc: float, v_proc: float) -> bool:
        """Check if processing coordinates fall within active content (not letterbox black borders)."""
        x_min = self._params.offset_x
        x_max = self._params.offset_x + self._params.content_width
        y_min = self._params.offset_y
        y_max = self._params.offset_y + self._params.content_height
        return (x_min <= u_proc <= x_max) and (y_min <= v_proc <= y_max)

    # --------------------------------------------------------------------------
    # Frame Transformation Operations
    # --------------------------------------------------------------------------
    def transform_frame(self, frame: np.ndarray, border_value: int = 0) -> np.ndarray:
        """Apply geometry-preserving transformation to an input image array.

        Parameters:
            frame: 2D uint8 grayscale array (H_orig x W_orig) or multi-channel array.
            border_value: Intensity for padding regions in LETTERBOX mode (default: 0).

        Returns:
            Transformed frame of exact shape (proc_height, proc_width).
        """
        if not isinstance(frame, np.ndarray):
            raise TypeError(f"Expected numpy.ndarray, got {type(frame).__name__}")

        h_in, w_in = frame.shape[:2]
        if w_in != self._orig_width or h_in != self._orig_height:
            raise ValueError(
                f"Frame dimensions ({w_in}x{h_in}) do not match configured original ({self._orig_width}x{self._orig_height})"
            )

        if self._params.is_identity:
            return frame.copy()

        # Target integer sizes
        scaled_w = max(1, int(round(self._params.content_width)))
        scaled_h = max(1, int(round(self._params.content_height)))

        # Choose optimal interpolation method
        if self._params.scale_x < 1.0 or self._params.scale_y < 1.0:
            interpolation = cv2.INTER_AREA  # Anti-aliasing downsampling
        else:
            interpolation = cv2.INTER_LINEAR  # Smooth upsampling

        resized = cv2.resize(frame, (scaled_w, scaled_h), interpolation=interpolation)

        if self._method == TransformationMethod.LETTERBOX:
            # Create processing canvas and paste centered
            pad_x = int(round(self._params.offset_x))
            pad_y = int(round(self._params.offset_y))

            if frame.ndim == 2:
                canvas = np.full((self._proc_height, self._proc_width), border_value, dtype=frame.dtype)
                # Clip bounds to ensure zero out-of-bounds indexing
                r_end = min(self._proc_height, pad_y + scaled_h)
                c_end = min(self._proc_width, pad_x + scaled_w)
                paste_h = r_end - pad_y
                paste_w = c_end - pad_x
                canvas[pad_y:r_end, pad_x:c_end] = resized[:paste_h, :paste_w]
            else:
                channels = frame.shape[2]
                canvas = np.full((self._proc_height, self._proc_width, channels), border_value, dtype=frame.dtype)
                r_end = min(self._proc_height, pad_y + scaled_h)
                c_end = min(self._proc_width, pad_x + scaled_w)
                paste_h = r_end - pad_y
                paste_w = c_end - pad_x
                canvas[pad_y:r_end, pad_x:c_end, :] = resized[:paste_h, :paste_w, :]

            return canvas

        elif self._method == TransformationMethod.CROP:
            # Center crop from oversized resized image
            crop_x = int(round(-self._params.offset_x))
            crop_y = int(round(-self._params.offset_y))
            if frame.ndim == 2:
                return resized[crop_y : crop_y + self._proc_height, crop_x : crop_x + self._proc_width].copy()
            else:
                return resized[crop_y : crop_y + self._proc_height, crop_x : crop_x + self._proc_width, :].copy()

        elif self._method == TransformationMethod.RESIZE_FIT:
            return resized.copy()

        raise RuntimeError(f"Unhandled transformation method {self._method}")

    def reverse_transform_frame(self, proc_frame: np.ndarray) -> np.ndarray:
        """Extract the active content from the processing canvas and unscale to original dimensions.

        Parameters:
            proc_frame: Transformed processing canvas array of shape (proc_height, proc_width).

        Returns:
            Recovered frame of shape (orig_height, orig_width).
        """
        if proc_frame.shape[0] != self._proc_height or proc_frame.shape[1] != self._proc_width:
            raise ValueError(
                f"Expected processing frame shape ({self._proc_height}, {self._proc_width}), got {proc_frame.shape}"
            )

        if self._params.is_identity:
            return proc_frame.copy()

        if self._method == TransformationMethod.LETTERBOX:
            pad_x = int(round(self._params.offset_x))
            pad_y = int(round(self._params.offset_y))
            scaled_w = int(round(self._params.content_width))
            scaled_h = int(round(self._params.content_height))

            r_end = min(self._proc_height, pad_y + scaled_h)
            c_end = min(self._proc_width, pad_x + scaled_w)

            content = proc_frame[pad_y:r_end, pad_x:c_end]
            recovered = cv2.resize(content, (self._orig_width, self._orig_height), interpolation=cv2.INTER_LINEAR)
            return recovered

        elif self._method == TransformationMethod.CROP:
            # Recovered by uncropping onto padded canvas
            scale = self._params.scale_x
            scaled_w = int(round(self._params.content_width))
            scaled_h = int(round(self._params.content_height))
            crop_x = int(round(-self._params.offset_x))
            crop_y = int(round(-self._params.offset_y))

            padded = np.zeros((scaled_h, scaled_w), dtype=proc_frame.dtype)
            padded[crop_y : crop_y + self._proc_height, crop_x : crop_x + self._proc_width] = proc_frame
            recovered = cv2.resize(padded, (self._orig_width, self._orig_height), interpolation=cv2.INTER_LINEAR)
            return recovered

        elif self._method == TransformationMethod.RESIZE_FIT:
            return cv2.resize(proc_frame, (self._orig_width, self._orig_height), interpolation=cv2.INTER_LINEAR)

        raise RuntimeError(f"Unhandled transformation method {self._method}")
