"""
HORIZON Camera Intrinsics Model
======================================
Formal mathematical model for pinhole optical camera intrinsics,
tangent projection, inverse projection, FOV boundary verification,
calibration override, uncertainty propagation, and mathematical invariants.

Coordinate convention (see simulator/camera/coordinate_contract.py):
  - Angular origin: camera boresight (theta_x=0, theta_y=0)
  - Image origin:   top-left pixel (u=0, v=0)
  - +theta_x / +u: rightward
  - +theta_y / +v: downward

Projection formulas:
  u = cx + fx * tan(theta_x)        [IMAGE system ← ANGULAR system]
  v = cy + fy * tan(theta_y)

Inverse:
  theta_x = arctan((u - cx) / fx)   [ANGULAR system ← IMAGE system]
  theta_y = arctan((v - cy) / fy)

Focal length derivation from FOV:
  fx = (W / 2) / tan(FOV_x / 2)
  fy = (H / 2) / tan(FOV_y / 2)
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional, Tuple


# ---------------------------------------------------------------------------
# Uncertainty propagation result
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class PixelUncertainty:
    """Pixel-domain measurement uncertainty input.

    Attributes:
        sigma_u: 1-sigma uncertainty in horizontal pixel coordinate (px).
        sigma_v: 1-sigma uncertainty in vertical pixel coordinate (px).
    """
    sigma_u: float
    sigma_v: float

    def __post_init__(self) -> None:
        if self.sigma_u < 0 or self.sigma_v < 0:
            raise ValueError(
                f"Pixel uncertainties must be non-negative: "
                f"sigma_u={self.sigma_u}, sigma_v={self.sigma_v}"
            )


@dataclass(frozen=True)
class AngularUncertainty:
    """Angular uncertainty propagated from pixel measurement noise.

    Uses exact first-order propagation of uncertainty through the
    arctan inverse-projection:
        sigma_theta_x = sigma_u / (fx * (1 + ((u - cx) / fx)^2))
        sigma_theta_y = sigma_v / (fy * (1 + ((v - cy) / fy)^2))

    At boresight (u=cx, v=cy) this simplifies to:
        sigma_theta_x = sigma_u / fx
        sigma_theta_y = sigma_v / fy

    Attributes:
        sigma_theta_x: 1-sigma angular uncertainty in horizontal axis (radians).
        sigma_theta_y: 1-sigma angular uncertainty in vertical axis (radians).
        sigma_u_input: Input pixel uncertainty that generated these values (px).
        sigma_v_input: Input pixel uncertainty that generated these values (px).
        theta_x_eval: Angle at which uncertainty was evaluated (radians).
        theta_y_eval: Angle at which uncertainty was evaluated (radians).
    """
    sigma_theta_x: float
    sigma_theta_y: float
    sigma_u_input: float
    sigma_v_input: float
    theta_x_eval: float
    theta_y_eval: float

    @property
    def sigma_theta_x_deg(self) -> float:
        """Horizontal angular uncertainty in degrees."""
        return math.degrees(self.sigma_theta_x)

    @property
    def sigma_theta_y_deg(self) -> float:
        """Vertical angular uncertainty in degrees."""
        return math.degrees(self.sigma_theta_y)

    def summary(self) -> str:
        return (
            f"AngularUncertainty:\n"
            f"  Input:   sigma_u={self.sigma_u_input:.4f} px, "
            f"sigma_v={self.sigma_v_input:.4f} px\n"
            f"  Eval at: theta_x={math.degrees(self.theta_x_eval):.4f}°, "
            f"theta_y={math.degrees(self.theta_y_eval):.4f}°\n"
            f"  Output:  sigma_theta_x={self.sigma_theta_x_deg:.6f}°, "
            f"sigma_theta_y={self.sigma_theta_y_deg:.6f}°"
        )


# ---------------------------------------------------------------------------
# Core intrinsics model (Phase 1 — backward compatible)
# ---------------------------------------------------------------------------

class CameraIntrinsics:
    """Pinhole camera intrinsic model with analytical projection.

    Coordinate convention:
      - Angular origin: camera boresight (theta_x=0, theta_y=0)
      - Image origin:   top-left pixel (u=0, v=0)
      - +theta_x / +u: rightward
      - +theta_y / +v: downward
      See simulator/camera/coordinate_contract.py for full reference.

    Parameters:
        width: Sensor width in pixels (e.g., 640).
        height: Sensor height in pixels (e.g., 480).
        fov_horizontal_deg: Horizontal Field-of-View in degrees (e.g., 4.0).
        fov_vertical_deg: Vertical Field-of-View in degrees (e.g., 3.0).
    """

    def __init__(
        self,
        width: int = 640,
        height: int = 480,
        fov_horizontal_deg: float = 4.0,
        fov_vertical_deg: float = 3.0,
    ) -> None:
        if width <= 0 or height <= 0:
            raise ValueError(f"Sensor dimensions must be positive: {width}x{height}")
        if fov_horizontal_deg <= 0 or fov_vertical_deg <= 0:
            raise ValueError(
                f"FOV must be positive: {fov_horizontal_deg}°x{fov_vertical_deg}°"
            )
        if fov_horizontal_deg >= 180 or fov_vertical_deg >= 180:
            raise ValueError(
                f"FOV must be < 180°: {fov_horizontal_deg}°x{fov_vertical_deg}°"
            )

        self._width = int(width)
        self._height = int(height)
        self._fov_x_deg = float(fov_horizontal_deg)
        self._fov_y_deg = float(fov_vertical_deg)

        self._fov_x_rad = math.radians(self._fov_x_deg)
        self._fov_y_rad = math.radians(self._fov_y_deg)

        self._half_fov_x_rad = self._fov_x_rad / 2.0
        self._half_fov_y_rad = self._fov_y_rad / 2.0

        # Principal point (exact center of sensor)
        self._cx = float(self._width) / 2.0
        self._cy = float(self._height) / 2.0

        # Exact analytical focal lengths derived from FOV
        self._fx = (float(self._width) / 2.0) / math.tan(self._half_fov_x_rad)
        self._fy = (float(self._height) / 2.0) / math.tan(self._half_fov_y_rad)

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def width(self) -> int:
        return self._width

    @property
    def height(self) -> int:
        return self._height

    @property
    def fov_x_deg(self) -> float:
        return self._fov_x_deg

    @property
    def fov_y_deg(self) -> float:
        return self._fov_y_deg

    @property
    def fov_x_rad(self) -> float:
        return self._fov_x_rad

    @property
    def fov_y_rad(self) -> float:
        return self._fov_y_rad

    @property
    def half_fov_x_rad(self) -> float:
        return self._half_fov_x_rad

    @property
    def half_fov_y_rad(self) -> float:
        return self._half_fov_y_rad

    @property
    def fx(self) -> float:
        return self._fx

    @property
    def fy(self) -> float:
        return self._fy

    @property
    def cx(self) -> float:
        return self._cx

    @property
    def cy(self) -> float:
        return self._cy

    # ------------------------------------------------------------------
    # Projection / Inverse
    # ------------------------------------------------------------------

    def project(self, theta_x_rad: float, theta_y_rad: float) -> Tuple[float, float]:
        """Project angular offsets (relative to camera boresight) to pixel coordinates (u, v).

        Formula:
            u = cx + fx * tan(theta_x)
            v = cy + fy * tan(theta_y)
        """
        u = self._cx + self._fx * math.tan(theta_x_rad)
        v = self._cy + self._fy * math.tan(theta_y_rad)
        return u, v

    def unproject(self, u: float, v: float) -> Tuple[float, float]:
        """Inverse projection from pixel coordinates (u, v) to angular offsets (theta_x, theta_y) in radians.

        Formula:
            theta_x = arctan((u - cx) / fx)
            theta_y = arctan((v - cy) / fy)
        """
        theta_x = math.atan((u - self._cx) / self._fx)
        theta_y = math.atan((v - self._cy) / self._fy)
        return theta_x, theta_y

    def is_in_fov(
        self, theta_x_rad: float, theta_y_rad: float, tol_rad: float = 1e-12
    ) -> bool:
        """Check if target angular location is within optical field of view.

        Returns True if:
            -half_fov_x <= theta_x <= +half_fov_x and
            -half_fov_y <= theta_y <= +half_fov_y
        """
        within_x = abs(theta_x_rad) <= (self._half_fov_x_rad + tol_rad)
        within_y = abs(theta_y_rad) <= (self._half_fov_y_rad + tol_rad)
        return within_x and within_y

    def is_pixel_in_sensor(self, u: float, v: float, tol_px: float = 1e-9) -> bool:
        """Check if projected pixel coordinate falls within active sensor array [0, W] x [0, H]."""
        return (-tol_px <= u <= self._width + tol_px) and (-tol_px <= v <= self._height + tol_px)

    # ------------------------------------------------------------------
    # New: Uncertainty Propagation
    # ------------------------------------------------------------------

    def compute_angular_uncertainty(
        self,
        pixel_uncertainty: PixelUncertainty,
        theta_x_rad: float = 0.0,
        theta_y_rad: float = 0.0,
    ) -> AngularUncertainty:
        """Propagate pixel measurement uncertainty to angular uncertainty.

        Uses exact first-order (Jacobian) uncertainty propagation through
        the arctan inverse projection:

            theta_x = arctan((u - cx) / fx)

        The partial derivative of theta_x w.r.t. u is:
            d(theta_x)/du = 1 / (fx * (1 + ((u - cx) / fx)^2))
                          = 1 / (fx * (1 + tan²(theta_x)))
                          = cos²(theta_x) / fx

        Therefore:
            sigma_theta_x = sigma_u * |d(theta_x)/du|
                          = sigma_u / (fx * (1 + tan²(theta_x)))

        At boresight (theta_x = theta_y = 0):
            sigma_theta_x = sigma_u / fx
            sigma_theta_y = sigma_v / fy

        This is the paraxial pixel-noise-to-angle-noise mapping used in
        pointing error budget analysis.

        Args:
            pixel_uncertainty: PixelUncertainty(sigma_u, sigma_v) in pixels.
            theta_x_rad: Angular position at which to evaluate (default 0 = boresight).
            theta_y_rad: Angular position at which to evaluate (default 0 = boresight).

        Returns:
            AngularUncertainty with sigma_theta_x and sigma_theta_y in radians.

        Notes:
            This does NOT use ground truth. sigma_u and sigma_v are
            measurement/detector noise characterizations, not GT-derived.
        """
        # Jacobian: d(theta_x)/d(u) = 1 / (fx * (1 + tan^2(theta_x)))
        tan_x = math.tan(theta_x_rad)
        tan_y = math.tan(theta_y_rad)

        jacobian_x = 1.0 / (self._fx * (1.0 + tan_x ** 2))
        jacobian_y = 1.0 / (self._fy * (1.0 + tan_y ** 2))

        sigma_theta_x = pixel_uncertainty.sigma_u * abs(jacobian_x)
        sigma_theta_y = pixel_uncertainty.sigma_v * abs(jacobian_y)

        return AngularUncertainty(
            sigma_theta_x=sigma_theta_x,
            sigma_theta_y=sigma_theta_y,
            sigma_u_input=pixel_uncertainty.sigma_u,
            sigma_v_input=pixel_uncertainty.sigma_v,
            theta_x_eval=theta_x_rad,
            theta_y_eval=theta_y_rad,
        )

    # ------------------------------------------------------------------
    # New: Mathematical Invariant Validation
    # ------------------------------------------------------------------

    def validate_invariants(self, tol: float = 1e-9) -> None:
        """Assert all mathematical invariants of this intrinsics object.

        Raises:
            AssertionError: If any invariant is violated.

        Invariants checked:
            1. fx > 0, fy > 0 (positive focal lengths)
            2. cx > 0, cy > 0 (positive principal point)
            3. 0 < FOV_x < 180°, 0 < FOV_y < 180° (valid FOV range)
            4. width > 0, height > 0 (valid resolution)
            5. cx == width / 2 (center principal point for FOV-derived calibration)
            6. cy == height / 2 (center principal point)
            7. FOV roundtrip: 2*atan(W/2 / fx) == FOV_x (focal length consistency)
            8. Projection at boresight → principal point
            9. Projection is monotone: positive theta_x → larger u
            10. All values are finite (no inf, no nan)
        """
        import math as _math

        # 1. Positive focal lengths
        assert self._fx > 0, f"fx must be positive, got {self._fx}"
        assert self._fy > 0, f"fy must be positive, got {self._fy}"

        # 2. Positive principal point
        assert self._cx > 0, f"cx must be positive, got {self._cx}"
        assert self._cy > 0, f"cy must be positive, got {self._cy}"

        # 3. Valid FOV range
        assert 0 < self._fov_x_deg < 180, f"FOV_x must be in (0°,180°), got {self._fov_x_deg}°"
        assert 0 < self._fov_y_deg < 180, f"FOV_y must be in (0°,180°), got {self._fov_y_deg}°"

        # 4. Valid resolution
        assert self._width > 0, f"width must be positive, got {self._width}"
        assert self._height > 0, f"height must be positive, got {self._height}"

        # 5-6. Center principal point
        assert abs(self._cx - self._width / 2.0) < tol, (
            f"cx ({self._cx}) != width/2 ({self._width / 2.0})"
        )
        assert abs(self._cy - self._height / 2.0) < tol, (
            f"cy ({self._cy}) != height/2 ({self._height / 2.0})"
        )

        # 7. FOV roundtrip consistency
        fov_x_roundtrip = 2.0 * _math.degrees(_math.atan((self._width / 2.0) / self._fx))
        fov_y_roundtrip = 2.0 * _math.degrees(_math.atan((self._height / 2.0) / self._fy))
        assert abs(fov_x_roundtrip - self._fov_x_deg) < tol, (
            f"FOV_x roundtrip error: expected {self._fov_x_deg}°, got {fov_x_roundtrip}°"
        )
        assert abs(fov_y_roundtrip - self._fov_y_deg) < tol, (
            f"FOV_y roundtrip error: expected {self._fov_y_deg}°, got {fov_y_roundtrip}°"
        )

        # 8. Boresight → principal point
        u0, v0 = self.project(0.0, 0.0)
        assert abs(u0 - self._cx) < tol, f"project(0,0).u != cx: {u0} != {self._cx}"
        assert abs(v0 - self._cy) < tol, f"project(0,0).v != cy: {v0} != {self._cy}"

        # 9. Monotone projection (positive theta → larger pixel)
        eps = _math.radians(0.001)
        u_pos, _ = self.project(eps, 0.0)
        u_neg, _ = self.project(-eps, 0.0)
        assert u_pos > u_neg, f"Projection not monotone in X: u(+ε)={u_pos} <= u(-ε)={u_neg}"
        _, v_pos = self.project(0.0, eps)
        _, v_neg = self.project(0.0, -eps)
        assert v_pos > v_neg, f"Projection not monotone in Y: v(+ε)={v_pos} <= v(-ε)={v_neg}"

        # 10. All values finite
        for name, val in [
            ("fx", self._fx), ("fy", self._fy),
            ("cx", self._cx), ("cy", self._cy),
            ("fov_x_rad", self._fov_x_rad), ("fov_y_rad", self._fov_y_rad),
        ]:
            assert _math.isfinite(val), f"Non-finite value detected: {name}={val}"

    # ------------------------------------------------------------------
    # New: Matrix representation
    # ------------------------------------------------------------------

    def to_matrix(self) -> list:
        """Return the 3×3 camera intrinsics matrix K as a nested list.

        K = [[fx,  0, cx],
             [ 0, fy, cy],
             [ 0,  0,  1]]

        Returns:
            3×3 nested list (row-major). Import numpy to convert:
            ``np.array(intrinsics.to_matrix())``
        """
        return [
            [self._fx, 0.0,      self._cx],
            [0.0,      self._fy, self._cy],
            [0.0,      0.0,      1.0     ],
        ]

    def summary(self) -> str:
        """Return a human-readable summary of this calibration."""
        return (
            f"CameraIntrinsics:\n"
            f"  Resolution:  {self._width}×{self._height} px\n"
            f"  FOV:         {self._fov_x_deg:.4f}° × {self._fov_y_deg:.4f}°\n"
            f"  fx={self._fx:.6f} px   fy={self._fy:.6f} px\n"
            f"  cx={self._cx:.4f} px   cy={self._cy:.4f} px\n"
            f"  half_FOV_x={math.degrees(self._half_fov_x_rad):.4f}°  "
            f"half_FOV_y={math.degrees(self._half_fov_y_rad):.4f}°"
        )


# ---------------------------------------------------------------------------
# CameraCalibration — explicit override path
# ---------------------------------------------------------------------------

class CameraCalibration:
    """Extended calibration model with optional explicit intrinsic overrides.

    Builds on CameraIntrinsics but allows explicit specification of fx, fy,
    cx, cy to represent a calibrated (not just FOV-derived) camera model.
    When explicit values are provided, the FOV arguments are still required
    for FOV boundary checks and summary reporting.

    Regenerates correctly when resolution, FOV, or aspect ratio changes
    via the from_config() classmethod.

    Parameters:
        width: Sensor width in pixels.
        height: Sensor height in pixels.
        fov_horizontal_deg: Horizontal FOV in degrees (used for FOV-derived defaults).
        fov_vertical_deg: Vertical FOV in degrees (used for FOV-derived defaults).
        fx_override: Optional explicit horizontal focal length in pixels.
                     If None, derived analytically from fov_horizontal_deg.
        fy_override: Optional explicit vertical focal length in pixels.
                     If None, derived analytically from fov_vertical_deg.
        cx_override: Optional explicit principal point x. If None = width/2.
        cy_override: Optional explicit principal point y. If None = height/2.
        label: Optional human-readable label for this calibration (e.g., "Lens_v1").
    """

    def __init__(
        self,
        width: int = 640,
        height: int = 480,
        fov_horizontal_deg: float = 4.0,
        fov_vertical_deg: float = 3.0,
        fx_override: Optional[float] = None,
        fy_override: Optional[float] = None,
        cx_override: Optional[float] = None,
        cy_override: Optional[float] = None,
        label: str = "default",
    ) -> None:
        # Build base intrinsics from FOV (analytical defaults)
        self._base = CameraIntrinsics(
            width=width,
            height=height,
            fov_horizontal_deg=fov_horizontal_deg,
            fov_vertical_deg=fov_vertical_deg,
        )
        self._label = label
        self._has_overrides = any(
            v is not None for v in (fx_override, fy_override, cx_override, cy_override)
        )

        # Validate overrides
        if fx_override is not None and fx_override <= 0:
            raise ValueError(f"fx_override must be positive, got {fx_override}")
        if fy_override is not None and fy_override <= 0:
            raise ValueError(f"fy_override must be positive, got {fy_override}")
        if cx_override is not None and not (0 < cx_override <= width):
            raise ValueError(f"cx_override must be in (0, {width}], got {cx_override}")
        if cy_override is not None and not (0 < cy_override <= height):
            raise ValueError(f"cy_override must be in (0, {height}], got {cy_override}")

        # Resolved values (override takes precedence over FOV-derived)
        self._fx = float(fx_override) if fx_override is not None else self._base.fx
        self._fy = float(fy_override) if fy_override is not None else self._base.fy
        self._cx = float(cx_override) if cx_override is not None else self._base.cx
        self._cy = float(cy_override) if cy_override is not None else self._base.cy

    @classmethod
    def from_config(
        cls,
        width: int,
        height: int,
        fov_horizontal_deg: float,
        fov_vertical_deg: float,
        label: str = "from_config",
    ) -> "CameraCalibration":
        """Create a CameraCalibration that always derives intrinsics from FOV.

        Regenerates correctly when resolution, FOV, or aspect ratio changes.
        No manual duplication of focal lengths required.

        Args:
            width: Sensor width in pixels.
            height: Sensor height in pixels.
            fov_horizontal_deg: Horizontal FOV in degrees.
            fov_vertical_deg: Vertical FOV in degrees.
            label: Human-readable label for this configuration.

        Returns:
            CameraCalibration with FOV-derived intrinsics.
        """
        return cls(
            width=width,
            height=height,
            fov_horizontal_deg=fov_horizontal_deg,
            fov_vertical_deg=fov_vertical_deg,
            label=label,
        )

    @classmethod
    def with_explicit_intrinsics(
        cls,
        width: int,
        height: int,
        fx: float,
        fy: float,
        cx: float,
        cy: float,
        fov_horizontal_deg: float = 4.0,
        fov_vertical_deg: float = 3.0,
        label: str = "explicit",
    ) -> "CameraCalibration":
        """Create a CameraCalibration with fully explicit intrinsics.

        Use when you have measured/calibrated fx, fy, cx, cy values from
        a real lens calibration procedure (e.g., OpenCV calibrateCamera).

        Args:
            width, height: Sensor resolution in pixels.
            fx, fy: Focal lengths in pixels.
            cx, cy: Principal point in pixels.
            fov_horizontal_deg, fov_vertical_deg: FOV for boundary checks.
            label: Calibration label.

        Returns:
            CameraCalibration with explicitly specified intrinsics.
        """
        return cls(
            width=width,
            height=height,
            fov_horizontal_deg=fov_horizontal_deg,
            fov_vertical_deg=fov_vertical_deg,
            fx_override=fx,
            fy_override=fy,
            cx_override=cx,
            cy_override=cy,
            label=label,
        )

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def fx(self) -> float:
        return self._fx

    @property
    def fy(self) -> float:
        return self._fy

    @property
    def cx(self) -> float:
        return self._cx

    @property
    def cy(self) -> float:
        return self._cy

    @property
    def width(self) -> int:
        return self._base.width

    @property
    def height(self) -> int:
        return self._base.height

    @property
    def fov_x_deg(self) -> float:
        return self._base.fov_x_deg

    @property
    def fov_y_deg(self) -> float:
        return self._base.fov_y_deg

    @property
    def half_fov_x_rad(self) -> float:
        return self._base.half_fov_x_rad

    @property
    def half_fov_y_rad(self) -> float:
        return self._base.half_fov_y_rad

    @property
    def has_overrides(self) -> bool:
        """True if any intrinsic was explicitly overridden."""
        return self._has_overrides

    @property
    def label(self) -> str:
        return self._label

    @property
    def base_intrinsics(self) -> CameraIntrinsics:
        """The underlying FOV-derived CameraIntrinsics object."""
        return self._base

    # ------------------------------------------------------------------
    # Projection / Inverse (using resolved fx/fy/cx/cy)
    # ------------------------------------------------------------------

    def project(self, theta_x_rad: float, theta_y_rad: float) -> Tuple[float, float]:
        """Project angular offsets to pixel coordinates using calibrated intrinsics."""
        u = self._cx + self._fx * math.tan(theta_x_rad)
        v = self._cy + self._fy * math.tan(theta_y_rad)
        return u, v

    def unproject(self, u: float, v: float) -> Tuple[float, float]:
        """Unproject pixel coordinates to angular offsets using calibrated intrinsics."""
        theta_x = math.atan((u - self._cx) / self._fx)
        theta_y = math.atan((v - self._cy) / self._fy)
        return theta_x, theta_y

    def is_in_fov(
        self, theta_x_rad: float, theta_y_rad: float, tol_rad: float = 1e-12
    ) -> bool:
        """Check if angular target position is within the nominal FOV."""
        within_x = abs(theta_x_rad) <= (self._base.half_fov_x_rad + tol_rad)
        within_y = abs(theta_y_rad) <= (self._base.half_fov_y_rad + tol_rad)
        return within_x and within_y

    def compute_angular_uncertainty(
        self,
        pixel_uncertainty: PixelUncertainty,
        theta_x_rad: float = 0.0,
        theta_y_rad: float = 0.0,
    ) -> AngularUncertainty:
        """Propagate pixel uncertainty to angular uncertainty at a given pointing angle.

        See CameraIntrinsics.compute_angular_uncertainty() for full documentation.
        """
        tan_x = math.tan(theta_x_rad)
        tan_y = math.tan(theta_y_rad)

        jacobian_x = 1.0 / (self._fx * (1.0 + tan_x ** 2))
        jacobian_y = 1.0 / (self._fy * (1.0 + tan_y ** 2))

        return AngularUncertainty(
            sigma_theta_x=pixel_uncertainty.sigma_u * abs(jacobian_x),
            sigma_theta_y=pixel_uncertainty.sigma_v * abs(jacobian_y),
            sigma_u_input=pixel_uncertainty.sigma_u,
            sigma_v_input=pixel_uncertainty.sigma_v,
            theta_x_eval=theta_x_rad,
            theta_y_eval=theta_y_rad,
        )

    def to_matrix(self) -> list:
        """Return the 3×3 camera intrinsics matrix K as a nested list.

        K = [[fx,  0, cx],
             [ 0, fy, cy],
             [ 0,  0,  1]]
        """
        return [
            [self._fx, 0.0,      self._cx],
            [0.0,      self._fy, self._cy],
            [0.0,      0.0,      1.0     ],
        ]

    def pointing_error_vs_base(
        self, theta_x_rad: float, theta_y_rad: float
    ) -> Tuple[float, float]:
        """Compute pointing error between this calibration and base FOV-derived intrinsics.

        Useful for calibration sensitivity experiments: projects a target at
        (theta_x, theta_y) using both this calibration and the FOV-derived base,
        then returns the pixel error (du, dv).

        Args:
            theta_x_rad: Target horizontal angular offset in radians.
            theta_y_rad: Target vertical angular offset in radians.

        Returns:
            (du, dv): Pixel-space pointing error (this - base).
        """
        u_this, v_this = self.project(theta_x_rad, theta_y_rad)
        u_base, v_base = self._base.project(theta_x_rad, theta_y_rad)
        return u_this - u_base, v_this - v_base

    def summary(self) -> str:
        """Return a human-readable calibration summary."""
        override_note = " [with explicit overrides]" if self._has_overrides else " [FOV-derived]"
        return (
            f"CameraCalibration '{self._label}'{override_note}:\n"
            f"  Resolution:  {self.width}×{self.height} px\n"
            f"  FOV:         {self.fov_x_deg:.4f}° × {self.fov_y_deg:.4f}°\n"
            f"  fx={self._fx:.6f} px   fy={self._fy:.6f} px\n"
            f"  cx={self._cx:.4f} px   cy={self._cy:.4f} px\n"
            f"  FOV-derived: fx={self._base.fx:.6f}  fy={self._base.fy:.6f}\n"
            f"  FOV-derived: cx={self._base.cx:.4f}  cy={self._base.cy:.4f}"
        )
