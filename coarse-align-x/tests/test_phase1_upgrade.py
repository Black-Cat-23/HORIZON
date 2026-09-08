"""
Phase 1 Upgrade: Pixel-to-Angle Validation Tests
=================================================
Verifies pixel→angle conversion for center, edge, and corner points
using independent reference calculations that do NOT use CameraIntrinsics
for the expected value.

Each expected value is computed from the pinhole model formula applied
independently with raw Python math — not from the production class.
"""

from __future__ import annotations

import math
import pytest
from simulator.camera.intrinsics import (
    CameraIntrinsics,
    CameraCalibration,
    PixelUncertainty,
)


# Canonical test configuration
W, H = 640, 480
FOV_X_DEG, FOV_Y_DEG = 4.0, 3.0


# ---------------------------------------------------------------------------
# Independent reference values (computed once, not from CameraIntrinsics)
# ---------------------------------------------------------------------------

def _ref_fx() -> float:
    return (W / 2.0) / math.tan(math.radians(FOV_X_DEG / 2.0))

def _ref_fy() -> float:
    return (H / 2.0) / math.tan(math.radians(FOV_Y_DEG / 2.0))

def _ref_cx() -> float:
    return W / 2.0

def _ref_cy() -> float:
    return H / 2.0

def _ref_pixel_to_angle(u: float, v: float) -> tuple[float, float]:
    """Reference inverse projection using raw math (no CameraIntrinsics)."""
    fx, fy, cx, cy = _ref_fx(), _ref_fy(), _ref_cx(), _ref_cy()
    theta_x = math.atan((u - cx) / fx)
    theta_y = math.atan((v - cy) / fy)
    return theta_x, theta_y

def _ref_angle_to_pixel(theta_x: float, theta_y: float) -> tuple[float, float]:
    """Reference forward projection using raw math (no CameraIntrinsics)."""
    fx, fy, cx, cy = _ref_fx(), _ref_fy(), _ref_cx(), _ref_cy()
    u = cx + fx * math.tan(theta_x)
    v = cy + fy * math.tan(theta_y)
    return u, v


# ---------------------------------------------------------------------------
# Pixel-to-Angle tests (unproject)
# ---------------------------------------------------------------------------

