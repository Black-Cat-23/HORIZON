"""
Mathematical Invariants Test Suite
=====================================
Automated assertion of mathematical invariants for CameraIntrinsics
and CameraCalibration across a range of valid configurations.

Tests:
  1. Finite values — no inf or nan in any intrinsic
  2. Valid FOV — 0 < FOV < 180°
  3. Valid focal lengths — fx, fy > 0
  4. Valid resolution — width, height > 0
  5. Valid principal point — cx = W/2, cy = H/2 (FOV-derived)
  6. FOV roundtrip — 2*atan(W/2/fx) == FOV_x to < 1e-9
  7. Boresight → principal point
  8. Monotone coordinate mappings — positive theta → larger pixel
  9. Reject invalid configurations
"""

from __future__ import annotations

import math
import pytest
from simulator.camera.intrinsics import (
    CameraIntrinsics,
    CameraCalibration,
    PixelUncertainty,
    AngularUncertainty,
)


class TestMathematicalInvariants:
    """Tests that call validate_invariants() across a range of configs."""

    @pytest.mark.parametrize("W, H, fov_x, fov_y", [
        (640, 480, 4.0, 3.0),    # Default HORIZON config
        (1920, 1080, 6.0, 4.5),  # HD resolution
        (320, 240, 2.0, 1.5),    # Half resolution, half FOV
        (640, 480, 10.0, 7.5),   # Wider FOV
        (512, 512, 5.0, 5.0),    # Square sensor
        (100, 100, 1.0, 1.0),    # Small narrow-FOV
        (640, 480, 0.1, 0.075),  # Very narrow FOV (high-zoom)
        (640, 480, 89.0, 60.0),  # Wide-angle (< 90°)
    ])
    def test_invariants_pass_for_valid_configs(self, W, H, fov_x, fov_y):
        """validate_invariants() must pass without assertion for valid configs."""
        cam = CameraIntrinsics(W, H, fov_x, fov_y)
        cam.validate_invariants()  # must not raise

    def test_default_config_invariants(self):
        """Default config must pass all invariants."""
        cam = CameraIntrinsics()
        cam.validate_invariants()

    def test_positive_focal_lengths(self):
        """fx and fy must always be strictly positive."""
        cam = CameraIntrinsics(640, 480, 4.0, 3.0)
        assert cam.fx > 0
        assert cam.fy > 0

    def test_finite_focal_lengths(self):
        """fx and fy must be finite (not inf, not nan)."""
        cam = CameraIntrinsics(640, 480, 4.0, 3.0)
        assert math.isfinite(cam.fx)
        assert math.isfinite(cam.fy)
        assert math.isfinite(cam.cx)
        assert math.isfinite(cam.cy)
        assert math.isfinite(cam.fov_x_rad)
        assert math.isfinite(cam.fov_y_rad)

    def test_fov_roundtrip_consistency(self):
        """FOV must be recoverable from fx/fy to machine precision."""
        configs = [
            (640, 480, 4.0, 3.0),
            (1920, 1080, 6.0, 4.5),
            (640, 480, 0.1, 0.075),
        ]
        for W, H, fov_x, fov_y in configs:
            cam = CameraIntrinsics(W, H, fov_x, fov_y)
            recovered_fov_x = 2.0 * math.degrees(math.atan((W / 2.0) / cam.fx))
            recovered_fov_y = 2.0 * math.degrees(math.atan((H / 2.0) / cam.fy))
            assert abs(recovered_fov_x - fov_x) < 1e-9, (
                f"FOV_x roundtrip failed: {recovered_fov_x:.10f} != {fov_x}"
            )
            assert abs(recovered_fov_y - fov_y) < 1e-9, (
                f"FOV_y roundtrip failed: {recovered_fov_y:.10f} != {fov_y}"
            )

    def test_principal_point_at_center(self):
        """cx must equal W/2, cy must equal H/2 for FOV-derived calibration."""
        for W, H in [(640, 480), (1920, 1080), (512, 512)]:
            cam = CameraIntrinsics(W, H, 4.0, 3.0)
            assert cam.cx == W / 2.0
            assert cam.cy == H / 2.0

    def test_projection_monotone_horizontal(self):
        """u must strictly increase as theta_x increases across the FOV."""
        cam = CameraIntrinsics(640, 480, 4.0, 3.0)
        thetas = [math.radians(d) for d in [-1.9, -1.0, -0.5, 0.0, 0.5, 1.0, 1.9]]
        u_vals = [cam.project(tx, 0.0)[0] for tx in thetas]
        for i in range(len(u_vals) - 1):
            assert u_vals[i + 1] > u_vals[i], (
                f"Monotonicity violated at index {i}: u[{i}]={u_vals[i]}, u[{i+1}]={u_vals[i+1]}"
            )

    def test_projection_monotone_vertical(self):
        """v must strictly increase as theta_y increases across the FOV."""
        cam = CameraIntrinsics(640, 480, 4.0, 3.0)
        thetas = [math.radians(d) for d in [-1.4, -0.8, -0.3, 0.0, 0.3, 0.8, 1.4]]
        v_vals = [cam.project(0.0, ty)[1] for ty in thetas]
        for i in range(len(v_vals) - 1):
            assert v_vals[i + 1] > v_vals[i], (
                f"Monotonicity violated at index {i}: v[{i}]={v_vals[i]}, v[{i+1}]={v_vals[i+1]}"
            )

    def test_boresight_maps_to_principal_point(self):
        """Projecting (0, 0) angle must give exactly (cx, cy)."""
        cam = CameraIntrinsics(640, 480, 4.0, 3.0)
        u, v = cam.project(0.0, 0.0)
        assert abs(u - cam.cx) < 1e-12
        assert abs(v - cam.cy) < 1e-12

    def test_symmetric_projection(self):
        """u(+theta) - cx == cx - u(-theta) (left-right symmetry)."""
        cam = CameraIntrinsics(640, 480, 4.0, 3.0)
        for theta_deg in [0.5, 1.0, 1.5, 1.99]:
            theta = math.radians(theta_deg)
            u_pos, _ = cam.project(+theta, 0.0)
            u_neg, _ = cam.project(-theta, 0.0)
            assert abs((u_pos - cam.cx) - (cam.cx - u_neg)) < 1e-10

    def test_k_matrix_shape_and_values(self):
        """to_matrix() must return correct 3×3 K matrix."""
        cam = CameraIntrinsics(640, 480, 4.0, 3.0)
        K = cam.to_matrix()
        assert len(K) == 3
        for row in K:
            assert len(row) == 3
        assert K[0][0] == cam.fx
        assert K[1][1] == cam.fy
        assert K[0][2] == cam.cx
        assert K[1][2] == cam.cy
        assert K[2][2] == 1.0
        assert K[0][1] == 0.0
        assert K[1][0] == 0.0
        assert K[2][0] == 0.0
        assert K[2][1] == 0.0


