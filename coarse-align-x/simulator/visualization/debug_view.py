"""
HORIZON Lightweight Development Debug View
=================================================
PySide6 engineering debug viewer to inspect and formally verify the real
deterministic simulation, virtual camera viewport, Phase 3 disturbance engine,
and Phase 4 real-time optical beacon perception tracking.

Features:
  - Triple viewports:
      1. Macro World (2000×2000) with dynamic camera FOV footprint.
      2. Clean Optical Sensor Feed (640×480) [Ground Truth Observation].
      3. Phase 4 Perception Tracking Feed (640×480) [Live Detection Bounding Box & Subpixel Centroid].
  - Real-Time Perception Telemetry: Lock status, estimated centroid, tracking error vs GT, confidence, and latency.
  - Live Centroiding Algorithm Switcher (Weighted CoG, 2D Gaussian Fit, Geometric).
  - Disturbance preset switcher (NOMINAL, DIFFICULT, SEVERE, RECOVERY, ADVERSARIAL).
  - Snapshot export: clean_frame.png, disturbed_frame.png, detection_annotated.png.
"""

from __future__ import annotations

import math
from pathlib import Path
import sys
from typing import Optional
import cv2
import numpy as np

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from simulator.core.config import (
    AppConfig,
    CircularTrajectoryConfig,
    FigureEightTrajectoryConfig,
    SimulationConfig,
    TrajectoryConfig,
)
from simulator.core.simulation import SimulationEngine
from simulator.disturbances.presets import get_preset_config
# Phase 4, Phase 7 & Phase 8 Perception Imports
from simulator.perception.config import CentroidConfig, DetectorConfig
from simulator.perception.detector import ClassicalBeaconDetector, DetectionResult
from simulator.perception.neural_detector import NeuralBeaconDetector
from simulator.perception.hybrid_detector import HybridBeaconDetector
from tracking.association.track import Track
from tracking.estimation.kalman import TargetKalmanFilter, EstimatorStatus
from tracking.diagnostics.visualization import draw_tracking_annotations

# Phase 6 PAT Imports
from pat.mode_manager import PATModeManager
from pat.state import PATMode
from control.camera_controller import PATCameraController
from tracking.estimation.state import EstimatorStatus, StateEstimate


