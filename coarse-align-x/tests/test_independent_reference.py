"""
Independent Reference Tests for Camera Projection
====================================================
All expected values are computed using ONLY NumPy and Python math —
ZERO imports from simulator.camera modules until the assertion comparison.

This ensures the production implementation is not tested against itself.

Reference formulas:
    fx_ref = (W/2) / tan(radians(FOV_x/2))
    fy_ref = (H/2) / tan(radians(FOV_y/2))
    cx_ref = W/2
    cy_ref = H/2

    project:   u = cx + fx * tan(theta_x)
               v = cy + fy * tan(theta_y)

    unproject: theta_x = atan((u - cx) / fx)
               theta_y = atan((v - cy) / fy)
"""

from __future__ import annotations

import math
import numpy as np
import pytest


# ===========================================================================
# SECTION A: Pure-NumPy reference calculations (no simulator imports)
# ===========================================================================

def numpy_focal_lengths(W: int, H: int, fov_x_deg: float, fov_y_deg: float):
    """Compute focal lengths from FOV using NumPy only."""
    fx = (W / 2.0) / np.tan(np.radians(fov_x_deg / 2.0))
    fy = (H / 2.0) / np.tan(np.radians(fov_y_deg / 2.0))
    cx = W / 2.0
    cy = H / 2.0
    return float(fx), float(fy), float(cx), float(cy)


def numpy_project(theta_x_rad: float, theta_y_rad: float,
                  fx: float, fy: float, cx: float, cy: float):
    """Project angle → pixel using NumPy only."""
    u = cx + fx * np.tan(theta_x_rad)
    v = cy + fy * np.tan(theta_y_rad)
    return float(u), float(v)


def numpy_unproject(u: float, v: float,
                    fx: float, fy: float, cx: float, cy: float):
    """Unproject pixel → angle using NumPy only."""
    theta_x = np.arctan((u - cx) / fx)
    theta_y = np.arctan((v - cy) / fy)
    return float(theta_x), float(theta_y)


# ===========================================================================
# SECTION B: Tests comparing production code against NumPy reference
# ===========================================================================

class TestIntrinsicsVsNumpyReference:
    """CameraIntrinsics verified against NumPy-only reference calculations."""

    def setup_method(self):
        # Import production code ONLY here — not used for reference values
        from simulator.camera.intrinsics import CameraIntrinsics
        self.W, self.H = 640, 480
        self.FOV_X, self.FOV_Y = 4.0, 3.0
        self.cam = CameraIntrinsics(self.W, self.H, self.FOV_X, self.FOV_Y)
        self.fx_ref, self.fy_ref, self.cx_ref, self.cy_ref = numpy_focal_lengths(
            self.W, self.H, self.FOV_X, self.FOV_Y
        )

    def test_fx_matches_numpy_reference(self):
        """Production fx must match NumPy-computed fx to < 1e-10 relative error."""
        rel_err = abs(self.cam.fx - self.fx_ref) / self.fx_ref
        assert rel_err < 1e-12, f"fx rel error = {rel_err:.2e}"

    def test_fy_matches_numpy_reference(self):
        rel_err = abs(self.cam.fy - self.fy_ref) / self.fy_ref
        assert rel_err < 1e-12, f"fy rel error = {rel_err:.2e}"

    def test_cx_matches_numpy_reference(self):
        assert abs(self.cam.cx - self.cx_ref) < 1e-12

    def test_cy_matches_numpy_reference(self):
        assert abs(self.cam.cy - self.cy_ref) < 1e-12

    @pytest.mark.parametrize("theta_x_deg, theta_y_deg", [
        (0.0, 0.0),
        (1.0, 0.0),
        (0.0, 1.0),
        (1.5, 1.0),
        (-1.99, -1.49),
        (1.99, 1.49),
        (-0.5, 0.75),
    ])
    def test_project_matches_numpy_reference(self, theta_x_deg, theta_y_deg):
        """Production project() must match NumPy reference to < 1e-10 px."""
        theta_x = math.radians(theta_x_deg)
        theta_y = math.radians(theta_y_deg)

        u_prod, v_prod = self.cam.project(theta_x, theta_y)
        u_ref, v_ref = numpy_project(
            theta_x, theta_y,
            self.fx_ref, self.fy_ref, self.cx_ref, self.cy_ref
        )

        assert abs(u_prod - u_ref) < 1e-10, (
            f"(θx={theta_x_deg}°, θy={theta_y_deg}°): "
            f"u_prod={u_prod:.10f}, u_ref={u_ref:.10f}"
        )
        assert abs(v_prod - v_ref) < 1e-10, (
            f"(θx={theta_x_deg}°, θy={theta_y_deg}°): "
            f"v_prod={v_prod:.10f}, v_ref={v_ref:.10f}"
        )

    @pytest.mark.parametrize("u_px, v_px", [
        (320.0, 240.0),   # principal point
        (0.0, 240.0),     # left edge
        (640.0, 240.0),   # right edge
        (320.0, 0.0),     # top edge
        (320.0, 480.0),   # bottom edge
        (0.0, 0.0),       # top-left corner
        (640.0, 480.0),   # bottom-right corner
        (400.0, 350.0),   # arbitrary interior point
    ])
    def test_unproject_matches_numpy_reference(self, u_px, v_px):
        """Production unproject() must match NumPy reference to < 1e-12 radians."""
        tx_prod, ty_prod = self.cam.unproject(u_px, v_px)
        tx_ref, ty_ref = numpy_unproject(
            u_px, v_px,
            self.fx_ref, self.fy_ref, self.cx_ref, self.cy_ref
        )

        assert abs(tx_prod - tx_ref) < 1e-12, (
            f"(u={u_px}, v={v_px}): theta_x_prod={tx_prod:.14f}, theta_x_ref={tx_ref:.14f}"
        )
        assert abs(ty_prod - ty_ref) < 1e-12, (
            f"(u={u_px}, v={v_px}): theta_y_prod={ty_prod:.14f}, theta_y_ref={ty_ref:.14f}"
        )


