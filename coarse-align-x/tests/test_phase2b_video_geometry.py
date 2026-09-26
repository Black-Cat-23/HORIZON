"""
HORIZON Phase 2B: External Video Geometry & Coordinate Integrity Verification Suite
===================================================================================
Rigorous validation of:
  1. Geometry-preserving transformations (Letterbox, Crop, Fit, Identity)
  2. Dynamic scale & offset calculation from arbitrary dimensions (never hardcoded)
  3. Traceable, reversible bidirectional coordinate mapping across all 4 spaces:
       - Original Video Coordinates
       - Processing Coordinates
       - HYBRID Perception Coordinates
       - Normalized Coordinates (Unit [0, 1] & Centered Boresight [-1, 1])
  4. Accuracy on Center, Edges, Corners, and arbitrary subpixel points
  5. Different aspect ratios: 16:9, 4:3, 1:1, 9:16, 21:9, and arbitrary non-standard
  6. Image frame transformation and reverse recovery
  7. Integration with ExternalVideoSource
  8. Benchmark-1 regression integrity (Virtual Camera & simulation unchanged)
"""

from __future__ import annotations

import math
from pathlib import Path
import cv2
import numpy as np
import pytest

from sources.video_geometry import (
    CoordinatePoint,
    CoordinateSpace,
    TransformationMethod,
    TransformationParameters,
    VideoGeometryTransformer,
)
from sources.external_video_source import ExternalVideoSource
from simulator.camera.camera import VirtualCamera
from simulator.camera.intrinsics import CameraIntrinsics
from simulator.core.config import AppConfig, SimulationConfig
from simulator.core.simulation import SimulationEngine


SAMPLE_VIDEO_PATH = Path("data/samples/isro_sample_beacon_test.mp4")

# Test resolutions representing diverse aspect ratios
TEST_RESOLUTIONS = [
    (1920, 1080, "16:9 Full HD"),
    (1280, 720, "16:9 HD"),
    (800, 600, "4:3 SVGA"),
    (1024, 768, "4:3 XGA"),
    (640, 480, "4:3 Native Benchmark-1"),
    (512, 512, "1:1 Square"),
    (1000, 1000, "1:1 Large Square"),
    (1080, 1920, "9:16 Vertical Portrait"),
    (720, 1280, "9:16 Vertical HD"),
    (2560, 1080, "21:9 Ultrawide"),
    (731, 419, "Arbitrary Non-Standard Aspect"),
]


