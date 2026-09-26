"""HORIZON Phase 11.5 Stress Screen View Component
=================================================
Composite view for Mode 3 ("Stress Testing").
Controlled disturbance experiment room.
"""

from __future__ import annotations
import json
import math
import time
from datetime import datetime
from enum import Enum
from pathlib import Path
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
    StraightTrajectoryConfig,
    TrajectoryConfig,
)
from simulator.core.simulation import SimulationEngine
from simulator.disturbances.config import DisturbanceConfig
from simulator.perception.config import CentroidConfig, DetectorConfig
from simulator.perception.hybrid_detector import HybridBeaconDetector
from tracking.association.track import Track
from tracking.estimation.kalman import EstimatorStatus
from tracking.estimation.state import StateEstimate

from pat.mode_manager import PATModeManager
from pat.state import PATMode, PATState
from control.camera_controller import PATCameraController

from simulator.ui.foundation.tokens import SPACING_12
from simulator.ui.foundation.primitives import SectionHeaderLabel
from simulator.ui.live.hero_sensor_view import HeroSensorView
from simulator.ui.stress.disturbance_controls import DisturbanceControlsWidget
from simulator.ui.stress.system_response_panel import SystemResponsePanelWidget


class ScreenState(Enum):
    IDLE = "idle"
    CONFIGURING = "configuring"
    RUNNING = "running"
    COMPLETED = "completed"
    STOPPED = "stopped"