class TestProjectionRoundTripVsReference:
    """Round-trip verified against combined reference computation."""

    def test_project_then_numpy_unproject(self):
        """project() → NumPy unproject must recover original angle."""
        from simulator.camera.intrinsics import CameraIntrinsics
        cam = CameraIntrinsics(640, 480, 4.0, 3.0)
        fx, fy, cx, cy = numpy_focal_lengths(640, 480, 4.0, 3.0)

        test_angles_deg = [
            (0.0, 0.0), (1.0, 0.5), (-1.5, 1.2), (1.99, -1.49), (-1.99, -1.49)
        ]
        for tx_deg, ty_deg in test_angles_deg:
            tx = math.radians(tx_deg)
            ty = math.radians(ty_deg)

            # Production project
            u_prod, v_prod = cam.project(tx, ty)

            # NumPy unproject (independent)
            tx_rec, ty_rec = numpy_unproject(u_prod, v_prod, fx, fy, cx, cy)

            assert abs(tx_rec - tx) < 1e-12, (
                f"Round-trip error at ({tx_deg}°, {ty_deg}°): {abs(tx_rec - tx):.2e} rad"
            )
            assert abs(ty_rec - ty) < 1e-12

    def test_numpy_project_then_unproject(self):
        """NumPy project → production unproject must recover original angle."""
        from simulator.camera.intrinsics import CameraIntrinsics
        cam = CameraIntrinsics(640, 480, 4.0, 3.0)
        fx, fy, cx, cy = numpy_focal_lengths(640, 480, 4.0, 3.0)

        test_angles_deg = [(0.5, 0.3), (-1.0, 1.0), (1.8, -1.3)]
        for tx_deg, ty_deg in test_angles_deg:
            tx = math.radians(tx_deg)
            ty = math.radians(ty_deg)

            # NumPy project (independent)
            u_ref, v_ref = numpy_project(tx, ty, fx, fy, cx, cy)

            # Production unproject
            tx_rec, ty_rec = cam.unproject(u_ref, v_ref)

            assert abs(tx_rec - tx) < 1e-12
            assert abs(ty_rec - ty) < 1e-12