# ==============================================================================
# 1. Coordinate Systems Reversible Mapping Validation
# ==============================================================================
class TestCoordinateSystemsReversibility:
    """Verify exact reversible mapping between Original and Processing coordinates."""

    @pytest.mark.parametrize("w, h, desc", TEST_RESOLUTIONS)
    def test_round_trip_center(self, w: int, h: int, desc: str) -> None:
        """Center of original video must round-trip exactly and map to processing center."""
        transformer = VideoGeometryTransformer(orig_width=w, orig_height=h, proc_width=640, proc_height=480)
        c_orig_u = w / 2.0
        c_orig_v = h / 2.0

        u_proc, v_proc = transformer.original_to_processing(c_orig_u, c_orig_v)
        u_rec, v_rec = transformer.processing_to_original(u_proc, v_proc)

        # Reversible precision must be sub-pixel exact (< 1e-9 px)
        assert abs(u_rec - c_orig_u) < 1e-9, f"Failed U center recovery for {desc}: err={abs(u_rec - c_orig_u)}"
        assert abs(v_rec - c_orig_v) < 1e-9, f"Failed V center recovery for {desc}: err={abs(v_rec - c_orig_v)}"

        # For letterbox, optical center of video must coincide with center of processing canvas (320, 240)
        assert abs(u_proc - 320.0) < 1e-6, f"Center U not aligned to canvas center for {desc}: {u_proc}"
        assert abs(v_proc - 240.0) < 1e-6, f"Center V not aligned to canvas center for {desc}: {v_proc}"

    @pytest.mark.parametrize("w, h, desc", TEST_RESOLUTIONS)
    def test_round_trip_corners(self, w: int, h: int, desc: str) -> None:
        """All 4 corners must round-trip perfectly and map to exact padded boundaries."""
        transformer = VideoGeometryTransformer(orig_width=w, orig_height=h, proc_width=640, proc_height=480)
        corners = [
            (0.0, 0.0, "Top-Left"),
            (float(w), 0.0, "Top-Right"),
            (0.0, float(h), "Bottom-Left"),
            (float(w), float(h), "Bottom-Right"),
        ]

        for u_c, v_c, corner_name in corners:
            u_proc, v_proc = transformer.original_to_processing(u_c, v_c)
            u_rec, v_rec = transformer.processing_to_original(u_proc, v_proc)

            assert abs(u_rec - u_c) < 1e-9, f"{corner_name} U recovery error for {desc}: {abs(u_rec - u_c)}"
            assert abs(v_rec - v_c) < 1e-9, f"{corner_name} V recovery error for {desc}: {abs(v_rec - v_c)}"

            # Processing coordinates must lie within the processing canvas
            assert 0.0 <= u_proc <= 640.0, f"{corner_name} U out of canvas for {desc}: {u_proc}"
            assert 0.0 <= v_proc <= 480.0, f"{corner_name} V out of canvas for {desc}: {v_proc}"

    @pytest.mark.parametrize("w, h, desc", TEST_RESOLUTIONS)
    def test_round_trip_edges(self, w: int, h: int, desc: str) -> None:
        """Midpoints of all 4 image edges must round-trip with zero geometric distortion."""
        transformer = VideoGeometryTransformer(orig_width=w, orig_height=h, proc_width=640, proc_height=480)
        edges = [
            (w / 2.0, 0.0, "Top-Edge"),
            (w / 2.0, float(h), "Bottom-Edge"),
            (0.0, h / 2.0, "Left-Edge"),
            (float(w), h / 2.0, "Right-Edge"),
        ]

        for u_e, v_e, edge_name in edges:
            u_proc, v_proc = transformer.original_to_processing(u_e, v_e)
            u_rec, v_rec = transformer.processing_to_original(u_proc, v_proc)

            assert abs(u_rec - u_e) < 1e-9, f"{edge_name} U error for {desc}: {abs(u_rec - u_e)}"
            assert abs(v_rec - v_e) < 1e-9, f"{edge_name} V error for {desc}: {abs(v_rec - v_e)}"

    @pytest.mark.parametrize("w, h, desc", TEST_RESOLUTIONS)
    def test_round_trip_dense_subpixel_grid(self, w: int, h: int, desc: str) -> None:
        """A dense grid of subpixel coordinates must achieve machine-precision reversibility."""
        transformer = VideoGeometryTransformer(orig_width=w, orig_height=h, proc_width=640, proc_height=480)
        rng = np.random.RandomState(42)
        test_points_u = rng.uniform(0.0, float(w), size=30)
        test_points_v = rng.uniform(0.0, float(h), size=30)

        for u_orig, v_orig in zip(test_points_u, test_points_v):
            u_proc, v_proc = transformer.original_to_processing(u_orig, v_orig)
            u_rec, v_rec = transformer.processing_to_original(u_proc, v_proc)

            assert abs(u_rec - u_orig) < 1e-9
            assert abs(v_rec - v_orig) < 1e-9


