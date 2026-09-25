"""
HORIZON Optional Lens Distortion Model
==========================================
Implements the Brown-Conrady radial and tangential lens distortion model.

This model is DISABLED BY DEFAULT (all coefficients = 0.0 → ideal pinhole).
Enable only when validated against a real calibrated lens.

Coordinate convention: image pixel coordinates (u, v) in the IMAGE system.
See simulator/camera/coordinate_contract.py for full convention reference.

Mathematical reference:
  Brown, D.C. (1966). Decentering distortion of lenses.
  Photogrammetric Engineering, 32(3), 444–462.

Distortion model:
  Given undistorted normalized coordinates (x_n, y_n):
    x_n = (u - cx) / fx
    y_n = (v - cy) / fy

  Radial distortion factor:
    r² = x_n² + y_n²
    r_factor = 1 + k1*r² + k2*r⁴ + k3*r⁶

  Tangential distortion:
    dx = 2*p1*x_n*y_n + p2*(r² + 2*x_n²)
    dy = p1*(r² + 2*y_n²) + 2*p2*x_n*y_n

  Distorted normalized coordinates:
    x_d = x_n * r_factor + dx
    y_d = y_n * r_factor + dy

  Distorted pixel coordinates:
    u_d = fx * x_d + cx
    v_d = fy * y_d + cy
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Final, Tuple


@dataclass
class LensDistortionModel:
    """Brown-Conrady radial and tangential lens distortion model.

    All coefficients default to 0.0 (ideal pinhole, no distortion).
    The model is enabled only if at least one coefficient is non-zero.

    Parameters:
        k1: First radial distortion coefficient.
        k2: Second radial distortion coefficient.
        k3: Third radial distortion coefficient.
        p1: First tangential distortion coefficient.
        p2: Second tangential distortion coefficient.
    """
    k1: float = 0.0
    k2: float = 0.0
    k3: float = 0.0
    p1: float = 0.0
    p2: float = 0.0

    @property
    def enabled(self) -> bool:
        """True if any coefficient is non-zero (distortion is active)."""
        return any(c != 0.0 for c in (self.k1, self.k2, self.k3, self.p1, self.p2))

    @property
    def radial_coefficients(self) -> Tuple[float, float, float]:
        """Radial distortion coefficients (k1, k2, k3)."""
        return (self.k1, self.k2, self.k3)

    @property
    def tangential_coefficients(self) -> Tuple[float, float]:
        """Tangential distortion coefficients (p1, p2)."""
        return (self.p1, self.p2)

    def distort(
        self,
        u_ideal: float,
        v_ideal: float,
        fx: float,
        fy: float,
        cx: float,
        cy: float,
    ) -> Tuple[float, float]:
        """Apply lens distortion to an ideal (undistorted) pixel coordinate.

        Args:
            u_ideal: Undistorted horizontal pixel coordinate.
            v_ideal: Undistorted vertical pixel coordinate.
            fx: Horizontal focal length in pixels.
            fy: Vertical focal length in pixels.
            cx: Principal point horizontal coordinate.
            cy: Principal point vertical coordinate.

        Returns:
            (u_distorted, v_distorted): Pixel coordinates after distortion.

        Notes:
            If distortion is disabled (all coefficients = 0), returns the
            input coordinates unchanged.
        """
        if not self.enabled:
            return u_ideal, v_ideal

        # Normalize to camera coordinates
        x_n = (u_ideal - cx) / fx
        y_n = (v_ideal - cy) / fy

        r2 = x_n * x_n + y_n * y_n
        r4 = r2 * r2
        r6 = r2 * r4

        # Radial factor
        r_factor = 1.0 + self.k1 * r2 + self.k2 * r4 + self.k3 * r6

        # Tangential components
        dx = 2.0 * self.p1 * x_n * y_n + self.p2 * (r2 + 2.0 * x_n * x_n)
        dy = self.p1 * (r2 + 2.0 * y_n * y_n) + 2.0 * self.p2 * x_n * y_n

        # Distorted normalized coordinates
        x_d = x_n * r_factor + dx
        y_d = y_n * r_factor + dy

        # Back to pixel coordinates
        u_d = fx * x_d + cx
        v_d = fy * y_d + cy

        return u_d, v_d

    def undistort(
        self,
        u_distorted: float,
        v_distorted: float,
        fx: float,
        fy: float,
        cx: float,
        cy: float,
        max_iterations: int = 50,
        tolerance: float = 1e-10,
    ) -> Tuple[float, float]:
        """Invert lens distortion to recover ideal pixel coordinates.

        Uses iterative Newton-Raphson refinement starting from the distorted
        coordinate as the initial guess.

        Args:
            u_distorted: Distorted horizontal pixel coordinate.
            v_distorted: Distorted vertical pixel coordinate.
            fx: Horizontal focal length in pixels.
            fy: Vertical focal length in pixels.
            cx: Principal point horizontal coordinate.
            cy: Principal point vertical coordinate.
            max_iterations: Maximum Newton iterations (default 50).
            tolerance: Convergence tolerance in normalized units (default 1e-10).

        Returns:
            (u_ideal, v_ideal): Recovered undistorted pixel coordinates.

        Notes:
            If distortion is disabled (all coefficients = 0), returns the
            input coordinates unchanged.
        """
        if not self.enabled:
            return u_distorted, v_distorted

        # Initial guess: distorted coordinate as starting point
        x_n = (u_distorted - cx) / fx
        y_n = (v_distorted - cy) / fy

        # Target distorted normalized
        x_d_target = x_n
        y_d_target = y_n

        for _ in range(max_iterations):
            r2 = x_n * x_n + y_n * y_n
            r4 = r2 * r2
            r6 = r2 * r4

            r_factor = 1.0 + self.k1 * r2 + self.k2 * r4 + self.k3 * r6
            dx = 2.0 * self.p1 * x_n * y_n + self.p2 * (r2 + 2.0 * x_n * x_n)
            dy = self.p1 * (r2 + 2.0 * y_n * y_n) + 2.0 * self.p2 * x_n * y_n

            x_err = x_n * r_factor + dx - x_d_target
            y_err = y_n * r_factor + dy - y_d_target

            if abs(x_err) < tolerance and abs(y_err) < tolerance:
                break

            # Gauss–Seidel update (first-order fixed-point iteration)
            x_n -= x_err / r_factor
            y_n -= y_err / r_factor

        u_ideal = fx * x_n + cx
        v_ideal = fy * y_n + cy
        return u_ideal, v_ideal

    def undistort_angle(
        self,
        theta_x_rad: float,
        theta_y_rad: float,
        fx: float,
        fy: float,
        cx: float,
        cy: float,
    ) -> Tuple[float, float]:
        """Apply undistortion in angular domain.

        Projects the angle to a distorted pixel, undistorts, then unprojects
        back to angle. Useful for comparing ideal vs distorted angular error.

        Args:
            theta_x_rad: Ideal horizontal angular offset in radians.
            theta_y_rad: Ideal vertical angular offset in radians.
            fx, fy, cx, cy: Camera intrinsics.

        Returns:
            (theta_x_distorted, theta_y_distorted): Angular offsets observed
            when lens distortion is present.
        """
        # Ideal pixel
        u_ideal = cx + fx * math.tan(theta_x_rad)
        v_ideal = cy + fy * math.tan(theta_y_rad)

        # Apply distortion
        u_d, v_d = self.distort(u_ideal, v_ideal, fx, fy, cx, cy)

        # Unproject distorted pixel back to angles
        theta_x_d = math.atan2(u_d - cx, fx)
        theta_y_d = math.atan2(v_d - cy, fy)
        return theta_x_d, theta_y_d

    def summary(self) -> str:
        """Return a human-readable summary of the distortion model."""
        status = "ENABLED" if self.enabled else "DISABLED (ideal pinhole)"
        return (
            f"LensDistortionModel [{status}]\n"
            f"  Radial:     k1={self.k1:.6e}  k2={self.k2:.6e}  k3={self.k3:.6e}\n"
            f"  Tangential: p1={self.p1:.6e}  p2={self.p2:.6e}"
        )

    def __repr__(self) -> str:
        return (
            f"LensDistortionModel("
            f"k1={self.k1}, k2={self.k2}, k3={self.k3}, "
            f"p1={self.p1}, p2={self.p2})"
        )


# ---------------------------------------------------------------------------
# Pre-defined distortion presets for experiment use
# ---------------------------------------------------------------------------

#: Ideal pinhole — no distortion
IDEAL_PINHOLE: Final = LensDistortionModel()

#: Mild barrel distortion (typical wide-angle lens, ~1% at edge)
MILD_BARREL: Final = LensDistortionModel(k1=-0.01, k2=0.0005)

#: Moderate barrel distortion (aggressive wide-angle, ~5% at edge)
MODERATE_BARREL: Final = LensDistortionModel(k1=-0.05, k2=0.002)

#: Mild pincushion distortion (telephoto lens)
MILD_PINCUSHION: Final = LensDistortionModel(k1=0.01, k2=0.0)