class TestAngularUncertaintyVsAnalyticalDerivative:
    """Uncertainty propagation verified against analytical partial derivative."""

    def test_jacobian_vs_finite_difference(self):
        """
        Production Jacobian sigma_theta_x / sigma_u must match
        finite-difference approximation of d(arctan((u-cx)/fx))/du.
        """
        from simulator.camera.intrinsics import CameraIntrinsics, PixelUncertainty
        cam = CameraIntrinsics(640, 480, 4.0, 3.0)

        # Finite-difference Jacobian at boresight
        eps_u = 1e-6
        u0 = cam.cx
        theta_x_plus, _ = cam.unproject(u0 + eps_u, cam.cy)
        theta_x_minus, _ = cam.unproject(u0 - eps_u, cam.cy)
        fd_jacobian_x = (theta_x_plus - theta_x_minus) / (2 * eps_u)

        # Analytical Jacobian at boresight = 1 / fx (since tan(0) = 0)
        analytical_jacobian_x = 1.0 / cam.fx

        # Propagated via production method
        pu = PixelUncertainty(sigma_u=1.0, sigma_v=1.0)
        au = cam.compute_angular_uncertainty(pu, theta_x_rad=0.0, theta_y_rad=0.0)

        assert abs(fd_jacobian_x - analytical_jacobian_x) < 1e-8, (
            f"FD Jacobian {fd_jacobian_x:.10f} != analytical {analytical_jacobian_x:.10f}"
        )
        assert abs(au.sigma_theta_x - analytical_jacobian_x) < 1e-12, (
            f"Production sigma_theta_x {au.sigma_theta_x:.10f} != analytical {analytical_jacobian_x:.10f}"
        )

    def test_off_axis_jacobian_vs_finite_difference(self):
        """Off-axis Jacobian must match finite-difference at theta_x = 1.0°."""
        from simulator.camera.intrinsics import CameraIntrinsics, PixelUncertainty
        cam = CameraIntrinsics(640, 480, 4.0, 3.0)

        theta_x_eval = math.radians(1.0)
        u_eval = cam.cx + cam.fx * math.tan(theta_x_eval)

        eps_u = 1e-6
        theta_x_plus, _ = cam.unproject(u_eval + eps_u, cam.cy)
        theta_x_minus, _ = cam.unproject(u_eval - eps_u, cam.cy)
        fd_jacobian = (theta_x_plus - theta_x_minus) / (2 * eps_u)

        # Production Jacobian
        pu = PixelUncertainty(sigma_u=1.0, sigma_v=1.0)
        au = cam.compute_angular_uncertainty(pu, theta_x_rad=theta_x_eval, theta_y_rad=0.0)

        assert abs(au.sigma_theta_x - fd_jacobian) < 1e-8, (
            f"Off-axis Jacobian mismatch: prod={au.sigma_theta_x:.10f}, FD={fd_jacobian:.10f}"
        )


class TestFovConsistencyVsNumericalVerification:
    """FOV consistency verified numerically (independent of intrinsics formula)."""

    def test_fov_matches_pixel_extent(self):
        """
        If focal length is correct, then a target at theta = half_fov should
        project exactly to the sensor edge pixel (u=W or u=0).
        This verifies the physical consistency of the FOV model.
        """
        from simulator.camera.intrinsics import CameraIntrinsics
        cam = CameraIntrinsics(640, 480, 4.0, 3.0)

        # NumPy-reference focal lengths
        fx_ref, fy_ref, cx_ref, cy_ref = numpy_focal_lengths(640, 480, 4.0, 3.0)

        # Project half-FOV angle using reference
        half_fov_x = np.radians(4.0 / 2.0)
        half_fov_y = np.radians(3.0 / 2.0)

        u_at_half_fov, _ = numpy_project(half_fov_x, 0.0, fx_ref, fy_ref, cx_ref, cy_ref)
        _, v_at_half_fov = numpy_project(0.0, half_fov_y, fx_ref, fy_ref, cx_ref, cy_ref)

        # These should be exactly at the sensor edge
        assert abs(u_at_half_fov - 640.0) < 1e-9, f"half-FOV_x does not project to edge: {u_at_half_fov}"
        assert abs(v_at_half_fov - 480.0) < 1e-9, f"half-FOV_y does not project to edge: {v_at_half_fov}"

        # Production must agree
        u_prod, _ = cam.project(float(half_fov_x), 0.0)
        _, v_prod = cam.project(0.0, float(half_fov_y))
        assert abs(u_prod - 640.0) < 1e-9
        assert abs(v_prod - 480.0) < 1e-9