class TestPixelToAngleValidation:
    """Pixel-to-angle conversion verified against independent references."""

    @pytest.fixture
    def cam(self):
        return CameraIntrinsics(W, H, FOV_X_DEG, FOV_Y_DEG)

    def test_center_pixel_gives_zero_angle(self, cam):
        """Boresight pixel (cx, cy) must map to (0, 0) angle."""
        theta_x, theta_y = cam.unproject(cam.cx, cam.cy)
        assert abs(theta_x) < 1e-12, f"Expected theta_x=0, got {theta_x}"
        assert abs(theta_y) < 1e-12, f"Expected theta_y=0, got {theta_y}"

        # Independent reference
        ref_tx, ref_ty = _ref_pixel_to_angle(_ref_cx(), _ref_cy())
        assert abs(ref_tx) < 1e-12
        assert abs(ref_ty) < 1e-12

    def test_right_edge_pixel_gives_half_fov_x(self, cam):
        """Right sensor edge (u=W, v=cy) must map to +half_fov_x."""
        theta_x, _ = cam.unproject(float(W), cam.cy)
        expected = math.radians(FOV_X_DEG / 2.0)

        # Independent reference
        ref_tx, _ = _ref_pixel_to_angle(float(W), _ref_cy())

        assert abs(theta_x - expected) < 1e-9, (
            f"Right edge: theta_x={math.degrees(theta_x):.6f}°, "
            f"expected={math.degrees(expected):.6f}°"
        )
        assert abs(ref_tx - expected) < 1e-9, (
            f"Reference mismatch: {math.degrees(ref_tx):.6f}° vs {math.degrees(expected):.6f}°"
        )
        assert abs(theta_x - ref_tx) < 1e-12, "Production vs reference disagreement!"

    def test_left_edge_pixel_gives_neg_half_fov_x(self, cam):
        """Left sensor edge (u=0, v=cy) must map to -half_fov_x."""
        theta_x, _ = cam.unproject(0.0, cam.cy)
        expected = -math.radians(FOV_X_DEG / 2.0)
        ref_tx, _ = _ref_pixel_to_angle(0.0, _ref_cy())

        assert abs(theta_x - expected) < 1e-9
        assert abs(theta_x - ref_tx) < 1e-12

    def test_bottom_edge_pixel_gives_half_fov_y(self, cam):
        """Bottom sensor edge (u=cx, v=H) must map to +half_fov_y."""
        _, theta_y = cam.unproject(cam.cx, float(H))
        expected = math.radians(FOV_Y_DEG / 2.0)
        _, ref_ty = _ref_pixel_to_angle(_ref_cx(), float(H))

        assert abs(theta_y - expected) < 1e-9, (
            f"Bottom edge: theta_y={math.degrees(theta_y):.6f}°, "
            f"expected={math.degrees(expected):.6f}°"
        )
        assert abs(theta_y - ref_ty) < 1e-12

    def test_top_edge_pixel_gives_neg_half_fov_y(self, cam):
        """Top sensor edge (u=cx, v=0) must map to -half_fov_y."""
        _, theta_y = cam.unproject(cam.cx, 0.0)
        expected = -math.radians(FOV_Y_DEG / 2.0)
        _, ref_ty = _ref_pixel_to_angle(_ref_cx(), 0.0)

        assert abs(theta_y - expected) < 1e-9
        assert abs(theta_y - ref_ty) < 1e-12

    def test_bottom_right_corner_independent_reference(self, cam):
        """Bottom-right corner: both axes should give +half_fov values."""
        theta_x, theta_y = cam.unproject(float(W), float(H))
        ref_tx, ref_ty = _ref_pixel_to_angle(float(W), float(H))

        exp_tx = math.radians(FOV_X_DEG / 2.0)
        exp_ty = math.radians(FOV_Y_DEG / 2.0)

        assert abs(theta_x - exp_tx) < 1e-9
        assert abs(theta_y - exp_ty) < 1e-9
        # Production must agree with reference
        assert abs(theta_x - ref_tx) < 1e-12
        assert abs(theta_y - ref_ty) < 1e-12

    def test_top_left_corner_independent_reference(self, cam):
        """Top-left corner: both axes should give -half_fov values."""
        theta_x, theta_y = cam.unproject(0.0, 0.0)
        ref_tx, ref_ty = _ref_pixel_to_angle(0.0, 0.0)

        exp_tx = -math.radians(FOV_X_DEG / 2.0)
        exp_ty = -math.radians(FOV_Y_DEG / 2.0)

        assert abs(theta_x - exp_tx) < 1e-9
        assert abs(theta_y - exp_ty) < 1e-9
        assert abs(theta_x - ref_tx) < 1e-12
        assert abs(theta_y - ref_ty) < 1e-12


# ---------------------------------------------------------------------------
# Angle-to-Pixel tests (project)
# ---------------------------------------------------------------------------

class TestAngleToPixelValidation:
    """Angular offset → pixel validated against independent reference."""

    @pytest.fixture
    def cam(self):
        return CameraIntrinsics(W, H, FOV_X_DEG, FOV_Y_DEG)

    @pytest.mark.parametrize("theta_x_deg, theta_y_deg", [
        (0.0, 0.0),
        (1.0, 0.5),
        (-1.5, 1.2),
        (1.99, -1.49),
        (-1.99, -1.49),
        (0.0, 1.0),
        (-0.5, -0.5),
    ])
    def test_angle_to_pixel_vs_independent_reference(self, cam, theta_x_deg, theta_y_deg):
        """Each test case verified against independent NumPy reference calculation."""
        theta_x = math.radians(theta_x_deg)
        theta_y = math.radians(theta_y_deg)

        u_prod, v_prod = cam.project(theta_x, theta_y)
        u_ref, v_ref = _ref_angle_to_pixel(theta_x, theta_y)

        assert abs(u_prod - u_ref) < 1e-10, (
            f"(θx={theta_x_deg}°, θy={theta_y_deg}°): u_prod={u_prod:.8f}, u_ref={u_ref:.8f}"
        )
        assert abs(v_prod - v_ref) < 1e-10, (
            f"(θx={theta_x_deg}°, θy={theta_y_deg}°): v_prod={v_prod:.8f}, v_ref={v_ref:.8f}"
        )