class StressScreenView(QWidget):
    """Controlled Disturbance Experiment Room (Mode 3)."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self._state = ScreenState.IDLE
        self._staged_config = DisturbanceConfig(enabled=False)
        self._active_config = None

        self._engine = None
        self._detector = None
        self._track = None
        self._pat_mgr = None
        self._pat_ctrl = None

        self._last_estimate: Optional[StateEstimate] = None
        self._search_start_time: float = 0.0
        self._frame_count: int = 0
        self._last_fps_calc_time: float = 0.0
        self._current_fps: float = 0.0

        self._run_current_frame = 0
        self._run_total_frames = 150

        self._sim_timer = QTimer(self)
        self._sim_timer.setInterval(33)
        self._sim_timer.timeout.connect(self._on_sim_step)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(SPACING_12, SPACING_12, SPACING_12, SPACING_12)
        layout.setSpacing(SPACING_12)

        header = SectionHeaderLabel("Controlled disturbance experiment room", self)
        layout.addWidget(header)

        workstation_layout = QHBoxLayout()
        workstation_layout.setContentsMargins(0, 0, 0, 0)
        workstation_layout.setSpacing(SPACING_12)

        self.controls_widget = DisturbanceControlsWidget(self)
        self.controls_widget.setMinimumWidth(280)
        self.controls_widget.setMaximumWidth(320)
        self.controls_widget.disturbance_changed.connect(self._on_disturbance_staged)
        self.controls_widget.run_test_requested.connect(self._on_run_stress_test)
        workstation_layout.addWidget(self.controls_widget, stretch=1)

        self.hero_sensor_view = HeroSensorView(self)
        workstation_layout.addWidget(self.hero_sensor_view, stretch=3)

        self.response_panel = SystemResponsePanelWidget(self)
        self.response_panel.setMinimumWidth(280)
        self.response_panel.setMaximumWidth(320)
        workstation_layout.addWidget(self.response_panel, stretch=1)

        layout.addLayout(workstation_layout, stretch=1)

        self._reset_to_idle_clean()

    def showEvent(self, event) -> None:
        super().showEvent(event)

    def hideEvent(self, event) -> None:
        super().hideEvent(event)
        if self._state == ScreenState.RUNNING:
            self._sim_timer.stop()

    def _reset_to_idle_clean(self) -> None:
        self._state = ScreenState.IDLE
        self._sim_timer.stop()

        static_traj = TrajectoryConfig(
            type="straight",
            straight=StraightTrajectoryConfig(velocity_x=0.0, velocity_y=0.0)
        )
        self._config = AppConfig(trajectory=static_traj)
        self._engine = SimulationEngine(self._config)
        self._engine.initialize()
        self._engine._disturbance_pipeline._config = DisturbanceConfig(enabled=False)

        self._engine.step()
        clean_frame = self._engine.get_clean_frame()

        self._detector = None
        self._track = None
        self._pat_mgr = None
        self._pat_ctrl = None
        self._last_estimate = None

        idle_pat = PATState(mode=PATMode.SEARCH)
        self.hero_sensor_view.update_sensor_display(
            disturbed_frame=clean_frame,
            clean_frame=clean_frame,
            pat_state=idle_pat,
            detection_res=None,
            estimate=None,
            detector_source="HYBRID",
            search_elapsed_s=0.0
        )

        self.response_panel.update_telemetry(
            screen_state=self._state.value,
            staged_config=self._staged_config,
            dist_telem=None,
            pat_state=idle_pat,
            detection_res=None,
            fps=0.0
        )

        self.controls_widget.set_run_state(self._state.value, 0, 0)

    def _on_disturbance_staged(self, config: DisturbanceConfig) -> None:
        self._staged_config = config
        if self._state in (ScreenState.IDLE, ScreenState.CONFIGURING, ScreenState.COMPLETED):
            self._state = ScreenState.CONFIGURING
            self.response_panel.update_telemetry(
                screen_state=self._state.value,
                staged_config=self._staged_config,
                dist_telem=None,
                pat_state=PATState(mode=PATMode.SEARCH),
                detection_res=None,
                fps=0.0
            )

    def _on_run_stress_test(self) -> None:
        if self._state == ScreenState.RUNNING:
            self._reset_to_idle_clean()
            return

        self._state = ScreenState.RUNNING
        self._active_config = self._staged_config

        active_traj = TrajectoryConfig(
            type="figure8",
            figure8=FigureEightTrajectoryConfig(
                amplitude_x=220.0, amplitude_y=140.0, angular_velocity=0.6
            ),
        )
        self._config = AppConfig(trajectory=active_traj)
        self._engine = SimulationEngine(self._config)
        self._engine.initialize()
        self._engine._disturbance_pipeline._config = self._active_config

        self._detector = HybridBeaconDetector(
            DetectorConfig(
                centroid=CentroidConfig(method="weighted_cog"),
                perception_mode="HYBRID",
            )
        )
        self._track = Track(track_id=1)
        self._pat_mgr = PATModeManager()
        self._pat_ctrl = PATCameraController()

        self._last_estimate = None
        self._search_start_time = time.time()
        self._frame_count = 0
        self._last_fps_calc_time = time.time()

        self._run_current_frame = 0
        self._run_total_frames = 150

        self._run_metrics = {
            "total_error": 0.0,
            "max_error": 0.0,
            "error_samples": 0,
            "detections": 0,
            "start_time": time.time(),
        }

        self.controls_widget.set_run_state(
            self._state.value, 0, self._run_total_frames
        )

        self._sim_timer.start()

    def _on_sim_step(self) -> None:
        if self._state != ScreenState.RUNNING or not self._engine.is_initialized:
            return

        self._engine.step()
        disturbed_frame = self._engine.get_camera_frame()
        clean_frame = self._engine.get_clean_frame()
        dist_telemetry = self._engine.last_disturbance_telemetry

        if disturbed_frame is None:
            return

        self._frame_count += 1
        now = time.time()
        dt = now - self._last_fps_calc_time
        if dt >= 1.0:
            self._current_fps = self._frame_count / dt
            self._frame_count = 0
            self._last_fps_calc_time = now

        detection_res = self._detector.detect(disturbed_frame)

        target_detected = detection_res is not None and detection_res.detected
        meas_centroid = detection_res.centroid if target_detected else None

        if target_detected:
            self._run_metrics["detections"] += 1
            if meas_centroid and self._engine.current_target_state:
                gt_state = self._engine.get_current_state()
                if gt_state:
                    _, _, gt_u, gt_v, _ = self._engine.camera.project_target(
                        gt_state.x, gt_state.y
                    )
                    err = math.hypot(
                        meas_centroid[0] - gt_u, meas_centroid[1] - gt_v
                    )
                    self._run_metrics["total_error"] += err
                    self._run_metrics["max_error"] = max(
                        self._run_metrics["max_error"], err
                    )
                    self._run_metrics["error_samples"] += 1

        pat_state = self._pat_mgr.process_step(
            dt=0.033,
            timestamp_s=time.time(),
            detection_valid=target_detected,
            detection_confidence=(
                detection_res.confidence if target_detected else 0.0
            ),
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
            is_sensor_step=True,
        )
        self._last_estimate = estimate

        cur_pan = (
            self._engine.camera.gimbal.pan_deg
            if hasattr(self._engine.camera, "gimbal")
            else 0.0
        )
        cur_tilt = (
            self._engine.camera.gimbal.tilt_deg
            if hasattr(self._engine.camera, "gimbal")
            else 0.0
        )
        search_pan_r, search_tilt_r = self._pat_mgr.search_manager.get_command(
            0.033, cur_pan, cur_tilt
        )
        reacq_pan_r, reacq_tilt_r, _ = (
            self._pat_mgr.reacquisition_manager.process_step(
                0.033, cur_pan, cur_tilt
            )
        )

        self._pat_ctrl.compute_control_command(
            dt=0.033,
            pat_state=pat_state,
            search_pan_rate=search_pan_r,
            search_tilt_rate=search_tilt_r,
            reacquire_pan_rate=reacq_pan_r,
            reacquire_tilt_rate=reacq_tilt_r,
            estimated_vx_px_s=(
                estimate.estimated_vx if estimate.estimated_vx else 0.0
            ),
            estimated_vy_px_s=(
                estimate.estimated_vy if estimate.estimated_vy else 0.0
            ),
            gimbal=self._engine.camera.gimbal,
        )

        search_elapsed = (
            time.time() - self._search_start_time
            if pat_state.mode in [PATMode.SEARCH, PATMode.REACQUIRE]
            else 0.0
        )
        self.hero_sensor_view.update_sensor_display(
            disturbed_frame=disturbed_frame,
            clean_frame=clean_frame,
            pat_state=pat_state,
            detection_res=detection_res,
            estimate=self._last_estimate,
            detector_source=(
                detection_res.method_used if detection_res else "HYBRID"
            ),
            search_elapsed_s=search_elapsed,
        )

        self.response_panel.update_telemetry(
            screen_state=self._state.value,
            staged_config=self._staged_config,
            dist_telem=dist_telemetry,
            pat_state=pat_state,
            detection_res=detection_res,
            fps=self._current_fps if self._current_fps > 0 else 30.0,
        )

        self._run_current_frame += 1
        self.controls_widget.set_run_state(
            self._state.value,
            self._run_current_frame,
            self._run_total_frames,
        )

        if self._run_current_frame >= self._run_total_frames:
            self._on_run_completed()

    def _on_run_completed(self) -> None:
        self._sim_timer.stop()
        self._state = ScreenState.COMPLETED
        self.controls_widget.set_run_state(
            self._state.value, self._run_total_frames, self._run_total_frames
        )

        exec_time = time.time() - self._run_metrics["start_time"]
        avg_fps = (
            self._run_total_frames / exec_time if exec_time > 0 else 0.0
        )
        det_rate = (
            self._run_metrics["detections"] / self._run_total_frames
        ) * 100.0
        mean_err = (
            (
                self._run_metrics["total_error"]
                / self._run_metrics["error_samples"]
            )
            if self._run_metrics["error_samples"] > 0
            else 0.0
        )
        max_error = self._run_metrics["max_error"]

        report = {
            "timestamp": datetime.now().isoformat(),
            "disturbance_profile": self.controls_widget.combo_preset.currentText(),
            "simulation_duration_frames": self._run_total_frames,
            "processing_speed_fps": round(avg_fps, 2),
            "lock_retention_rate": round(det_rate, 2),
            "average_tracking_error_px": round(mean_err, 3),
            "maximum_tracking_error_px": round(max_error, 3),
            "target_loss_percent": round(100.0 - det_rate, 2),
        }

        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        report_path = log_dir / "stress_performance_report.json"
        with open(report_path, "w") as f:
            json.dump(report, f, indent=4)

        if self.isVisible():
            msg_lines = [
                "Executed %d frames." % self._run_total_frames,
                "",
                "Lock Retention Rate: %.1f%%" % det_rate,
                "Average Tracking Error: %.2f px" % mean_err,
                "Max Error: %.2f px" % max_error,
                "",
                "Detailed performance report saved to:",
                str(report_path.absolute()),
            ]
            QMessageBox.information(
                self,
                "Stress Test Completed",
                "\n".join(msg_lines),
            )

        self._reset_to_idle_clean()
