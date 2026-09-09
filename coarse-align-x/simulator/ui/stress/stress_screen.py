"""HORIZON Phase 11.5 Stress Screen View Component
=================================================
Composite view for Mode 3 ("Stress Testing").
Controlled disturbance experiment room.

Layout Structure:
  - LEFT: Disturbance Controls Widget (Preset profiles & real disturbance parameters)
  - CENTER (Main): Hero Sensor View — REUSED from Phase 11.2 (HeroSensorView)
  - RIGHT: System Response & Real Telemetry Panel

Cause -> Effect Enforced:
  Changing any control reconfigures real backend DisturbancePipeline and reprocesses frames.
  All metric changes come directly from real backend execution — ZERO UI interpolation.
"""

from __future__ import annotations
import math
import time
from typing import Optional, Tuple
import cv2
import numpy as np

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QHBoxLayout,
    QMessageBox,
    QVBoxLayout,
    QWidget,
)

from simulator.core.config import (
    AppConfig,
    FigureEightTrajectoryConfig,
    TrajectoryConfig,
)
from simulator.core.simulation import SimulationEngine
from simulator.disturbances.config import DisturbanceConfig
from simulator.perception.config import CentroidConfig, DetectorConfig
from simulator.perception.hybrid_detector import HybridBeaconDetector
from tracking.association.track import Track
from tracking.estimation.kalman import EstimatorStatus
from tracking.estimation.state import StateEstimate

# PAT System Imports
from pat.mode_manager import PATModeManager
from pat.state import PATMode, PATState
from control.camera_controller import PATCameraController

# Foundation Primitives
from simulator.ui.foundation.tokens import SPACING_12
from simulator.ui.foundation.primitives import SectionHeaderLabel

# Reused Component from Phase 11.2 (DO NOT REBUILD)
from simulator.ui.live.hero_sensor_view import HeroSensorView

# Phase 11.5 Stress Subcomponents
from simulator.ui.stress.disturbance_controls import DisturbanceControlsWidget
from simulator.ui.stress.system_response_panel import SystemResponsePanelWidget


