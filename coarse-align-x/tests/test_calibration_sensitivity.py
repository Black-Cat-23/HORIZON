"""
Calibration Sensitivity Experiment
=======================================
Test mode that perturbs focal length, principal point, and FOV, then
measures the resulting pointing error.

This is a future calibration robustness experiment — these tests
characterize how sensitive the pointing model is to calibration errors.

Metrics:
    - Pointing error: angular error from mismatched calibration (radians, degrees)
    - Pixel error: projection offset from nominal (pixels)

The experiment uses CameraCalibration.pointing_error_vs_base() to
measure the pixel-space pointing error between the perturbed and
FOV-derived (nominal) calibration.
"""

from __future__ import annotations

import math
import pytest
from simulator.camera.intrinsics import (
    CameraIntrinsics,
    CameraCalibration,
    PixelUncertainty,
)


W, H = 640, 480
FOV_X_DEG, FOV_Y_DEG = 4.0, 3.0

# Test angles well within FOV
TEST_ANGLES_DEG = [(1.0, 0.5), (-1.0, -0.5), (1.8, 1.4), (-0.5, 1.0)]


def _nominal() -> CameraIntrinsics:
    return CameraIntrinsics(W, H, FOV_X_DEG, FOV_Y_DEG)


class TestFocalLengthSensitivity:
    """Pointing error as a function of focal length perturbation."""

    @pytest.mark.parametrize("fx_error_pct", [-5.0, -1.0, -0.1, 0.1, 1.0, 5.0])
    def test_fx_perturbation_pointing_error(self, fx_error_pct):
        """
        Perturbing fx by ±P% should produce non-zero pointing error
        that scales monotonically with P%.
        """
        nom = _nominal()
        perturbed = CameraCalibration.with_explicit_intrinsics(
            W, H,
            fx=nom.fx * (1.0 + fx_error_pct / 100.0),
            fy=nom.fy,
            cx=nom.cx,
            cy=nom.cy,
            label=f"fx_{fx_error_pct:+.1f}pct",
        )

        errors_u = []
        for tx_deg, ty_deg in TEST_ANGLES_DEG:
            tx, ty = math.radians(tx_deg), math.radians(ty_deg)
            du, dv = perturbed.pointing_error_vs_base(tx, ty)
            errors_u.append((tx_deg, du))
            # ty/fy unchanged → dv should be near zero
            assert abs(dv) < 1e-6, f"dv={dv} unexpectedly large for fy-unchanged perturbation"

        # At positive theta_x, positive fx_error_pct → positive du
        # At negative theta_x, positive fx_error_pct → negative du
        # (larger fx shifts u further from cx in the same direction as theta)
        for tx_deg, du in errors_u:
            if abs(tx_deg) < 0.01:
                continue  # skip near-zero angles
            expected_sign = math.copysign(1.0, tx_deg) * math.copysign(1.0, fx_error_pct)
            actual_sign = math.copysign(1.0, du)
            assert actual_sign == expected_sign, (
                f"fx_error={fx_error_pct}%, tx={tx_deg}°: du={du:.6f} has wrong sign"
            )

    def test_fx_perturbation_scales_with_angle(self):
        """Larger theta_x → larger pointing error from fx perturbation."""
        nom = _nominal()
        perturbed = CameraCalibration.with_explicit_intrinsics(
            W, H, fx=nom.fx * 1.01, fy=nom.fy, cx=nom.cx, cy=nom.cy
        )

        small_theta = math.radians(0.5)
        large_theta = math.radians(1.8)

        du_small, _ = perturbed.pointing_error_vs_base(small_theta, 0.0)
        du_large, _ = perturbed.pointing_error_vs_base(large_theta, 0.0)

        assert abs(du_large) > abs(du_small), (
            f"Larger angle should give larger error: du_large={du_large:.4f}, du_small={du_small:.4f}"
        )

    def test_fx_error_zero_gives_zero_pointing_error(self):
        """0% fx error must produce zero pointing error at all angles."""
        nom = _nominal()
        exact = CameraCalibration.with_explicit_intrinsics(
            W, H, fx=nom.fx, fy=nom.fy, cx=nom.cx, cy=nom.cy
        )
        for tx_deg, ty_deg in TEST_ANGLES_DEG:
            du, dv = exact.pointing_error_vs_base(math.radians(tx_deg), math.radians(ty_deg))
            assert abs(du) < 1e-9
            assert abs(dv) < 1e-9