# ==============================================================================
# 2. All Four Coordinate Spaces Traceability
# ==============================================================================
class TestAllFourCoordinateSpaces:
    """Verify seamless traceability across: Original -> Processing -> HYBRID -> Normalized."""

    def test_traceable_pipeline_unit_normalized(self) -> None:
        """Original -> Processing -> HYBRID -> Normalized [0, 1] -> Reverse."""
        transformer = VideoGeometryTransformer(orig_width=1920, orig_height=1080, proc_width=640, proc_height=480)
        orig_u, orig_v = 960.0, 540.0  # Center of 1080p

        # Forward trace
        x_norm, y_norm = transformer.original_to_normalized(orig_u, orig_v, mode="unit")
        # Center in 640x480 canvas is (0.5, 0.5)
        assert abs(x_norm - 0.5) < 1e-7
        assert abs(y_norm - 0.5) < 1e-7

        # Backward trace
        u_rec, v_rec = transformer.normalized_to_original(x_norm, y_norm, mode="unit")
        assert abs(u_rec - orig_u) < 1e-9
        assert abs(v_rec - orig_v) < 1e-9

    def test_traceable_pipeline_centered_boresight(self) -> None:
        """Original -> Processing -> HYBRID -> Normalized Centered [-1, 1] -> Reverse."""
        transformer = VideoGeometryTransformer(orig_width=1280, orig_height=720, proc_width=640, proc_height=480)
        orig_u, orig_v = 640.0, 360.0  # Center of 720p

        # Forward trace
        x_norm, y_norm = transformer.original_to_normalized(orig_u, orig_v, mode="centered")
        # Optical boresight center must be (0.0, 0.0)
        assert abs(x_norm - 0.0) < 1e-7
        assert abs(y_norm - 0.0) < 1e-7

        # Backward trace
        u_rec, v_rec = transformer.normalized_to_original(x_norm, y_norm, mode="centered")
        assert abs(u_rec - orig_u) < 1e-9
        assert abs(v_rec - orig_v) < 1e-9

    def test_trace_point_arbitrary_transitions(self) -> None:
        """Test trace_point across all CoordinateSpace enum members."""
        transformer = VideoGeometryTransformer(orig_width=800, orig_height=600, proc_width=640, proc_height=480)
        pt_orig = CoordinatePoint(x=400.0, y=300.0, space=CoordinateSpace.ORIGINAL_VIDEO)

        # Original -> Processing
        pt_proc = transformer.trace_point(pt_orig, CoordinateSpace.PROCESSING)
        assert pt_proc.space == CoordinateSpace.PROCESSING
        assert abs(pt_proc.x - 320.0) < 1e-6
        assert abs(pt_proc.y - 240.0) < 1e-6

        # Processing -> HYBRID
        pt_hyb = transformer.trace_point(pt_proc, CoordinateSpace.HYBRID)
        assert pt_hyb.space == CoordinateSpace.HYBRID
        assert abs(pt_hyb.x - 320.0) < 1e-6
        assert abs(pt_hyb.y - 240.0) < 1e-6

        # HYBRID -> Normalized Unit
        pt_unit = transformer.trace_point(pt_hyb, CoordinateSpace.NORMALIZED_UNIT)
        assert pt_unit.space == CoordinateSpace.NORMALIZED_UNIT
        assert abs(pt_unit.x - 0.5) < 1e-6
        assert abs(pt_unit.y - 0.5) < 1e-6

        # Normalized Unit -> Normalized Centered
        pt_cent = transformer.trace_point(pt_unit, CoordinateSpace.NORMALIZED_CENTERED)
        assert pt_cent.space == CoordinateSpace.NORMALIZED_CENTERED
        assert abs(pt_cent.x - 0.0) < 1e-6
        assert abs(pt_cent.y - 0.0) < 1e-6

        # Normalized Centered -> Original Video
        pt_recovered = transformer.trace_point(pt_cent, CoordinateSpace.ORIGINAL_VIDEO)
        assert pt_recovered.space == CoordinateSpace.ORIGINAL_VIDEO
        assert abs(pt_recovered.x - pt_orig.x) < 1e-9
        assert abs(pt_recovered.y - pt_orig.y) < 1e-9