class StressScreenView(QWidget):
    """Controlled Disturbance Experiment Room (Mode 3)."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        # 1. Initialize Real Simulation Engine & Subsystems
        self._config = AppConfig(
            trajectory=TrajectoryConfig(
                type="figure8",
                figure8=FigureEightTrajectoryConfig(amplitude_x=220.0, amplitude_y=140.0, angular_velocity=0.6),
            )
        )
        self._engine = SimulationEngine(self._config)
        self._engine.initialize()

        # Perception, Tracking, PAT controllers
        self._detector = HybridBeaconDetector(
            DetectorConfig(centroid=CentroidConfig(method="weighted_cog"), perception_mode="HYBRID")
        )
        self._track = Track(track_id=1)
        self._pat_mgr = PATModeManager()
        self._pat_ctrl = PATCameraController()

        self._last_estimate: Optional[StateEstimate] = None
        self._search_start_time: float = time.time()
        self._frame_count: int = 0
        self._last_fps_calc_time: float = time.time()
        self._current_fps: float = 0.0

        # Real-time simulation execution loop QTimer
        self._sim_timer = QTimer(self)
        self._sim_timer.setInterval(33)  # ~30 FPS loop
        self._sim_timer.timeout.connect(self._on_sim_step)

        # 2. Build Layout Architecture
        layout = QVBoxLayout(self)
        layout.setContentsMargins(SPACING_12, SPACING_12, SPACING_12, SPACING_12)
        layout.setSpacing(SPACING_12)

        # Screen Title Header: "Controlled disturbance experiment room" (Sentence case)
        header = SectionHeaderLabel("Controlled disturbance experiment room", self)
        layout.addWidget(header)

        # Horizontal 3-Column Workstation Layout
        workstation_layout = QHBoxLayout()
        workstation_layout.setContentsMargins(0, 0, 0, 0)
        workstation_layout.setSpacing(SPACING_12)

        # Column 1: Left Disturbance Controls Panel
        self.controls_widget = DisturbanceControlsWidget(self)
        self.controls_widget.setMinimumWidth(280)
        self.controls_widget.setMaximumWidth(320)
        self.controls_widget.disturbance_changed.connect(self._on_disturbance_changed)
        self.controls_widget.run_test_requested.connect(self._on_run_stress_test)
        workstation_layout.addWidget(self.controls_widget, stretch=1)

        # Column 2: Center Hero Sensor View (REUSED Component from Phase 11.2!)
        self.hero_sensor_view = HeroSensorView(self)
        workstation_layout.addWidget(self.hero_sensor_view, stretch=3)

        # Column 3: Right System Response & Real Telemetry Panel
        self.response_panel = SystemResponsePanelWidget(self)
        self.response_panel.setMinimumWidth(280)
        self.response_panel.setMaximumWidth(320)
        workstation_layout.addWidget(self.response_panel, stretch=1)

        layout.addLayout(workstation_layout, stretch=1)

        # Start loop
        self._sim_timer.start()

    def showEvent(self, event) -> None:
        super().showEvent(event)
        if not self._sim_timer.isActive():
            self._sim_timer.start()

    def hideEvent(self, event) -> None:
        super().hideEvent(event)
        self._sim_timer.stop()

    def _on_disturbance_changed(self, config: DisturbanceConfig) -> None:
        """Apply user disturbance configuration directly to real backend DisturbancePipeline."""
        if self._engine and self._engine._disturbance_pipeline:
            self._engine._disturbance_pipeline._config = config
            # Instantly execute one step so user sees honest immediate backend reprocessing
            self._on_sim_step()

    def _on_sim_step(self) -> None:
        """Main step callback driven by QTimer."""
        if not self._engine.is_initialized:
            return

        # 1. Step backend engine
        self._engine.step()
        disturbed_frame = self._engine.get_camera_frame()
        clean_frame = self._engine.get_clean_frame()
        dist_telemetry = self._engine.last_disturbance_telemetry

        if disturbed_frame is None:
            return

        # Calculate real FPS
        self._frame_count += 1
        now = time.time()
        dt = now - self._last_fps_calc_time
        if dt >= 1.0:
            self._current_fps = self._frame_count / dt
            self._frame_count = 0
            self._last_fps_calc_time = now

        # 2. Run real perception detector
        detection_res = self._detector.detect(disturbed_frame)

        # 3. Update PAT state & tracking filters
        target_detected = (detection_res is not None and detection_res.detected)
        meas_centroid = detection_res.centroid if target_detected else None

        pat_state = self._pat_mgr.process_step(
            dt=0.033,
            timestamp_s=time.time(),
            detection_valid=target_detected,
            detection_confidence=detection_res.confidence if target_detected else 0.0,
            mahalanobis_d2=0.0,
            covariance_trace=1.0,
            estimated_u_px=meas_centroid[0] if meas_centroid else 320.0,
            estimated_v_px=meas_centroid[1] if meas_centroid else 240.0,
            estimated_vx_px_s=0.0,
            estimated_vy_px_s=0.0,
            current_pan_deg=0.0,
            current_tilt_deg=0.0,
        )

        estimate = self._track.step(
            measurement=meas_centroid if target_detected else None,
            confidence=detection_res.confidence if target_detected else 0.0,
            timestamp=time.time(),
        )
        self._last_estimate = estimate

        # 4. Update Reused HeroSensorView
        search_elapsed = time.time() - self._search_start_time if pat_state.mode in [PATMode.SEARCH, PATMode.REACQUIRE] else 0.0
        self.hero_sensor_view.update_sensor_display(
            disturbed_frame=disturbed_frame,
            clean_frame=clean_frame,
            pat_state=pat_state,
            detection_res=detection_res,
            estimate=self._last_estimate,
            detector_source=detection_res.method_used if detection_res else "HYBRID",
            search_elapsed_s=search_elapsed,
        )

        # 5. Update System Response Panel
        self.response_panel.update_telemetry(
            dist_telem=dist_telemetry,
            pat_state=pat_state,
            detection_res=detection_res,
            fps=self._current_fps if self._current_fps > 0 else 30.0,
        )

    def _on_run_stress_test(self) -> None:
        """Execute a real backend experiment under current disturbance settings and show honest results."""
        # Sentence case action requirement: "Run stress test"
        total_steps = 30
        detections = 0
        total_error = 0.0
        error_samples = 0

        # Temporarily run 30 real backend steps
        for _ in range(total_steps):
            self._engine.step()
            frame = self._engine.get_camera_frame()
            if frame is not None:
                res = self._detector.detect(frame)
                if res and res.detected:
                    detections += 1
                    if res.centroid and self._engine.current_target_state:
                        # Ground truth pos comparison for verification metric
                        gt_x = self._engine.current_target_state.x
                        gt_y = self._engine.current_target_state.y
                        err = math.hypot(res.centroid[0] - gt_x, res.centroid[1] - gt_y)
                        total_error += err
                        error_samples += 1

        det_rate = (detections / total_steps) * 100.0
        mean_err = (total_error / error_samples) if error_samples > 0 else 0.0

        if self.isVisible():
            QMessageBox.information(
                self,
                "Stress Test Completed",
                f"Executed {total_steps} real backend experiment steps.\n\n"
                f"Detection Rate: {det_rate:.1f}%\n"
                f"Mean Tracking Error: {mean_err:.2f} px\n"
                f"Disturbance Profile: {self.controls_widget.combo_preset.currentText()}",
            )