class SimulationDebugViewer(QMainWindow):
    """Development debug viewer for HORIZON simulation, disturbances & perception."""

    def __init__(self, config: Optional[AppConfig] = None) -> None:
        super().__init__()
        self.setWindowTitle("HORIZON — Phase 7 Neural Perception & PAT Viewer (SIH26169)")
        self.resize(1560, 900)

        if config is None:
            self._config = AppConfig(
                trajectory=TrajectoryConfig(
                    type="figure8",
                    figure8=FigureEightTrajectoryConfig(amplitude_x=220.0, amplitude_y=140.0, angular_velocity=0.6),
                )
            )
        else:
            self._config = config
        self._engine = SimulationEngine(self._config)
        self._engine.initialize()

        # Phase 4, Phase 7 & Phase 8 Perception Detectors
        self._centroid_method = "weighted_cog"
        self._perception_mode = "HYBRID"
        self._classical_detector = ClassicalBeaconDetector(
            DetectorConfig(centroid=CentroidConfig(method=self._centroid_method), perception_mode="CLASSICAL")
        )
        self._neural_detector = NeuralBeaconDetector(
            DetectorConfig(centroid=CentroidConfig(method=self._centroid_method), perception_mode="NEURAL")
        )
        self._hybrid_detector = HybridBeaconDetector(
            DetectorConfig(centroid=CentroidConfig(method=self._centroid_method), perception_mode="HYBRID")
        )
        self._detector = self._hybrid_detector
        self._last_detection: Optional[DetectionResult] = None

        # Phase 5 Optical Target Tracker & State Estimator
        self._track = Track(track_id=1)
        self._last_estimate: Optional[StateEstimate] = None

        # Phase 6 PAT Mode Manager & Closed-Loop Camera Controller
        self._pat_mgr = PATModeManager()
        self._pat_ctrl = PATCameraController()
        self._suppress_detection_test = False

        # Playback timer
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._on_sim_tick)
        self._is_paused = True

        self._setup_ui()
        self._update_display()

    def _setup_ui(self) -> None:
        main_widget = QWidget(self)
        self.setCentralWidget(main_widget)
        root_layout = QHBoxLayout(main_widget)

        # Left side: Viewports container
        viewports_container = QWidget(self)
        vp_layout = QVBoxLayout(viewports_container)

        # Top row: Clean Sensor Feed vs Phase 4 Perception Tracking Feed
        cam_comparison_box = QGroupBox("Camera Sensor Comparison: Clean vs. Phase 4 Perception Tracking (640×480)", self)
        cam_comp_layout = QHBoxLayout(cam_comparison_box)

        # Clean Camera Feed
        clean_box = QGroupBox("Clean Camera Frame (Ground Truth)", self)
        clean_layout = QVBoxLayout(clean_box)
        self._clean_cam_label = QLabel(self)
        self._clean_cam_label.setMinimumSize(420, 315)
        self._clean_cam_label.setAlignment(Qt.AlignCenter)
        self._clean_cam_label.setStyleSheet("background-color: #111; border: 1px solid #333;")
        clean_layout.addWidget(self._clean_cam_label)
        cam_comp_layout.addWidget(clean_box)

        # Phase 4 Perception Tracking Feed
        dist_box = QGroupBox("Phase 4 Perception Output (Live Lock & Subpixel Centroid)", self)
        dist_layout = QVBoxLayout(dist_box)
        self._dist_cam_label = QLabel(self)
        self._dist_cam_label.setMinimumSize(420, 315)
        self._dist_cam_label.setAlignment(Qt.AlignCenter)
        self._dist_cam_label.setStyleSheet("background-color: #111; border: 1px solid #333;")
        dist_layout.addWidget(self._dist_cam_label)
        cam_comp_layout.addWidget(dist_box)

        vp_layout.addWidget(cam_comparison_box, stretch=2)

        # Bottom row: Macro World (2000x2000)
        world_box = QGroupBox("Macro World Overview (2000×2000)", self)
        w_layout = QHBoxLayout(world_box)
        self._world_label = QLabel(self)
        self._world_label.setMinimumSize(420, 320)
        self._world_label.setAlignment(Qt.AlignCenter)
        self._world_label.setStyleSheet("background-color: #111; border: 1px solid #333;")
        w_layout.addWidget(self._world_label)
        vp_layout.addWidget(world_box, stretch=2)

        root_layout.addWidget(viewports_container, stretch=3)

        # Right side: Controls & Telemetry
        scroll_area = QScrollArea(self)
        scroll_area.setWidgetResizable(True)
        scroll_content = QWidget()
        ctrl_panel_layout = QVBoxLayout(scroll_content)

        # 0. Phase 6 Closed-Loop PAT Telemetry Box
        pat_telemetry_box = QGroupBox("Phase 6 Closed-Loop PAT Telemetry", self)
        pat_layout = QFormLayout(pat_telemetry_box)

        self._lbl_pat_mode = QLabel("SEARCH")
        self._lbl_pat_mode.setStyleSheet("color: #ffcc00; font-weight: bold; font-size: 14px;")
        self._lbl_pat_quality = QLabel("0.0%")
        self._lbl_pat_error = QLabel("Pan: 0.00° | Tilt: 0.00°")
        self._lbl_pat_cmd_rate = QLabel("Pan: 0.00°/s | Tilt: 0.00°/s")
        self._lbl_pat_act_rate = QLabel("Pan: 0.00°/s | Tilt: 0.00°/s")
        self._lbl_pat_sat = QLabel("NO")
        self._lbl_pat_sat.setStyleSheet("color: #4cd964; font-weight: bold;")

        pat_layout.addRow("PAT Mode:", self._lbl_pat_mode)
        pat_layout.addRow("Track Quality:", self._lbl_pat_quality)
        pat_layout.addRow("Pointing Error (e):", self._lbl_pat_error)
        pat_layout.addRow("Commanded Rates (u):", self._lbl_pat_cmd_rate)
        pat_layout.addRow("Actual Gimbal Rates:", self._lbl_pat_act_rate)
        pat_layout.addRow("Actuator Saturation:", self._lbl_pat_sat)
        ctrl_panel_layout.addWidget(pat_telemetry_box)

        # 1. Phase 5 State Estimation Telemetry Box (NEW)
        est_telemetry_box = QGroupBox("Phase 5 State Estimation Telemetry (Kalman Filter)", self)
        et_layout = QFormLayout(est_telemetry_box)

        self._lbl_est_status = QLabel("UNINITIALIZED")
        self._lbl_est_status.setStyleSheet("color: #00d4ff; font-weight: bold; font-size: 13px;")
        self._lbl_est_pos = QLabel("u: 0.00 | v: 0.00 px")
        self._lbl_est_vel = QLabel("Vu: 0.00 | Vv: 0.00 px/s")
        self._lbl_est_unc = QLabel("pos: ±0.00 px | vel: ±0.00 px/s")
        self._lbl_est_inno = QLabel("||y||: 0.00 px | d²: 0.00")
        self._lbl_est_latency = QLabel("0.0 ms")

        et_layout.addRow("Filter Status:", self._lbl_est_status)
        et_layout.addRow("Estimated Position:", self._lbl_est_pos)
        et_layout.addRow("Estimated Velocity:", self._lbl_est_vel)
        et_layout.addRow("1-Sigma Uncertainty:", self._lbl_est_unc)
        et_layout.addRow("Innovation / Gate:", self._lbl_est_inno)
        et_layout.addRow("Estimator Latency:", self._lbl_est_latency)
        ctrl_panel_layout.addWidget(est_telemetry_box)

        # 2. Phase 4 Perception Telemetry Box
        perc_telemetry_box = QGroupBox("Phase 4 Perception Telemetry (Live Tracking)", self)
        pt_layout = QFormLayout(perc_telemetry_box)

        self._lbl_perc_lock = QLabel("LOCKED")
        self._lbl_perc_lock.setStyleSheet("color: #4cd964; font-weight: bold; font-size: 13px;")
        self._lbl_perc_centroid = QLabel("u: 0.00 | v: 0.00 px")
        self._lbl_perc_error = QLabel("0.000 px")
        self._lbl_perc_error.setStyleSheet("color: #00d4ff; font-weight: bold;")
        self._lbl_perc_conf = QLabel("0.0%")
        self._lbl_perc_latency = QLabel("0.0 ms")

        pt_layout.addRow("Tracking State:", self._lbl_perc_lock)
        pt_layout.addRow("Estimated Centroid:", self._lbl_perc_centroid)
        pt_layout.addRow("Subpixel Error vs GT:", self._lbl_perc_error)
        pt_layout.addRow("Detection Confidence:", self._lbl_perc_conf)
        pt_layout.addRow("Perception Latency:", self._lbl_perc_latency)
        ctrl_panel_layout.addWidget(perc_telemetry_box)

        # 2. Disturbance Telemetry Box
        dist_telemetry_box = QGroupBox("Disturbance Telemetry (Phase 3)", self)
        dt_layout = QFormLayout(dist_telemetry_box)

        self._lbl_dt_status = QLabel("ENABLED")
        self._lbl_dt_status.setStyleSheet("color: #ff9500; font-weight: bold;")
        self._lbl_sp = QLabel("OFF")
        self._lbl_gauss = QLabel("OFF")
        self._lbl_poisson = QLabel("OFF")
        self._lbl_jitter = QLabel("dx: +0.00 | dy: +0.00 px")
        self._lbl_platform = QLabel("ox: +0.00 | oy: +0.00 px")
        self._lbl_atmos = QLabel("CLEAR")

        dt_layout.addRow("Disturbance State:", self._lbl_dt_status)
        dt_layout.addRow("Salt & Pepper:", self._lbl_sp)
        dt_layout.addRow("Gaussian Noise:", self._lbl_gauss)
        dt_layout.addRow("Poisson Shot Noise:", self._lbl_poisson)
        dt_layout.addRow("Camera Jitter:", self._lbl_jitter)
        dt_layout.addRow("Platform Motion:", self._lbl_platform)
        dt_layout.addRow("Atmosphere:", self._lbl_atmos)
        ctrl_panel_layout.addWidget(dist_telemetry_box)

        # 3. Ground-Truth Kinematics Telemetry
        telemetry_box = QGroupBox("Ground-Truth Telemetry", self)
        t_layout = QFormLayout(telemetry_box)

        self._lbl_time = QLabel("0.000 s")
        self._lbl_frame = QLabel("0")
        self._lbl_pos = QLabel("X: 0.00 | Y: 0.00 px")
        self._lbl_vel = QLabel("Vx: 0.00 | Vy: 0.00 px/s")
        self._lbl_cam_pixel = QLabel("u: 0.00 | v: 0.00 px")
        self._lbl_fov_status = QLabel("VISIBLE")
        self._lbl_fov_status.setStyleSheet("color: #4cd964; font-weight: bold;")

        t_layout.addRow("Simulation Time:", self._lbl_time)
        t_layout.addRow("Frame Number:", self._lbl_frame)
        t_layout.addRow("Target World Pos:", self._lbl_pos)
        t_layout.addRow("Target Velocity:", self._lbl_vel)
        t_layout.addRow("True Projected (u, v):", self._lbl_cam_pixel)
        t_layout.addRow("Camera FOV Status:", self._lbl_fov_status)
        ctrl_panel_layout.addWidget(telemetry_box)

        # 4. Controls & Configuration
        controls_box = QGroupBox("Configuration & Presets", self)
        form_layout = QFormLayout(controls_box)
        # Perception Mode selector (CLASSICAL vs NEURAL vs HYBRID)
        self._combo_perc_mode = QComboBox(self)
        self._combo_perc_mode.addItems(["CLASSICAL", "NEURAL", "HYBRID"])
        self._combo_perc_mode.setCurrentText(self._perception_mode)
        self._combo_perc_mode.currentTextChanged.connect(self._on_perc_mode_changed)
        form_layout.addRow("Perception Engine:", self._combo_perc_mode)

        # Centroid Method selector
        self._combo_method = QComboBox(self)
        self._combo_method.addItems(["weighted_cog", "gaussian_fit", "geometric"])
        self._combo_method.setCurrentText(self._centroid_method)
        self._combo_method.currentTextChanged.connect(self._on_method_changed)
        form_layout.addRow("Centroid Method:", self._combo_method)

        # Disturbance preset selector
        self._combo_preset = QComboBox(self)
        self._combo_preset.addItems(["NOMINAL", "DIFFICULT", "SEVERE", "RECOVERY", "ADVERSARIAL"])
        self._combo_preset.setCurrentText("DIFFICULT")
        self._combo_preset.currentTextChanged.connect(self._on_preset_changed)
        form_layout.addRow("Disturbance Preset:", self._combo_preset)

        # Trajectory selector
        self._combo_traj = QComboBox(self)
        self._combo_traj.addItems(["figure8", "circular", "straight", "random", "spiral", "sinusoidal"])
        self._combo_traj.setCurrentText("figure8")
        form_layout.addRow("Trajectory:", self._combo_traj)

        self._spin_seed = QSpinBox(self)
        self._spin_seed.setRange(0, 999999)
        self._spin_seed.setValue(self._config.simulation.seed)
        form_layout.addRow("Random Seed:", self._spin_seed)

        self._spin_duration = QDoubleSpinBox(self)
        self._spin_duration.setRange(1.0, 3600.0)
        self._spin_duration.setValue(self._config.simulation.duration_seconds)
        self._spin_duration.setSuffix(" s")
        form_layout.addRow("Duration:", self._spin_duration)

        ctrl_panel_layout.addWidget(controls_box)

        # 5. Action Buttons
        btn_layout = QHBoxLayout()
        self._btn_play = QPushButton("▶ Start", self)
        self._btn_play.clicked.connect(self._toggle_play)
        btn_layout.addWidget(self._btn_play)

        self._btn_reset = QPushButton("↺ Reset", self)
        self._btn_reset.clicked.connect(self._reset_sim)
        btn_layout.addWidget(self._btn_reset)
        ctrl_panel_layout.addLayout(btn_layout)

        # Snapshot & Export buttons
        snap_layout = QHBoxLayout()
        self._btn_snap_clean = QPushButton("📷 Save Clean", self)
        self._btn_snap_clean.clicked.connect(self._save_clean_snapshot)
        snap_layout.addWidget(self._btn_snap_clean)

        self._btn_snap_dist = QPushButton("📷 Save Tracking", self)
        self._btn_snap_dist.clicked.connect(self._save_disturbed_snapshot)
        snap_layout.addWidget(self._btn_snap_dist)
        ctrl_panel_layout.addLayout(snap_layout)

        self._btn_export = QPushButton("💾 Export Ground Truth (CSV)", self)
        self._btn_export.clicked.connect(self._export_data)
        ctrl_panel_layout.addWidget(self._btn_export)

        self._btn_test_blackout = QPushButton("⚡ Suppress Detection (Test Loss)", self)
        self._btn_test_blackout.setCheckable(True)
        self._btn_test_blackout.setStyleSheet("background-color: #3a2020; color: #ff3b30; font-weight: bold;")
        self._btn_test_blackout.clicked.connect(self._toggle_blackout_test)
        ctrl_panel_layout.addWidget(self._btn_test_blackout)

        self._lbl_status = QLabel("Status: Ready (Paused)", self)
        self._lbl_status.setStyleSheet("color: #888; font-style: italic;")
        ctrl_panel_layout.addWidget(self._lbl_status)

        ctrl_panel_layout.addStretch()
        scroll_area.setWidget(scroll_content)
        root_layout.addWidget(scroll_area, stretch=1)

    def _on_perc_mode_changed(self, mode_str: str) -> None:
        self._perception_mode = mode_str
        if mode_str == "NEURAL":
            self._detector = self._neural_detector
        elif mode_str == "HYBRID":
            self._detector = self._hybrid_detector
        else:
            self._detector = self._classical_detector
        self._lbl_status.setText(f"Perception Mode: {mode_str}")
        self._update_display()

    def _on_method_changed(self, method_name: str) -> None:
        self._centroid_method = method_name
        self._classical_detector = ClassicalBeaconDetector(
            DetectorConfig(centroid=CentroidConfig(method=self._centroid_method), perception_mode="CLASSICAL")
        )
        self._neural_detector = NeuralBeaconDetector(
            DetectorConfig(centroid=CentroidConfig(method=self._centroid_method), perception_mode="NEURAL")
        )
        self._hybrid_detector = HybridBeaconDetector(
            DetectorConfig(centroid=CentroidConfig(method=self._centroid_method), perception_mode="HYBRID")
        )
        if self._perception_mode == "NEURAL":
            self._detector = self._neural_detector
        elif self._perception_mode == "HYBRID":
            self._detector = self._hybrid_detector
        else:
            self._detector = self._classical_detector
        self._update_display()

    def _on_preset_changed(self, preset_name: str) -> None:
        new_dist = get_preset_config(preset_name)
        new_config = AppConfig(
            world=self._config.world,
            camera=self._config.camera,
            target=self._config.target,
            simulation=self._config.simulation,
            trajectory=self._config.trajectory,
            logging=self._config.logging,
            ground_truth=self._config.ground_truth,
            disturbance=new_dist,
        )
        self._config = new_config
        self._reset_sim()

    def _toggle_play(self) -> None:
        if self._is_paused:
            self._is_paused = False
            self._btn_play.setText("⏸ Pause")
            self._lbl_status.setText("Status: Simulating & Tracking...")
            self._timer.start(16)
        else:
            self._is_paused = True
            self._btn_play.setText("▶ Resume")
            self._lbl_status.setText("Status: Paused")
            self._timer.stop()

    def _toggle_blackout_test(self, checked: bool) -> None:
        self._suppress_detection_test = checked
        if checked:
            self._btn_test_blackout.setText("⚡ Detection SUPPRESSED (Active Test)")
            self._btn_test_blackout.setStyleSheet("background-color: #ff3b30; color: #ffffff; font-weight: bold;")
        else:
            self._btn_test_blackout.setText("⚡ Suppress Detection (Test Loss)")
            self._btn_test_blackout.setStyleSheet("background-color: #3a2020; color: #ff3b30; font-weight: bold;")

    def _reset_sim(self) -> None:
        self._timer.stop()
        self._is_paused = True
        self._btn_play.setText("▶ Start")
        self._lbl_status.setText("Status: Reset")

        new_config = AppConfig(
            world=self._config.world,
            camera=self._config.camera,
            target=self._config.target,
            simulation=SimulationConfig(
                frequency_hz=self._config.simulation.frequency_hz,
                seed=self._spin_seed.value(),
                duration_seconds=self._spin_duration.value(),
            ),
            trajectory=TrajectoryConfig(
                type=self._combo_traj.currentText(),
                straight=self._config.trajectory.straight,
                circular=CircularTrajectoryConfig(radius=120.0, angular_velocity=0.6)
                if self._combo_traj.currentText() == "circular"
                else self._config.trajectory.circular,
                figure8=FigureEightTrajectoryConfig(amplitude_x=220.0, amplitude_y=140.0, angular_velocity=0.6)
                if self._combo_traj.currentText() == "figure8"
                else self._config.trajectory.figure8,
                random=self._config.trajectory.random,
                spiral=self._config.trajectory.spiral,
                sinusoidal=self._config.trajectory.sinusoidal,
            ),
            logging=self._config.logging,
            ground_truth=self._config.ground_truth,
            disturbance=get_preset_config(self._combo_preset.currentText()),
        )
        self._config = new_config
        self._engine = SimulationEngine(self._config)
        self._engine.initialize()
        self._track.reset()
        self._pat_mgr = PATModeManager()
        self._pat_ctrl = PATCameraController()
        self._last_estimate = None
        self._update_display()

    def _on_sim_tick(self) -> None:
        if not self._engine.is_running:
            self._timer.stop()
            self._is_paused = True
            self._btn_play.setText("▶ Start")
            self._lbl_status.setText("Status: Complete (Reached Duration)")
            return

        self._engine.step()
        self._update_display()

    def _update_display(self) -> None:
        state = self._engine.get_current_state()
        world_frame = self._engine.get_current_frame()
        clean_cam_frame = self._engine.get_clean_frame()
        dist_cam_frame = self._engine.get_disturbed_frame()
        camera = self._engine.camera
        telem = self._engine.last_disturbance_telemetry

        # 1. Ground Truth Projection
        _, _, u_true, v_true, in_fov = camera.project_target(state.x, state.y)

        # 2. Execute Phase 4 Perception Detection on Disturbed Frame
        detection_res = self._detector.detect(dist_cam_frame, timestamp=state.timestamp, collect_diagnostics=True)
        self._last_detection = detection_res

        # 3. Execute Phase 5 Target Tracking & State Estimation with Gimbal Compensation
        estimate = self._track.step(
            measurement=detection_res.centroid if (detection_res.detected and not self._suppress_detection_test) else None,
            confidence=detection_res.confidence if not self._suppress_detection_test else 0.0,
            timestamp=state.timestamp,
            gimbal_pan_rate=camera.gimbal.actual_pan_rate,
            gimbal_tilt_rate=camera.gimbal.actual_tilt_rate,
        )
        self._last_estimate = estimate

        # 3a. Execute Phase 6 Closed-Loop PAT Mode Manager & Controller
        dt_step = 1.0 / self._config.simulation.frequency_hz
        cov_trace = float(estimate.position_uncertainty**2)
        search_pan_r, search_tilt_r = self._pat_mgr.search_manager.get_command(
            dt_step, camera.gimbal.pan_deg, camera.gimbal.tilt_deg
        )
        reacq_pan_r, reacq_tilt_r, _ = self._pat_mgr.reacquisition_manager.process_step(
            dt_step, camera.gimbal.pan_deg, camera.gimbal.tilt_deg
        )

        # Valid detection ONLY if Phase 4 detected AND Phase 5 estimator accepted it (not an outlier)
        is_measurement_accepted = (
            detection_res.detected 
            and not self._suppress_detection_test 
            and estimate.filter_status != EstimatorStatus.REJECTED_MEASUREMENT
        )
        valid_confidence = detection_res.confidence if is_measurement_accepted else 0.0

        pat_state = self._pat_mgr.process_step(
            dt=dt_step,
            timestamp_s=state.timestamp,
            detection_valid=is_measurement_accepted,
            detection_confidence=valid_confidence,
            mahalanobis_d2=estimate.mahalanobis_distance**2,
            covariance_trace=cov_trace,
            estimated_u_px=estimate.estimated_x,
            estimated_v_px=estimate.estimated_y,
            estimated_vx_px_s=estimate.estimated_vx,
            estimated_vy_px_s=estimate.estimated_vy,
            current_pan_deg=camera.gimbal.pan_deg,
            current_tilt_deg=camera.gimbal.tilt_deg,
            suppress_detection=self._suppress_detection_test,
        )

        cmd_pan_rate, cmd_tilt_rate, pid_p, pid_t, ff_p, ff_t, is_sat = self._pat_ctrl.compute_control_command(
            dt=dt_step,
            pat_state=pat_state,
            search_pan_rate=search_pan_r,
            search_tilt_rate=search_tilt_r,
            reacquire_pan_rate=reacq_pan_r,
            reacquire_tilt_rate=reacq_tilt_r,
            estimated_vx_px_s=estimate.estimated_vx,
            estimated_vy_px_s=estimate.estimated_vy,
            gimbal=camera.gimbal,
        )

        # Apply controller command to camera gimbal actuator
        camera.gimbal.step(dt_step)

        # Update Phase 6 PAT Telemetry Readouts
        m_str = pat_state.mode.value
        if pat_state.mode == PATMode.TRACK:
            self._lbl_pat_mode.setText("● TRACK")
            self._lbl_pat_mode.setStyleSheet("color: #4cd964; font-weight: bold; font-size: 14px;")
        elif pat_state.mode == PATMode.ACQUIRE:
            self._lbl_pat_mode.setText("◐ ACQUIRE")
            self._lbl_pat_mode.setStyleSheet("color: #00d4ff; font-weight: bold; font-size: 14px;")
        elif pat_state.mode == PATMode.DEGRADED:
            self._lbl_pat_mode.setText("⚠ DEGRADED")
            self._lbl_pat_mode.setStyleSheet("color: #ff9500; font-weight: bold; font-size: 14px;")
        elif pat_state.mode == PATMode.REACQUIRE:
            self._lbl_pat_mode.setText("🔄 REACQUIRE")
            self._lbl_pat_mode.setStyleSheet("color: #ff2d55; font-weight: bold; font-size: 14px;")
        else:
            self._lbl_pat_mode.setText("🔍 SEARCH")
            self._lbl_pat_mode.setStyleSheet("color: #ffcc00; font-weight: bold; font-size: 14px;")

        self._lbl_pat_quality.setText(f"{pat_state.track_quality * 100:.1f}%")
        self._lbl_pat_error.setText(f"Pan: {pat_state.pan_error_deg:+.2f}° | Tilt: {pat_state.tilt_error_deg:+.2f}°")
        self._lbl_pat_cmd_rate.setText(f"Pan: {cmd_pan_rate:+.2f}°/s | Tilt: {cmd_tilt_rate:+.2f}°/s")
        self._lbl_pat_act_rate.setText(f"Pan: {camera.gimbal.actual_pan_rate:+.2f}°/s | Tilt: {camera.gimbal.actual_tilt_rate:+.2f}°/s")
        if is_sat:
            self._lbl_pat_sat.setText("YES (RATE CLAMPED)")
            self._lbl_pat_sat.setStyleSheet("color: #ff3b30; font-weight: bold;")
        else:
            self._lbl_pat_sat.setText("NO")
            self._lbl_pat_sat.setStyleSheet("color: #4cd964; font-weight: bold;")

        # 3a. Update Phase 5 State Estimation Telemetry
        st = estimate.filter_status
        if st == EstimatorStatus.TRACKING:
            self._lbl_est_status.setText("● TRACKING")
            self._lbl_est_status.setStyleSheet("color: #00d4ff; font-weight: bold; font-size: 13px;")
        elif st == EstimatorStatus.PREDICTING:
            self._lbl_est_status.setText("◐ PREDICTING (COAST)")
            self._lbl_est_status.setStyleSheet("color: #ff9500; font-weight: bold; font-size: 13px;")
        elif st == EstimatorStatus.REJECTED_MEASUREMENT:
            self._lbl_est_status.setText("⚠ REJECTED (OUTLIER)")
            self._lbl_est_status.setStyleSheet("color: #ff3b30; font-weight: bold; font-size: 13px;")
        else:
            self._lbl_est_status.setText(f"○ {st.value}")
            self._lbl_est_status.setStyleSheet("color: #888888; font-weight: bold; font-size: 13px;")

        self._lbl_est_pos.setText(f"u: {estimate.estimated_x:.2f} | v: {estimate.estimated_y:.2f} px")
        self._lbl_est_vel.setText(f"Vu: {estimate.estimated_vx:+.1f} | Vv: {estimate.estimated_vy:+.1f} px/s")
        self._lbl_est_unc.setText(f"pos: ±{estimate.position_uncertainty:.2f} px | vel: ±{estimate.velocity_uncertainty:.1f} px/s")
        inno_norm = float(np.linalg.norm(estimate.innovation)) if estimate.innovation is not None else 0.0
        self._lbl_est_inno.setText(f"||y||: {inno_norm:.2f} px | d: {estimate.mahalanobis_distance:.2f}")
        self._lbl_est_latency.setText(f"{estimate.processing_time_ms:.3f} ms ({1000.0/max(estimate.processing_time_ms, 0.01):,.0f} Hz)")

        # 3b. Update Phase 4 Perception Telemetry Readouts
        ox = telem.platform_offset_x if telem else 0.0
        oy = telem.platform_offset_y if telem else 0.0
        jx = telem.camera_jitter_x if telem else 0.0
        jy = telem.camera_jitter_y if telem else 0.0
        effective_u = u_true + ox + jx
        effective_v = v_true + oy + jy

        if detection_res.detected and detection_res.centroid is not None:
            u_est, v_est = detection_res.centroid
            if estimate.filter_status == EstimatorStatus.REJECTED_MEASUREMENT:
                self._lbl_perc_lock.setText("⚠ REJECTED (FALSE POSITIVE)")
                self._lbl_perc_lock.setStyleSheet("color: #ff9500; font-weight: bold; font-size: 13px;")
            else:
                self._lbl_perc_lock.setText("● LOCKED")
                self._lbl_perc_lock.setStyleSheet("color: #4cd964; font-weight: bold; font-size: 13px;")
            self._lbl_perc_centroid.setText(f"u: {u_est:.2f} | v: {v_est:.2f} px")

            tracking_err = math.hypot(u_est - effective_u, v_est - effective_v)
            self._lbl_perc_error.setText(f"{tracking_err:.3f} px")
            self._lbl_perc_conf.setText(f"{detection_res.confidence * 100:.1f}%")
        else:
            self._lbl_perc_lock.setText("○ SEARCHING / LOST")
            self._lbl_perc_lock.setStyleSheet("color: #ff3b30; font-weight: bold; font-size: 13px;")
            self._lbl_perc_centroid.setText("u: N/A | v: N/A")
            self._lbl_perc_error.setText("N/A")
            self._lbl_perc_conf.setText(f"{detection_res.confidence * 100:.1f}%")

        self._lbl_perc_latency.setText(f"{detection_res.processing_time_ms:.1f} ms ({1000.0/max(detection_res.processing_time_ms, 0.1):.0f} FPS)")

        # 4. Ground Truth Telemetry Readouts
        self._lbl_time.setText(f"{state.timestamp:.3f} s")
        self._lbl_frame.setText(str(self._engine.clock.current_frame))
        self._lbl_pos.setText(f"X: {state.x:.2f} | Y: {state.y:.2f} px")
        self._lbl_vel.setText(f"Vx: {state.vx:.2f} | Vy: {state.vy:.2f} px/s")
        self._lbl_cam_pixel.setText(f"u: {u_true:.2f} | v: {v_true:.2f} px")
        if in_fov:
            self._lbl_fov_status.setText("● IN FOV")
            self._lbl_fov_status.setStyleSheet("color: #4cd964; font-weight: bold;")
        else:
            self._lbl_fov_status.setText("○ OUTSIDE FOV")
            self._lbl_fov_status.setStyleSheet("color: #ff3b30; font-weight: bold;")

        # 5. Disturbance Telemetry Readouts
        if telem and telem.disturbance_enabled:
            self._lbl_dt_status.setText("ACTIVE")
            self._lbl_dt_status.setStyleSheet("color: #ff9500; font-weight: bold;")
            sp_str = f"{telem.salt_pepper_probability*100:.1f}%" if telem.salt_pepper_enabled else "OFF"
            self._lbl_sp.setText(sp_str)
            gauss_str = f"σ = {telem.gaussian_sigma:.1f} px" if telem.gaussian_enabled else "OFF"
            self._lbl_gauss.setText(gauss_str)
            poiss_str = f"ON (peak={telem.poisson_parameter:.0f})" if telem.poisson_enabled else "OFF"
            self._lbl_poisson.setText(poiss_str)
            jit_str = f"dx: {telem.camera_jitter_x:+.1f} | dy: {telem.camera_jitter_y:+.1f} px" if telem.camera_jitter_enabled else "OFF"
            self._lbl_jitter.setText(jit_str)
            plat_str = f"ox: {telem.platform_offset_x:+.1f} | oy: {telem.platform_offset_y:+.1f} px" if telem.platform_motion_enabled else "OFF"
            self._lbl_platform.setText(plat_str)
            self._lbl_atmos.setText(f"{telem.atmosphere_condition.upper()} (c={telem.contrast_factor:.2f}, b={telem.brightness_factor:+.2f})")
        else:
            self._lbl_dt_status.setText("DISABLED / NOMINAL")
            self._lbl_dt_status.setStyleSheet("color: #888; font-weight: bold;")
            self._lbl_sp.setText("OFF")
            self._lbl_gauss.setText("OFF")
            self._lbl_poisson.setText("OFF")
            self._lbl_jitter.setText("OFF")
            self._lbl_platform.setText("OFF")
            self._lbl_atmos.setText("CLEAR")

        # 6. Render World with FOV Footprint
        display_world = world_frame.copy()
        bx, by = camera.get_boresight_world_pos()
        w_cam, h_cam = camera.intrinsics.width, camera.intrinsics.height
        c1 = (int(round(bx - w_cam / 2.0)), int(round(by - h_cam / 2.0)))
        c2 = (int(round(bx + w_cam / 2.0)), int(round(by + h_cam / 2.0)))
        cv2.rectangle(display_world, c1, c2, color=120, thickness=2)

        ibx, iby = int(round(bx)), int(round(by))
        cv2.line(display_world, (ibx - 15, iby), (ibx + 15, iby), color=180, thickness=1)
        cv2.line(display_world, (ibx, iby - 15), (ibx, iby + 15), color=180, thickness=1)

        h_w, w_w = display_world.shape
        q_world = QImage(display_world.data, w_w, h_w, w_w, QImage.Format_Grayscale8)
        self._world_label.setPixmap(
            QPixmap.fromImage(q_world).scaled(
                self._world_label.width() - 10,
                self._world_label.height() - 10,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation,
            )
        )

        # 7. Render Clean Camera Feed
        disp_clean = clean_cam_frame.copy()
        cx_i, cy_i = int(camera.intrinsics.cx), int(camera.intrinsics.cy)
        cv2.line(disp_clean, (cx_i - 15, cy_i), (cx_i + 15, cy_i), color=80, thickness=1)
        cv2.line(disp_clean, (cx_i, cy_i - 15), (cx_i, cy_i + 15), color=80, thickness=1)

        hc, wc = disp_clean.shape
        q_clean = QImage(disp_clean.data, wc, hc, wc, QImage.Format_Grayscale8)
        self._clean_cam_label.setPixmap(
            QPixmap.fromImage(q_clean).scaled(
                self._clean_cam_label.width() - 10,
                self._clean_cam_label.height() - 10,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation,
            )
        )

        # 8. Render Phase 4 & Phase 5 Perception + State Tracking Feed
        if detection_res.diagnostics is not None and detection_res.diagnostics.annotated_frame is not None:
            disp_annotated = detection_res.diagnostics.annotated_frame.copy()
        else:
            disp_annotated = cv2.cvtColor(dist_cam_frame, cv2.COLOR_GRAY2BGR)

        # Draw Phase 5 multi-layer tracking diagnostics:
        # White = GT [Eval], Red = Measurement, Cyan = Estimate + Ellipse, Yellow = Prediction
        disp_annotated = draw_tracking_annotations(
            frame=disp_annotated,
            estimate=self._last_estimate,
            ground_truth_pos=(effective_u, effective_v) if in_fov else None,
            measurement_pos=detection_res.centroid if detection_res.detected else None,
            draw_ellipse=True,
            draw_velocity_vector=True,
        )

        # Draw boresight crosshair in faint blue
        cv2.line(disp_annotated, (cx_i - 15, cy_i), (cx_i + 15, cy_i), (100, 80, 50), 1)
        cv2.line(disp_annotated, (cx_i, cy_i - 15), (cx_i, cy_i + 15), (100, 80, 50), 1)

        hd, wd, _ = disp_annotated.shape
        # Convert BGR to RGB for QImage
        disp_rgb = cv2.cvtColor(disp_annotated, cv2.COLOR_BGR2RGB)
        bytes_per_line = 3 * wd
        q_annotated = QImage(disp_rgb.data, wd, hd, bytes_per_line, QImage.Format_RGB888)
        self._dist_cam_label.setPixmap(
            QPixmap.fromImage(q_annotated).scaled(
                self._dist_cam_label.width() - 10,
                self._dist_cam_label.height() - 10,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation,
            )
        )

    def _save_clean_snapshot(self) -> None:
        clean = self._engine.get_clean_frame()
        out_dir = Path("data/snapshots")
        out_dir.mkdir(parents=True, exist_ok=True)
        path = out_dir / "clean_frame.png"
        cv2.imwrite(str(path), clean)
        self._lbl_status.setText(f"Saved: {path.name}")

    def _save_disturbed_snapshot(self) -> None:
        out_dir = Path("data/snapshots")
        out_dir.mkdir(parents=True, exist_ok=True)
        if self._last_detection and self._last_detection.diagnostics:
            path = out_dir / "detection_annotated.png"
            cv2.imwrite(str(path), self._last_detection.diagnostics.annotated_frame)
            self._lbl_status.setText(f"Saved tracking: {path.name}")
        else:
            dist = self._engine.get_disturbed_frame()
            path = out_dir / "disturbed_frame.png"
            cv2.imwrite(str(path), dist)
            self._lbl_status.setText(f"Saved: {path.name}")

    def _export_data(self) -> None:
        out_csv = self._engine.recorder.export_csv("data/ground_truth/debug_export.csv")
        self._engine.recorder.export_json("data/ground_truth/debug_export.json")
        self._lbl_status.setText(f"Exported: {out_csv.name} ({self._engine.recorder.record_count} frames)")


def launch_viewer(config: Optional[AppConfig] = None) -> None:
    """Entry point to launch the PySide6 debug viewer."""
    app = QApplication.instance() or QApplication(sys.argv)
    viewer = SimulationDebugViewer(config=config)
    viewer.show()
    sys.exit(app.exec())