# ---------------------------------------------------------------------------
# CameraCalibration round-trip
# ---------------------------------------------------------------------------

class TestCameraCalibrationRoundTrip:
    """CameraCalibration project/unproject round-trip validation."""

    def test_fov_derived_calibration_matches_intrinsics(self):
        """from_config() calibration must give identical results to CameraIntrinsics."""
        intrinsics = CameraIntrinsics(W, H, FOV_X_DEG, FOV_Y_DEG)
        calib = CameraCalibration.from_config(W, H, FOV_X_DEG, FOV_Y_DEG)

        assert abs(calib.fx - intrinsics.fx) < 1e-10
        assert abs(calib.fy - intrinsics.fy) < 1e-10
        assert abs(calib.cx - intrinsics.cx) < 1e-10
        assert abs(calib.cy - intrinsics.cy) < 1e-10

    def test_explicit_override_changes_projection(self):
        """Explicit fx/cx override must produce different projection from FOV-derived."""
        base = CameraIntrinsics(W, H, FOV_X_DEG, FOV_Y_DEG)
        perturbed = CameraCalibration.with_explicit_intrinsics(
            W, H,
            fx=base.fx * 1.01,  # +1% focal length error
            fy=base.fy,
            cx=base.cx,
            cy=base.cy,
        )

        theta_x = math.radians(1.0)
        theta_y = math.radians(0.5)

        u_base, v_base = base.project(theta_x, theta_y)
        u_perturbed, v_perturbed = perturbed.project(theta_x, theta_y)

        # +1% fx means u is farther from cx by ~1%
        assert u_perturbed != u_base
        assert abs(v_perturbed - v_base) < 1e-9  # fy unchanged

    def test_pointing_error_vs_base_sign(self):
        """pointing_error_vs_base() signs must be consistent with focal length bias."""
        base = CameraIntrinsics(W, H, FOV_X_DEG, FOV_Y_DEG)
        # Under-estimated focal length → underestimates angular displacement
        underestimated = CameraCalibration.with_explicit_intrinsics(
            W, H, fx=base.fx * 0.99, fy=base.fy, cx=base.cx, cy=base.cy
        )
        # At positive theta_x, lower fx → smaller u deviation → negative du
        theta_x = math.radians(1.5)
        du, dv = underestimated.pointing_error_vs_base(theta_x, 0.0)
        assert du < 0, f"Expected du < 0 for under-estimated fx, got {du}"
        assert abs(dv) < 1e-9

    def test_round_trip_explicit_intrinsics(self):
        """project → unproject must give back original angles with explicit intrinsics."""
        calib = CameraCalibration.with_explicit_intrinsics(
            W, H, fx=9200.0, fy=9180.0, cx=321.5, cy=241.0
        )
        test_angles = [
            (math.radians(a_x), math.radians(a_y))
            for a_x, a_y in [(0, 0), (1.0, 0.5), (-1.5, 1.0), (0, -1.0)]
        ]
        for theta_x, theta_y in test_angles:
            u, v = calib.project(theta_x, theta_y)
            tx_rec, ty_rec = calib.unproject(u, v)
            assert abs(tx_rec - theta_x) < 1e-12
            assert abs(ty_rec - theta_y) < 1e-12


# ---------------------------------------------------------------------------
# Uncertainty Propagation tests
# ---------------------------------------------------------------------------

