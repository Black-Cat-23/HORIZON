"""
Formal V&V: Camera Intrinsics, Projection, Inverse Projection, Round-Trip, and FOV.
Sections 6, 7, 8, 9, 10 of Phase 2 Formal Verification & Validation specification.
"""

import math
import pytest
from simulator.camera.intrinsics import CameraIntrinsics


class TestCameraIntrinsicsVerification:
    """Section 6: Camera Intrinsic Verification."""

    def test_intrinsic_parameters_analytical_reference(self):
        W, H = 640, 480
        fov_x_deg, fov_y_deg = 4.0, 3.0

        # Independent calculation of expected reference values
        expected_cx = W / 2.0  # 320.0
        expected_cy = H / 2.0  # 240.0
        half_fov_x_rad = math.radians(fov_x_deg / 2.0)
        half_fov_y_rad = math.radians(fov_y_deg / 2.0)
        expected_fx = (W / 2.0) / math.tan(half_fov_x_rad)
        expected_fy = (H / 2.0) / math.tan(half_fov_y_rad)

        cam = CameraIntrinsics(
            width=W,
            height=H,
            fov_horizontal_deg=fov_x_deg,
            fov_vertical_deg=fov_y_deg,
        )

        tol = 1e-9
        assert abs(cam.cx - expected_cx) < tol
        assert abs(cam.cy - expected_cy) < tol
        assert abs(cam.fx - expected_fx) < tol
        assert abs(cam.fy - expected_fy) < tol

        # Numerical report assertions (relative error < 1e-12)
        rel_err_fx = abs(cam.fx - expected_fx) / expected_fx
        rel_err_fy = abs(cam.fy - expected_fy) / expected_fy
        assert rel_err_fx < 1e-12
        assert rel_err_fy < 1e-12


class TestProjectionVerification:
    """Section 7: Projection Verification."""

    @pytest.fixture
    def camera(self):
        return CameraIntrinsics(width=640, height=480, fov_horizontal_deg=4.0, fov_vertical_deg=3.0)

    def test_optical_axis_boresight_projection(self, camera):
        # theta_x = 0, theta_y = 0 -> u = cx, v = cy
        u, v = camera.project(0.0, 0.0)
        assert abs(u - camera.cx) < 1e-9
        assert abs(v - camera.cy) < 1e-9

    def test_projection_symmetry(self, camera):
        theta = math.radians(1.0)
        u_pos, _ = camera.project(+theta, 0.0)
        u_neg, _ = camera.project(-theta, 0.0)
        assert abs((u_pos - camera.cx) - (camera.cx - u_neg)) < 1e-9

        _, v_pos = camera.project(0.0, +theta)
        _, v_neg = camera.project(0.0, -theta)
        assert abs((v_pos - camera.cy) - (camera.cy - v_neg)) < 1e-9

    def test_projection_monotonicity(self, camera):
        # Larger positive theta_x moves u rightward
        thetas_x = [math.radians(deg) for deg in [-1.8, -1.0, -0.2, 0.0, 0.5, 1.2, 1.9]]
        u_vals = [camera.project(tx, 0.0)[0] for tx in thetas_x]
        for i in range(len(u_vals) - 1):
            assert u_vals[i + 1] > u_vals[i], "Monotonicity violated in horizontal projection!"

        # Larger positive theta_y moves v downward
        thetas_y = [math.radians(deg) for deg in [-1.4, -0.8, -0.1, 0.0, 0.4, 0.9, 1.4]]
        v_vals = [camera.project(0.0, ty)[1] for ty in thetas_y]
        for i in range(len(v_vals) - 1):
            assert v_vals[i + 1] > v_vals[i], "Monotonicity violated in vertical projection!"


class TestInverseProjectionAndRoundTrip:
    """Sections 8 & 9: Inverse Projection and Round-Trip Verification."""

    @pytest.fixture
    def camera(self):
        return CameraIntrinsics(width=640, height=480, fov_horizontal_deg=4.0, fov_vertical_deg=3.0)

    def test_inverse_projection_known_points(self, camera):
        # Principal point -> (0, 0)
        tx, ty = camera.unproject(camera.cx, camera.cy)
        assert abs(tx) < 1e-9
        assert abs(ty) < 1e-9

        # Near edge points
        tx_edge, _ = camera.unproject(640.0, camera.cy)
        expected_tx_edge = math.radians(2.0)
        assert abs(tx_edge - expected_tx_edge) < 1e-9

        _, ty_edge = camera.unproject(camera.cx, 480.0)
        expected_ty_edge = math.radians(1.5)
        assert abs(ty_edge - expected_ty_edge) < 1e-9

    def test_round_trip_angle_pixel_angle(self, camera):
        # Round trip: angle -> (u, v) -> angle'
        test_angles = [
            (0.0, 0.0),
            (math.radians(+1.0), math.radians(+0.5)),
            (math.radians(-1.5), math.radians(+1.2)),
            (math.radians(+1.99), math.radians(-1.49)),
            (math.radians(-1.99), math.radians(-1.49)),
        ]

        errors = []
        for tx, ty in test_angles:
            u, v = camera.project(tx, ty)
            tx_rec, ty_rec = camera.unproject(u, v)

            err_x = abs(tx - tx_rec)
            err_y = abs(ty - ty_rec)
            errors.append(err_x)
            errors.append(err_y)

        max_error = max(errors)
        rms_error = math.sqrt(sum(e ** 2 for e in errors) / len(errors))

        # Numerical tolerance: strict 1e-12 radians
        assert max_error < 1e-12, f"Max round-trip error {max_error} exceeds tolerance 1e-12!"
        assert rms_error < 1e-12


class TestFovVerification:
    """Section 10: FOV Boundary Verification."""

    @pytest.fixture
    def camera(self):
        return CameraIntrinsics(width=640, height=480, fov_horizontal_deg=4.0, fov_vertical_deg=3.0)

    def test_fov_boundary_conditions(self, camera):
        half_x = camera.half_fov_x_rad  # 2 deg
        half_y = camera.half_fov_y_rad  # 1.5 deg
        eps = 1e-6  # small angular perturbation

        # 1. Target exactly at optical axis
        assert camera.is_in_fov(0.0, 0.0) is True

        # 2. Target slightly inside FOV
        assert camera.is_in_fov(half_x - eps, half_y - eps) is True

        # 3. Target exactly at horizontal boundary
        assert camera.is_in_fov(+half_x, 0.0) is True
        assert camera.is_in_fov(-half_x, 0.0) is True

        # 4. Target slightly outside horizontal boundary
        assert camera.is_in_fov(half_x + eps, 0.0) is False
        assert camera.is_in_fov(-half_x - eps, 0.0) is False

        # 5. Target exactly at vertical boundary
        assert camera.is_in_fov(0.0, +half_y) is True
        assert camera.is_in_fov(0.0, -half_y) is True

        # 6. Target slightly outside vertical boundary
        assert camera.is_in_fov(0.0, half_y + eps) is False
        assert camera.is_in_fov(0.0, -half_y - eps) is False

        # 7. Target outside both axes
        assert camera.is_in_fov(half_x + eps, half_y + eps) is False
        assert camera.is_in_fov(-half_x - eps, -half_y - eps) is False