# ==============================================================================
# 3. Geometry Preservation & Dynamic Scaling (Never Hard-Coded)
# ==============================================================================
class TestGeometryPreservationAndScaling:
    """Verify that scaling is isotropic, never hard-coded, and preserves video aspect ratio."""

    def test_isotropic_scaling_no_stretching(self) -> None:
        """scale_x must equal scale_y in LETTERBOX and CROP mode (geometry preservation)."""
        for w, h, desc in TEST_RESOLUTIONS:
            transformer = VideoGeometryTransformer(orig_width=w, orig_height=h, proc_width=640, proc_height=480)
            assert transformer.params.is_isotropic, f"Scaling is non-isotropic (stretched!) for {desc}"
            assert abs(transformer.scale_x - transformer.scale_y) < 1e-7

    def test_dynamic_parameters_16_to_9(self) -> None:
        """16:9 into 4:3 canvas produces vertical letterbox bars (top/bottom)."""
        t = VideoGeometryTransformer(orig_width=1920, orig_height=1080, proc_width=640, proc_height=480)
        expected_scale = 640.0 / 1920.0  # 1/3
        assert math.isclose(t.scale_x, expected_scale, rel_tol=1e-6)
        assert math.isclose(t.scale_y, expected_scale, rel_tol=1e-6)
        assert math.isclose(t.offset_x, 0.0, abs_tol=1e-6)
        expected_offset_y = (480.0 - 1080.0 * expected_scale) / 2.0  # 60.0 px
        assert math.isclose(t.offset_y, expected_offset_y, rel_tol=1e-6)
        assert t.params.pad_top == t.params.pad_bottom

    def test_dynamic_parameters_1_to_1(self) -> None:
        """1:1 square into 4:3 canvas produces horizontal pillarbox bars (left/right)."""
        t = VideoGeometryTransformer(orig_width=512, orig_height=512, proc_width=640, proc_height=480)
        expected_scale = 480.0 / 512.0  # 0.9375
        assert math.isclose(t.scale_x, expected_scale, rel_tol=1e-6)
        assert math.isclose(t.scale_y, expected_scale, rel_tol=1e-6)
        assert math.isclose(t.offset_y, 0.0, abs_tol=1e-6)
        expected_offset_x = (640.0 - 512.0 * expected_scale) / 2.0  # 80.0 px
        assert math.isclose(t.offset_x, expected_offset_x, rel_tol=1e-6)
        assert t.params.pad_left == t.params.pad_right

    def test_dynamic_parameters_identity_640x480(self) -> None:
        """Native 640x480 into 640x480 is an exact identity mapping."""
        t = VideoGeometryTransformer(orig_width=640, orig_height=480, proc_width=640, proc_height=480)
        assert t.params.is_identity
        assert t.scale_x == 1.0
        assert t.scale_y == 1.0
        assert t.offset_x == 0.0
        assert t.offset_y == 0.0

    def test_content_region_boundaries(self) -> None:
        """Points inside letterbox black borders must be flagged as out-of-content."""
        t = VideoGeometryTransformer(orig_width=1920, orig_height=1080, proc_width=640, proc_height=480)
        # offset_y is 60.0. A point at y=30 is in the top black letterbox bar
        assert not t.is_in_content_region(320.0, 30.0)
        # Point at y=450 is in bottom black letterbox bar
        assert not t.is_in_content_region(320.0, 450.0)
        # Point at y=240 is inside active video
        assert t.is_in_content_region(320.0, 240.0)


# ==============================================================================
# 4. Image Frame Transformation and Spot Recovery
# ==============================================================================
class TestImageFrameTransformation:
    """Verify that image array pixels transform and recover consistently with math."""

    def test_frame_transform_and_spot_tracking(self) -> None:
        """Synthesize an optical spot at known original coordinates; verify transformed location."""
        w_orig, h_orig = 1280, 720
        transformer = VideoGeometryTransformer(orig_width=w_orig, orig_height=h_orig, proc_width=640, proc_height=480)

        # Create original frame with bright spot at (600, 300)
        u_spot, v_spot = 600, 300
        orig_frame = np.zeros((h_orig, w_orig), dtype=np.uint8)
        cv2.circle(orig_frame, (u_spot, v_spot), radius=6, color=255, thickness=-1)

        # Transform to processing canvas (640x480)
        proc_frame = transformer.transform_frame(orig_frame, border_value=0)
        assert proc_frame.shape == (480, 640)
        assert proc_frame.dtype == np.uint8

        # Compute centroid of transformed spot using image moments
        moments = cv2.moments(proc_frame)
        assert moments["m00"] > 0
        proc_cx = moments["m10"] / moments["m00"]
        proc_cy = moments["m01"] / moments["m00"]

        # Expected location via mathematical transform
        exp_u, exp_v = transformer.original_to_processing(u_spot, v_spot)
        assert abs(proc_cx - exp_u) <= 0.5  # Sub-pixel agreement
        assert abs(proc_cy - exp_v) <= 0.5

        # Reverse transform back to original resolution
        recovered_frame = transformer.reverse_transform_frame(proc_frame)
        assert recovered_frame.shape == (h_orig, w_orig)
        rec_moments = cv2.moments(recovered_frame)
        assert rec_moments["m00"] > 0
        rec_cx = rec_moments["m10"] / rec_moments["m00"]
        rec_cy = rec_moments["m01"] / rec_moments["m00"]
        assert abs(rec_cx - u_spot) <= 1.0
        assert abs(rec_cy - v_spot) <= 1.0

    def test_crop_transformation_method(self) -> None:
        """Verify CROP transformation method (aspect-preserving center crop)."""
        t = VideoGeometryTransformer(
            orig_width=1920, orig_height=1080, proc_width=640, proc_height=480, method=TransformationMethod.CROP
        )
        assert t.params.is_isotropic
        # Scale for crop must cover the canvas
        assert t.scale_x >= 640.0 / 1920.0
        assert t.offset_x <= 0.0 or t.offset_y <= 0.0

        # Center must still round-trip perfectly
        u_proc, v_proc = t.original_to_processing(960.0, 540.0)
        u_orig, v_orig = t.processing_to_original(u_proc, v_proc)
        assert abs(u_orig - 960.0) < 1e-9
        assert abs(v_orig - 540.0) < 1e-9