class TestInvalidConfigurationRejection:
    """Negative tests: invalid configurations must raise ValueError."""

    @pytest.mark.parametrize("W, H", [
        (0, 480),
        (640, 0),
        (-1, 480),
        (640, -1),
    ])
    def test_invalid_resolution_rejected(self, W, H):
        with pytest.raises(ValueError):
            CameraIntrinsics(W, H, 4.0, 3.0)

    @pytest.mark.parametrize("fov_x, fov_y", [
        (0.0, 3.0),
        (4.0, 0.0),
        (-1.0, 3.0),
        (4.0, -1.0),
        (180.0, 3.0),
        (4.0, 180.0),
        (200.0, 3.0),
    ])
    def test_invalid_fov_rejected(self, fov_x, fov_y):
        with pytest.raises(ValueError):
            CameraIntrinsics(640, 480, fov_x, fov_y)

    def test_invalid_calibration_fx_override_rejected(self):
        with pytest.raises(ValueError):
            CameraCalibration.with_explicit_intrinsics(
                640, 480, fx=-100.0, fy=9165.0, cx=320.0, cy=240.0
            )

    def test_invalid_calibration_zero_fx_rejected(self):
        with pytest.raises(ValueError):
            CameraCalibration.with_explicit_intrinsics(
                640, 480, fx=0.0, fy=9165.0, cx=320.0, cy=240.0
            )

    def test_negative_pixel_uncertainty_rejected(self):
        with pytest.raises(ValueError):
            PixelUncertainty(sigma_u=-0.1, sigma_v=0.5)

        with pytest.raises(ValueError):
            PixelUncertainty(sigma_u=0.5, sigma_v=-0.1)


class TestCameraCalibrationInvariants:
    """Invariant tests for CameraCalibration class."""

    def test_from_config_gives_identical_intrinsics(self):
        """from_config() must produce same fx/fy/cx/cy as CameraIntrinsics."""
        W, H = 640, 480
        calib = CameraCalibration.from_config(W, H, 4.0, 3.0)
        base = CameraIntrinsics(W, H, 4.0, 3.0)
        assert abs(calib.fx - base.fx) < 1e-12
        assert abs(calib.fy - base.fy) < 1e-12
        assert abs(calib.cx - base.cx) < 1e-12
        assert abs(calib.cy - base.cy) < 1e-12

    def test_has_overrides_flag(self):
        """has_overrides must be False for FOV-derived, True for explicit."""
        calib_fov = CameraCalibration.from_config(640, 480, 4.0, 3.0)
        calib_exp = CameraCalibration.with_explicit_intrinsics(
            640, 480, fx=9163.0, fy=9165.0, cx=320.0, cy=240.0
        )
        assert calib_fov.has_overrides is False
        assert calib_exp.has_overrides is True

    def test_calibration_k_matrix_correct(self):
        """to_matrix() must be consistent with fx/fy/cx/cy."""
        calib = CameraCalibration.with_explicit_intrinsics(
            640, 480, fx=9200.0, fy=9180.0, cx=321.5, cy=241.0
        )
        K = calib.to_matrix()
        assert K[0][0] == calib.fx
        assert K[1][1] == calib.fy
        assert K[0][2] == calib.cx
        assert K[1][2] == calib.cy