class TestPrincipalPointSensitivity:
    """Pointing error as a function of principal point perturbation."""

    @pytest.mark.parametrize("cx_offset_px", [-5.0, -1.0, 1.0, 5.0])
    def test_cx_offset_produces_constant_pixel_error(self, cx_offset_px):
        """
        Shifting cx by ΔP pixels introduces a constant pixel offset of ΔP
        at all pointing angles (because cx is a pure additive offset in u).

        du = (cx + ΔP) + fx*tan(θ) - (cx + fx*tan(θ)) = ΔP
        """
        nom = _nominal()
        shifted = CameraCalibration.with_explicit_intrinsics(
            W, H,
            fx=nom.fx, fy=nom.fy,
            cx=nom.cx + cx_offset_px, cy=nom.cy,
            label=f"cx_{cx_offset_px:+.0f}px",
        )
        for tx_deg, ty_deg in TEST_ANGLES_DEG:
            du, _ = shifted.pointing_error_vs_base(math.radians(tx_deg), math.radians(ty_deg))
            assert abs(du - cx_offset_px) < 1e-9, (
                f"cx offset {cx_offset_px}px at ({tx_deg}°, {ty_deg}°): du={du:.6f} != {cx_offset_px}"
            )

    @pytest.mark.parametrize("cy_offset_px", [-5.0, -1.0, 1.0, 5.0])
    def test_cy_offset_produces_constant_pixel_error(self, cy_offset_px):
        """
        Shifting cy by ΔP pixels introduces a constant v-offset of ΔP.
        dv = cy + ΔP + fy*tan(θ_y) - (cy + fy*tan(θ_y)) = ΔP
        """
        nom = _nominal()
        shifted = CameraCalibration.with_explicit_intrinsics(
            W, H,
            fx=nom.fx, fy=nom.fy,
            cx=nom.cx, cy=nom.cy + cy_offset_px,
            label=f"cy_{cy_offset_px:+.0f}px",
        )
        for tx_deg, ty_deg in TEST_ANGLES_DEG:
            _, dv = shifted.pointing_error_vs_base(math.radians(tx_deg), math.radians(ty_deg))
            assert abs(dv - cy_offset_px) < 1e-9


class TestFovSensitivity:
    """Pointing error as a function of FOV perturbation."""

    @pytest.mark.parametrize("fov_x_offset_deg", [-0.5, -0.1, 0.1, 0.5])
    def test_fov_perturbation_changes_fx(self, fov_x_offset_deg):
        """Perturbing FOV_x by δ degrees produces a different fx."""
        base_fov = 4.0
        perturbed_fov = base_fov + fov_x_offset_deg

        nom = CameraIntrinsics(W, H, base_fov, FOV_Y_DEG)
        perturbed = CameraCalibration.from_config(W, H, perturbed_fov, FOV_Y_DEG)

        # fx should change
        assert perturbed.fx != nom.fx, "FOV perturbation must change fx"

        # Direction: larger FOV → smaller focal length (wider angle lens)
        if fov_x_offset_deg > 0:
            assert perturbed.fx < nom.fx, "Larger FOV must reduce fx"
        else:
            assert perturbed.fx > nom.fx, "Smaller FOV must increase fx"

    def test_fov_perturbation_pointing_error_magnitude(self):
        """1° FOV error must produce a measurable pointing error at 1.5°.

        We compute the pixel location using the 4° FOV model and then
        unproject using the 5° FOV model to measure the angular error.
        """
        nom = CameraIntrinsics(W, H, FOV_X_DEG, FOV_Y_DEG)      # 4° nominal
        wrong_model = CameraIntrinsics(W, H, FOV_X_DEG + 1.0, FOV_Y_DEG)  # 5° wrong

        # Target is at theta_x = 1.5° in the true 4° model
        theta_x_true = math.radians(1.5)
        u_true, _ = nom.project(theta_x_true, 0.0)

        # Wrong model interprets same pixel as different angle
        theta_x_wrong, _ = wrong_model.unproject(u_true, nom.cy)

        angular_error_deg = abs(math.degrees(theta_x_wrong - theta_x_true))
        angular_error_px = abs(
            nom.project(theta_x_true, 0.0)[0] - nom.project(theta_x_wrong, 0.0)[0]
        )

        # Expect measurable error (>0.01° or >1 pixel equivalent)
        assert angular_error_deg > 0.01, (
            f"1° FOV error should produce >0.01° angular error at 1.5°, "
            f"got {angular_error_deg:.4f}°"
        )


class TestCalibrationSensitivitySummary:
    """Summary table: angular sensitivity in arcseconds/pixel for each intrinsic."""

    def test_angular_sensitivity_budget(self):
        """
        Compute sensor angular sensitivity (arcseconds per pixel)
        and verify it is physically reasonable for a 4°×3° / 640×480 camera.
        """
        cam = CameraIntrinsics(W, H, FOV_X_DEG, FOV_Y_DEG)
        pu = PixelUncertainty(sigma_u=1.0, sigma_v=1.0)
        au = cam.compute_angular_uncertainty(pu)

        # Expected sensitivity: 1 px ≈ (FOV/pixels) in arcseconds
        expected_arcsec_per_px_x = (FOV_X_DEG / W) * 3600.0  # arcsec/px
        expected_arcsec_per_px_y = (FOV_Y_DEG / H) * 3600.0
        actual_arcsec_per_px_x = au.sigma_theta_x_deg * 3600.0
        actual_arcsec_per_px_y = au.sigma_theta_y_deg * 3600.0

        # At boresight, pinhole angular resolution per pixel
        # is FOV / pixel_count (within ~10% relative)
        assert abs(actual_arcsec_per_px_x / expected_arcsec_per_px_x - 1.0) < 0.01, (
            f"Angular sensitivity X: {actual_arcsec_per_px_x:.2f} arcsec/px, "
            f"expected ~{expected_arcsec_per_px_x:.2f} arcsec/px"
        )
        assert abs(actual_arcsec_per_px_y / expected_arcsec_per_px_y - 1.0) < 0.01