# ==============================================================================
# 5. ExternalVideoSource Integration
# ==============================================================================
class TestExternalVideoSourceIntegration:
    """Verify ExternalVideoSource correctly exposes and utilizes the geometry transformer."""

    def test_external_video_source_has_transformer(self) -> None:
        """When opened, ExternalVideoSource dynamically initializes geometry_transformer."""
        if not SAMPLE_VIDEO_PATH.exists():
            pytest.skip(f"Sample video not found: {SAMPLE_VIDEO_PATH}")

        source = ExternalVideoSource(SAMPLE_VIDEO_PATH)
        assert source.geometry_transformer is None

        opened = source.open()
        assert opened is True
        assert source.geometry_transformer is not None
        assert isinstance(source.geometry_transformer, VideoGeometryTransformer)
        assert source.geometry_transformer.orig_width == source.width
        assert source.geometry_transformer.orig_height == source.height
        assert source.geometry_transformer.proc_width == 640
        assert source.geometry_transformer.proc_height == 480

        source.close()
        assert source.geometry_transformer is None

    def test_read_processing_frame(self) -> None:
        """Verify read_processing_frame returns valid 640x480 packet with geometry metadata."""
        if not SAMPLE_VIDEO_PATH.exists():
            pytest.skip(f"Sample video not found: {SAMPLE_VIDEO_PATH}")

        source = ExternalVideoSource(SAMPLE_VIDEO_PATH)
        assert source.open() is True

        proc_packet, geom_params = source.read_processing_frame(target_width=640, target_height=480)
        assert proc_packet.valid is True
        assert proc_packet.frame is not None
        assert proc_packet.frame.shape == (480, 640)
        assert proc_packet.width == 640
        assert proc_packet.height == 480
        assert isinstance(geom_params, TransformationParameters)
        assert proc_packet.geometry == geom_params

        source.close()


# ==============================================================================
# 6. Benchmark-1 Regression Integrity
# ==============================================================================
class TestBenchmark1Regression:
    """Verify that Virtual Camera, simulation math, and intrinsics are 100% untouched."""

    def test_virtual_camera_projection_unchanged(self) -> None:
        """Verify VirtualCamera intrinsics, optical projection, and state remain intact."""
        intrinsics = CameraIntrinsics(
            width=640,
            height=480,
            fov_horizontal_deg=4.0,
            fov_vertical_deg=3.0,
        )
        cam = VirtualCamera(intrinsics=intrinsics, update_rate_hz=30.0)
        assert cam.intrinsics.width == 640
        assert cam.intrinsics.height == 480
        assert cam.intrinsics.cx == 320.0
        assert cam.intrinsics.cy == 240.0

        # Baseline projection check: target at center (1000, 1000)
        theta_x, theta_y, u, v, in_fov = cam.project_target(1000.0, 1000.0)
        assert in_fov is True
        assert abs(theta_x) < 1e-6
        assert abs(theta_y) < 1e-6
        assert abs(u - 320.0) < 1e-4
        assert abs(v - 240.0) < 1e-4

    def test_simulation_engine_step_regression(self) -> None:
        """Run a simulation step to ensure zero interference with Benchmark-1 tracking pipeline."""
        sim_cfg = SimulationConfig(duration_seconds=0.2, frequency_hz=30.0, seed=123)
        app_cfg = AppConfig(simulation=sim_cfg)
        engine = SimulationEngine(app_cfg)
        engine.initialize()

        states = []
        for _ in range(6):
            engine.step()
            s = engine.get_current_state()
            states.append((s.timestamp, s.x, s.y, s.vx, s.vy))

        assert len(states) == 6
        assert abs(states[0][0] - (1.0 / 30.0)) < 1e-9
        assert abs(states[-1][0] - 0.2) < 1e-9
        for t, x, y, vx, vy in states:
            assert np.isfinite(x) and np.isfinite(y)
            assert np.isfinite(vx) and np.isfinite(vy)