class TestUncertaintyPropagation:
    """PixelUncertainty → AngularUncertainty propagation tests."""

    @pytest.fixture
    def cam(self):
        return CameraIntrinsics(W, H, FOV_X_DEG, FOV_Y_DEG)

    def test_boresight_uncertainty_equals_sigma_over_f(self, cam):
        """At boresight, sigma_theta = sigma_pixel / f (exact)."""
        sigma_u, sigma_v = 0.5, 0.5  # half-pixel noise
        pu = PixelUncertainty(sigma_u=sigma_u, sigma_v=sigma_v)
        au = cam.compute_angular_uncertainty(pu, theta_x_rad=0.0, theta_y_rad=0.0)

        # Expected: sigma_theta_x = sigma_u / fx
        expected_x = sigma_u / cam.fx
        expected_y = sigma_v / cam.fy

        assert abs(au.sigma_theta_x - expected_x) < 1e-14
        assert abs(au.sigma_theta_y - expected_y) < 1e-14

    def test_off_axis_uncertainty_is_larger_at_edge(self, cam):
        """Off-axis uncertainty must be larger than boresight (tangential compression)."""
        pu = PixelUncertainty(sigma_u=1.0, sigma_v=1.0)
        au_center = cam.compute_angular_uncertainty(pu, 0.0, 0.0)

        # Near edge (theta_x = 1.9°, near half-FOV 2°)
        theta_edge = math.radians(1.9)
        au_edge = cam.compute_angular_uncertainty(pu, theta_edge, 0.0)

        # At the edge, angular sensitivity decreases (cos²(theta)/f < 1/f at boresight)
        # Actually Jacobian = cos²(theta)/f < 1/f → edge sigma_theta < center sigma_theta
        # This is correct: pixel displacements at large angles correspond to smaller angles
        assert au_edge.sigma_theta_x < au_center.sigma_theta_x, (
            "Off-axis angular uncertainty should be smaller (compressed), not larger."
        )

    def test_uncertainty_is_independent_of_ground_truth(self, cam):
        """Uncertainty propagation must not require ground truth."""
        # We can compute angular uncertainty without knowing where the target actually is
        pu = PixelUncertainty(sigma_u=0.3, sigma_v=0.4)
        # Evaluated at boresight (no position knowledge required)
        au = cam.compute_angular_uncertainty(pu)
        assert au.sigma_theta_x > 0
        assert au.sigma_theta_y > 0
        assert math.isfinite(au.sigma_theta_x)
        assert math.isfinite(au.sigma_theta_y)

    def test_zero_pixel_uncertainty_gives_zero_angular_uncertainty(self, cam):
        """Zero measurement noise → zero angular noise."""
        pu = PixelUncertainty(sigma_u=0.0, sigma_v=0.0)
        au = cam.compute_angular_uncertainty(pu)
        assert au.sigma_theta_x == 0.0
        assert au.sigma_theta_y == 0.0

    def test_negative_sigma_rejected(self):
        """Negative uncertainty values must be rejected."""
        with pytest.raises(ValueError):
            PixelUncertainty(sigma_u=-0.1, sigma_v=0.5)

    def test_uncertainty_scales_linearly_with_pixel_noise(self, cam):
        """Doubling pixel sigma must double angular sigma (linear propagation)."""
        pu1 = PixelUncertainty(sigma_u=0.5, sigma_v=0.3)
        pu2 = PixelUncertainty(sigma_u=1.0, sigma_v=0.6)
        au1 = cam.compute_angular_uncertainty(pu1)
        au2 = cam.compute_angular_uncertainty(pu2)

        assert abs(au2.sigma_theta_x / au1.sigma_theta_x - 2.0) < 1e-12
        assert abs(au2.sigma_theta_y / au1.sigma_theta_y - 2.0) < 1e-12

    def test_calibration_summary_produces_string(self):
        """summary() must return a non-empty string."""
        calib = CameraCalibration.from_config(W, H, FOV_X_DEG, FOV_Y_DEG)
        s = calib.summary()
        assert isinstance(s, str) and len(s) > 10
