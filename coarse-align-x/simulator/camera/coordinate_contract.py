"""
HORIZON Coordinate System Contract
=======================================
Authoritative, single-source-of-truth definition for all coordinate
conventions used in the HORIZON simulation environment.

This module defines NO logic. It exists solely as a documentation object
imported by camera and projection modules to enforce consistent
convention references.

CONVENTIONS ARE FROZEN. Do not change without updating all modules
that import this contract and all related tests.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final


# ---------------------------------------------------------------------------
# Axis direction constants (used in documentation and assertions)
# ---------------------------------------------------------------------------

RIGHT: Final[str] = "right (+X)"
DOWN: Final[str] = "down (+Y)"
RADIANS: Final[str] = "radians"
DEGREES: Final[str] = "degrees"


@dataclass(frozen=True)
class CoordinateSystemSpec:
    """Immutable specification of a single coordinate system.

    Attributes:
        name: Human-readable name (e.g. "World", "Image", "Angular").
        origin: Textual description of the origin point.
        positive_x: Direction that positive X axis points toward.
        positive_y: Direction that positive Y axis points toward.
        units: Physical unit of the coordinate values.
        handedness: Chirality ("left" or "right").
        notes: Optional clarifying notes for this coordinate system.
    """
    name: str
    origin: str
    positive_x: str
    positive_y: str
    units: str
    handedness: str
    notes: str = ""


# ---------------------------------------------------------------------------
# WORLD Coordinate System
# ---------------------------------------------------------------------------
WORLD: Final[CoordinateSystemSpec] = CoordinateSystemSpec(
    name="World",
    origin=(
        "Top-left corner of the 2000×2000 simulation canvas at pixel (0, 0). "
        "The camera's physical resting center is at (1000.0, 1000.0)."
    ),
    positive_x="right — increasing column index",
    positive_y="down — increasing row index",
    units="world pixels (1 world pixel = 1 simulation metre at default scale)",
    handedness="left",
    notes=(
        "World coordinates are continuous floating-point. "
        "TargetState.x and TargetState.y are in this system. "
        "The world is rendered as a 2D NumPy array with shape (height, width), "
        "so world row = y, world column = x."
    ),
)

# ---------------------------------------------------------------------------
# CAMERA Coordinate System (Boresight Reference Frame)
# ---------------------------------------------------------------------------
CAMERA: Final[CoordinateSystemSpec] = CoordinateSystemSpec(
    name="Camera",
    origin=(
        "The world position (bx, by) of the camera boresight, computed as: "
        "  bx = world_center_x + fx * tan(pan_rad) "
        "  by = world_center_y + fy * tan(tilt_rad) "
        "where world_center = (world_width/2, world_height/2)."
    ),
    positive_x="right — corresponds to positive pan (rightward image motion)",
    positive_y="down — corresponds to positive tilt (downward image motion)",
    units=(
        "world pixels. "
        "IMPLICIT SCALE ASSUMPTION: The boresight world-pixel displacement "
        "uses fx and fy (image focal lengths in image pixels) directly. "
        "This is valid because the simulation defines 1 world pixel = 1 image pixel "
        "at the camera sensor plane — i.e., the crop window is a 1:1 pixel mapping. "
        "This assumption must be preserved in any architectural change."
    ),
    handedness="left",
    notes=(
        "This is not a separate physical 3D camera frame. "
        "It is a 2D boresight displacement reference used to translate "
        "pan/tilt angles to world pixel positions for viewport extraction."
    ),
)

# ---------------------------------------------------------------------------
# IMAGE Coordinate System (Sensor / Pixel)
# ---------------------------------------------------------------------------
IMAGE: Final[CoordinateSystemSpec] = CoordinateSystemSpec(
    name="Image",
    origin="Top-left of the 640×480 sensor array at pixel (0, 0)",
    positive_x="right — increasing column index (+u direction)",
    positive_y="down — increasing row index (+v direction)",
    units="image pixels",
    handedness="left",
    notes=(
        "u corresponds to horizontal pixel position. "
        "v corresponds to vertical pixel position. "
        "Principal point (cx, cy) = (W/2, H/2) = (320.0, 240.0) for default config. "
        "Valid pixel range: u ∈ [0, W], v ∈ [0, H]. "
        "Subpixel coordinates are continuous floats within this range."
    ),
)

# ---------------------------------------------------------------------------
# ANGULAR Coordinate System (Camera Angular Offsets)
# ---------------------------------------------------------------------------
ANGULAR: Final[CoordinateSystemSpec] = CoordinateSystemSpec(
    name="Angular",
    origin=(
        "Camera boresight direction: theta_x = 0, theta_y = 0 "
        "maps to principal point (cx, cy) in image coordinates."
    ),
    positive_x=(
        "positive theta_x = rightward angular offset — target appears at u > cx. "
        "Corresponds to positive gimbal pan angle."
    ),
    positive_y=(
        "positive theta_y = downward angular offset — target appears at v > cy. "
        "Corresponds to positive gimbal tilt angle."
    ),
    units=(
        "radians (internally). "
        "Degrees used in gimbal state properties and configuration. "
        "Always convert: math.radians() and math.degrees()."
    ),
    handedness="left",
    notes=(
        "Projection formula: u = cx + fx * tan(theta_x), v = cy + fy * tan(theta_y). "
        "Inverse: theta_x = atan((u - cx) / fx), theta_y = atan((v - cy) / fy). "
        "Valid angular range: |theta_x| < FOV_x/2, |theta_y| < FOV_y/2. "
        "At the default FOV of 4°×3°: half-FOV = 2° × 1.5°. "
        "Pointing error is defined as theta in the angular coordinate system."
    ),
)

# ---------------------------------------------------------------------------
# Consistency invariants (documented, not runtime-enforced here)
# ---------------------------------------------------------------------------
CONSISTENCY_INVARIANTS: Final[list[str]] = [
    "World +X   ↔ Image +u   ↔ Angular +theta_x  (all rightward).",
    "World +Y   ↔ Image +v   ↔ Angular +theta_y  (all downward).",
    "Camera boresight at (0° pan, 0° tilt) → image principal point (cx, cy).",
    "Positive pan  → u increases (target moves right in image).",
    "Positive tilt → v increases (target moves down in image).",
    "All systems are left-handed in 2D (Z would point into screen).",
    "World pixel scale = image pixel scale at boresight (1:1 crop, no rescaling).",
]

# ---------------------------------------------------------------------------
# Module-level summary for quick reference
# ---------------------------------------------------------------------------
COORDINATE_CONTRACT_SUMMARY: Final[str] = """
HORIZON Coordinate System Contract (Summary)
=============================================
System   | Origin                      | +X         | +Y         | Units
---------|-----------------------------| -----------|------------|------
World    | Canvas top-left (0, 0)      | right      | down       | world px
Camera   | Boresight world position    | right      | down       | world px
Image    | Sensor top-left (0, 0)      | right (+u) | down (+v)  | image px
Angular  | Boresight (0°, 0°)          | right (+θx)| down (+θy) | radians

Projection:  u = cx + fx * tan(θx)     Inverse: θx = atan((u-cx)/fx)
             v = cy + fy * tan(θy)              θy = atan((v-cy)/fy)

All systems: LEFT-HANDED, consistent +X right / +Y down.
"""
