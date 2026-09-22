"""HORIZON Phase 11.2 Live Tracking Workstation View Component
============================================================
Exact replica of the Phase 1–10 engineering workstation (Screenshot 2)
styled using Phase 11 true neutral design system tokens (`tokens.py`).

Layout Architecture:
  - LEFT COLUMN (70%):
      - Top: Dual Viewports Side-by-Side:
          1. Clean Camera Frame (Ground Truth Reference Feed)
          2. Phase 4 Perception Output (Live Lock & Subpixel Centroid Annotations)
      - Bottom: Macro World Overview (2000×2000 global target & camera FOV map)
  - RIGHT COLUMN (30% Scrollable Telemetry Sidebar):
      - Group 0: Phase 6 Closed-Loop PAT Telemetry
      - Group 1: Phase 5 State Estimation Telemetry (Kalman Filter)
      - Group 2: Phase 4 Perception Telemetry (Live Tracking)
      - Group 3: Phase 3 Disturbance Telemetry
      - Group 4: Ground-Truth Kinematics Telemetry
      - Group 5: Configuration Presets & Live Solver Controls
      - Group 6: Simulation Execution & Export Action Bar

Bound exclusively to real simulation engine, detectors, tracking filters, and PAT mode manager.
No fake data, no dummy counters, no ground-truth leakage into perception.
"""

from __future__ import annotations
import csv
import math
import os
from pathlib import Path
import sys
import time
from typing import Any, Dict, List, Optional, Tuple
import cv2
import numpy as np

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)
from sources import (
    ExternalVideoSource,
    FramePacket,
    VirtualCameraFrameAdapter,
    VideoFrameSource,
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
from simulator.perception.config import CentroidConfig, DetectorConfig
from simulator.perception.detector import ClassicalBeaconDetector, DetectionResult
from simulator.perception.neural_detector import NeuralBeaconDetector
from simulator.perception.hybrid_detector import HybridBeaconDetector
from simulator.perception.sota_detector import SOTABeaconDetector
from tracking.association.track import Track
from tracking.estimation.kalman import EstimatorStatus
from tracking.estimation.state import StateEstimate
from tracking.diagnostics.visualization import draw_tracking_annotations

# PAT System Imports
from pat.mode_manager import PATModeManager
from pat.state import PATMode, PATState
from control.camera_controller import PATCameraController

# UI Foundation Tokens
from simulator.ui.foundation.tokens import (
    COLOR_CONFIRM_GREEN,
    COLOR_DISTURBANCE_AMBER,
    COLOR_FIELD,
    COLOR_FIELD_RAISED,
    COLOR_HAIRLINE_BORDER_HEX,
    COLOR_LOCK_CYAN,
    COLOR_LOST_RED,
    COLOR_TEXT_PRIMARY,
    COLOR_TEXT_SECONDARY,
    COLOR_VOID,
    FONT_BODY,
    FONT_HEADLINE,
    FONT_TELEMETRY,
    SPACING_8,
    SPACING_12,
    SPACING_16,
)
from simulator.ui.live.world_overview_panel import WorldOverviewPanel
from simulator.ui.live.event_timeline import EventTimelineWidget


class LiveScreenView(QWidget):
    """Phase 11.2 Live Tracking Workstation Screen (Screenshot 2 Replica)."""

    # Signal emitted after every simulation step — carries live data for Track screen
    track_data_ready = Signal(object, object, object, object, object, float)
    # (dist_frame: np.ndarray, detection_res, estimate, pat_state, ground_truth_pos, sim_time)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        from simulator.core.config import TargetConfig, TargetInitialPosition, CameraConfig
        self._config = AppConfig(
            camera=CameraConfig(
                max_initial_offset_deg=1.5,  # Seed-derived ±1.5° camera offset so SEARCH is active from launch
                auto_align_boresight=False,
            ),
            target=TargetConfig(initial_position=TargetInitialPosition(x=None, y=None)),  # Seed-placed
            trajectory=TrajectoryConfig(
                type="figure8",
                figure8=FigureEightTrajectoryConfig(amplitude_x=220.0, amplitude_y=140.0, angular_velocity=0.6),
            ),
            disturbance=get_preset_config("NOMINAL"),
        )
        self._engine = SimulationEngine(self._config)
        self._engine.initialize()

        # Detector Setup
        self._centroid_method = "weighted_cog"
        self._perception_mode = "HYBRID"
        self._sota_detector = SOTABeaconDetector(
            DetectorConfig(centroid=CentroidConfig(method=self._centroid_method), perception_mode="SOTA_FOURIER_GMM")
        )
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


        # Tracker & PAT Subsystems
        self._track = Track(track_id=1, filter_type="IMM_ADAPTIVE_EKF")
        self._pat_mgr = PATModeManager()
        self._pat_ctrl = PATCameraController(controller_type="PID")

        self._suppress_detection_test = False
        self._last_estimate: Optional[StateEstimate] = None
        self._last_pat_mode: Optional[PATMode] = PATMode.SEARCH
        self._search_start_time: float = 0.0
        self._frame_count: int = 0
        self._last_fps_calc_time: float = time.time()
        self._current_fps: float = 0.0
        self._is_paused = True

        # External Video Ingestion State (ISRO Evaluation-2)
        self._input_source: str = "VIRTUAL_CAMERA"
        self._external_video: Optional[ExternalVideoSource] = None
        self._video_source: Optional[ExternalVideoSource] = None
        self._video_path: Optional[str] = None
        self._video_log_records: List[Dict[str, Any]] = []
        self._video_last_frame: Optional[np.ndarray] = None
        self._video_gt_data: Dict[int, Tuple[float, float]] = {}

        # Real-time update timer
        self._sim_timer = QTimer(self)
        self._sim_timer.setInterval(33)  # ~30 FPS loop
        self._sim_timer.timeout.connect(self._on_sim_step)

        # Build UI Architecture
        self._setup_ui()
        self._update_ui_displays()

    def _setup_ui(self) -> None:
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(SPACING_8, SPACING_8, SPACING_8, SPACING_8)
        root_layout.setSpacing(SPACING_8)

        # Main Split Layout: Left Viewports (70%) vs Right Telemetry Sidebar (30%)
        main_split = QHBoxLayout()
        main_split.setSpacing(SPACING_12)

        # ======================================================================
        # LEFT COLUMN: VIEWPORTS CONTAINER
        # ======================================================================
        left_container = QWidget(self)
        left_layout = QVBoxLayout(left_container)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(SPACING_12)

        # Top Section: Dual Viewports Box
        dual_box = QGroupBox("Camera Sensor Comparison: Clean vs. Phase 4 Perception Tracking (640×480)", self)
        dual_box.setStyleSheet(f"QGroupBox {{ font-family: {FONT_HEADLINE}; color: {COLOR_TEXT_PRIMARY}; border: 1px solid {COLOR_HAIRLINE_BORDER_HEX}; background-color: {COLOR_FIELD}; border-radius: 4px; padding-top: 18px; }} QGroupBox::title {{ subcontrol-origin: margin; left: 8px; padding: 0 4px; }}")
        dual_layout = QHBoxLayout(dual_box)
        dual_layout.setSpacing(SPACING_12)

        # 1. Clean Camera Frame Viewport
        clean_box = QGroupBox("Clean Camera Frame (Ground Truth)", self)
        clean_box.setStyleSheet(f"QGroupBox {{ font-family: {FONT_HEADLINE}; color: {COLOR_TEXT_SECONDARY}; border: 1px solid {COLOR_HAIRLINE_BORDER_HEX}; background-color: {COLOR_VOID}; border-radius: 4px; padding-top: 16px; }}")
        clean_v_layout = QVBoxLayout(clean_box)
        self._clean_cam_label = QLabel(self)
        self._clean_cam_label.setMinimumSize(360, 270)
        self._clean_cam_label.setAlignment(Qt.AlignCenter)
        self._clean_cam_label.setStyleSheet(f"background-color: {COLOR_VOID}; border: 1px solid {COLOR_HAIRLINE_BORDER_HEX};")
        clean_v_layout.addWidget(self._clean_cam_label)
        dual_layout.addWidget(clean_box)

        # 2. Phase 4 Perception Output Viewport
        dist_box = QGroupBox("Phase 4 Perception Output (Live Lock & Subpixel Centroid)", self)
        dist_box.setStyleSheet(f"QGroupBox {{ font-family: {FONT_HEADLINE}; color: {COLOR_LOCK_CYAN}; border: 1px solid {COLOR_HAIRLINE_BORDER_HEX}; background-color: {COLOR_VOID}; border-radius: 4px; padding-top: 16px; }}")
        dist_v_layout = QVBoxLayout(dist_box)
        self._dist_cam_label = QLabel(self)
        self._dist_cam_label.setMinimumSize(360, 270)
        self._dist_cam_label.setAlignment(Qt.AlignCenter)
        self._dist_cam_label.setStyleSheet(f"background-color: {COLOR_VOID}; border: 1px solid {COLOR_HAIRLINE_BORDER_HEX};")
        dist_v_layout.addWidget(self._dist_cam_label)
        dual_layout.addWidget(dist_box)

        left_layout.addWidget(dual_box, stretch=3)

        # Bottom Section: Macro World Overview (2000x2000)
        self.world_panel = WorldOverviewPanel(self)
        left_layout.addWidget(self.world_panel, stretch=2)

        main_split.addWidget(left_container, stretch=7)

        # ======================================================================
        # RIGHT COLUMN: SCROLLABLE TELEMETRY & CONTROLS SIDEBAR
        # ======================================================================
        scroll_area = QScrollArea(self)
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet(f"QScrollArea {{ border: 1px solid {COLOR_HAIRLINE_BORDER_HEX}; background-color: {COLOR_FIELD}; }}")

        scroll_content = QWidget()
        scroll_content.setStyleSheet(f"background-color: {COLOR_FIELD};")
        sidebar_layout = QVBoxLayout(scroll_content)
        sidebar_layout.setContentsMargins(SPACING_12, SPACING_12, SPACING_12, SPACING_12)
        sidebar_layout.setSpacing(SPACING_12)

        # Group Style Helper
        gb_style = f"QGroupBox {{ font-family: {FONT_HEADLINE}; font-size: 13px; font-weight: bold; color: {COLOR_TEXT_PRIMARY}; border: 1px solid {COLOR_HAIRLINE_BORDER_HEX}; background-color: {COLOR_FIELD_RAISED}; border-radius: 4px; padding-top: 18px; margin-top: 4px; }} QGroupBox::title {{ subcontrol-origin: margin; left: 8px; padding: 0 4px; }}"
        label_val_style = f"font-family: {FONT_TELEMETRY}; color: {COLOR_TEXT_PRIMARY}; font-size: 13px;"

        # --- 0. Phase 6 Closed-Loop PAT Telemetry Box ---
        pat_box = QGroupBox("Phase 6 Closed-Loop PAT Telemetry", self)
        pat_box.setStyleSheet(gb_style)
        pat_form = QFormLayout(pat_box)
        pat_form.setSpacing(6)

        self._lbl_pat_mode = QLabel("SEARCH")
        self._lbl_pat_mode.setStyleSheet(f"font-family: {FONT_TELEMETRY}; color: {COLOR_DISTURBANCE_AMBER}; font-weight: bold; font-size: 13px;")
        self._lbl_pat_quality = QLabel("0.0%")
        self._lbl_pat_quality.setStyleSheet(label_val_style)
        self._lbl_pat_error = QLabel("Pan: 0.00° | Tilt: 0.00°")
        self._lbl_pat_error.setStyleSheet(label_val_style)
        self._lbl_pat_cmd_rate = QLabel("Pan: 0.00°/s | Tilt: 0.00°/s")
        self._lbl_pat_cmd_rate.setStyleSheet(label_val_style)
        self._lbl_pat_act_rate = QLabel("Pan: 0.00°/s | Tilt: 0.00°/s")
        self._lbl_pat_act_rate.setStyleSheet(label_val_style)
        self._lbl_pat_sat = QLabel("NO")
        self._lbl_pat_sat.setStyleSheet(f"font-family: {FONT_TELEMETRY}; color: {COLOR_CONFIRM_GREEN}; font-weight: bold;")

        pat_form.addRow("PAT Mode:", self._lbl_pat_mode)
        pat_form.addRow("Track Quality:", self._lbl_pat_quality)
        pat_form.addRow("Pointing Error (e):", self._lbl_pat_error)
        pat_form.addRow("Commanded Rates (u):", self._lbl_pat_cmd_rate)
        pat_form.addRow("Actual Gimbal Rates:", self._lbl_pat_act_rate)
        pat_form.addRow("Actuator Saturation:", self._lbl_pat_sat)
        sidebar_layout.addWidget(pat_box)

        # --- 1. Phase 5 State Estimation Telemetry Box ---
        est_box = QGroupBox("Phase 5 State Estimation Telemetry (Kalman Filter)", self)
        est_box.setStyleSheet(gb_style)
        est_form = QFormLayout(est_box)
        est_form.setSpacing(6)

        self._lbl_est_status = QLabel("UNINITIALIZED")
        self._lbl_est_status.setStyleSheet(f"font-family: {FONT_TELEMETRY}; color: {COLOR_LOCK_CYAN}; font-weight: bold;")
        self._lbl_est_pos = QLabel("u: 0.00 | v: 0.00 px")
        self._lbl_est_pos.setStyleSheet(label_val_style)
        self._lbl_est_vel = QLabel("Vu: 0.00 | Vv: 0.00 px/s")
        self._lbl_est_vel.setStyleSheet(label_val_style)
        self._lbl_est_unc = QLabel("pos: ±0.00 px | vel: ±0.00 px/s")
        self._lbl_est_unc.setStyleSheet(label_val_style)
        self._lbl_est_inno = QLabel("||y||: 0.00 px | d²: 0.00")
        self._lbl_est_inno.setStyleSheet(label_val_style)
        self._lbl_est_latency = QLabel("0.0 ms")
        self._lbl_est_latency.setStyleSheet(label_val_style)

        est_form.addRow("Filter Status:", self._lbl_est_status)
        est_form.addRow("Estimated Position:", self._lbl_est_pos)
        est_form.addRow("Estimated Velocity:", self._lbl_est_vel)
        est_form.addRow("1-Sigma Uncertainty:", self._lbl_est_unc)
        est_form.addRow("Innovation / Gate:", self._lbl_est_inno)
        est_form.addRow("Estimator Latency:", self._lbl_est_latency)
        sidebar_layout.addWidget(est_box)

        # --- 2. Phase 4 Perception Telemetry Box ---
        perc_box = QGroupBox("Phase 4 Perception Telemetry (Live Tracking)", self)
        perc_box.setStyleSheet(gb_style)
        perc_form = QFormLayout(perc_box)
        perc_form.setSpacing(6)

        self._lbl_perc_lock = QLabel("LOCKED")
        self._lbl_perc_lock.setStyleSheet(f"font-family: {FONT_TELEMETRY}; color: {COLOR_CONFIRM_GREEN}; font-weight: bold;")
        self._lbl_perc_centroid = QLabel("u: 0.00 | v: 0.00 px")
        self._lbl_perc_centroid.setStyleSheet(label_val_style)
        self._lbl_perc_error = QLabel("0.000 px")
        self._lbl_perc_error.setStyleSheet(f"font-family: {FONT_TELEMETRY}; color: {COLOR_LOCK_CYAN}; font-weight: bold;")
        self._lbl_perc_conf = QLabel("0.0%")
        self._lbl_perc_conf.setStyleSheet(label_val_style)
        self._lbl_perc_latency = QLabel("0.0 ms")
        self._lbl_perc_latency.setStyleSheet(label_val_style)

        perc_form.addRow("Tracking State:", self._lbl_perc_lock)
        perc_form.addRow("Estimated Centroid:", self._lbl_perc_centroid)
        perc_form.addRow("Subpixel Error vs GT:", self._lbl_perc_error)
        perc_form.addRow("Detection Confidence:", self._lbl_perc_conf)
        perc_form.addRow("Perception Latency:", self._lbl_perc_latency)
        sidebar_layout.addWidget(perc_box)

        # --- 3. Disturbance Telemetry Box ---
        dist_tele_box = QGroupBox("Disturbance Telemetry (Phase 3)", self)
        dist_tele_box.setStyleSheet(gb_style)
        dt_form = QFormLayout(dist_tele_box)
        dt_form.setSpacing(6)

        self._lbl_dt_status = QLabel("ENABLED")
        self._lbl_dt_status.setStyleSheet(f"font-family: {FONT_TELEMETRY}; color: {COLOR_DISTURBANCE_AMBER}; font-weight: bold;")
        self._lbl_sp = QLabel("OFF")
        self._lbl_sp.setStyleSheet(label_val_style)
        self._lbl_gauss = QLabel("OFF")
        self._lbl_gauss.setStyleSheet(label_val_style)
        self._lbl_poisson = QLabel("OFF")
        self._lbl_poisson.setStyleSheet(label_val_style)
        self._lbl_jitter = QLabel("dx: +0.00 | dy: +0.00 px")
        self._lbl_jitter.setStyleSheet(label_val_style)
        self._lbl_platform = QLabel("ox: +0.00 | oy: +0.00 px")
        self._lbl_platform.setStyleSheet(label_val_style)
        self._lbl_atmos = QLabel("CLEAR")
        self._lbl_atmos.setStyleSheet(label_val_style)

        dt_form.addRow("Disturbance State:", self._lbl_dt_status)
        dt_form.addRow("Salt & Pepper:", self._lbl_sp)
        dt_form.addRow("Gaussian Noise:", self._lbl_gauss)
        dt_form.addRow("Poisson Shot Noise:", self._lbl_poisson)
        dt_form.addRow("Camera Jitter:", self._lbl_jitter)
        dt_form.addRow("Platform Motion:", self._lbl_platform)
        dt_form.addRow("Atmosphere:", self._lbl_atmos)
        sidebar_layout.addWidget(dist_tele_box)

        # --- 4. Ground-Truth Kinematics Telemetry Box ---
        gt_box = QGroupBox("Ground-Truth Telemetry", self)
        gt_box.setStyleSheet(gb_style)
        gt_form = QFormLayout(gt_box)
        gt_form.setSpacing(6)

        self._lbl_time = QLabel("0.000 s")
        self._lbl_time.setStyleSheet(label_val_style)
        self._lbl_frame = QLabel("0")
        self._lbl_frame.setStyleSheet(label_val_style)
        self._lbl_pos = QLabel("X: 0.00 | Y: 0.00 px")
        self._lbl_pos.setStyleSheet(label_val_style)
        self._lbl_vel = QLabel("Vx: 0.00 | Vy: 0.00 px/s")
        self._lbl_vel.setStyleSheet(label_val_style)
        self._lbl_cam_pixel = QLabel("u: 0.00 | v: 0.00 px")
        self._lbl_cam_pixel.setStyleSheet(label_val_style)
        self._lbl_fov_status = QLabel("INSIDE FOV")
        self._lbl_fov_status.setStyleSheet(f"font-family: {FONT_TELEMETRY}; color: {COLOR_CONFIRM_GREEN}; font-weight: bold;")

        gt_form.addRow("Simulation Time:", self._lbl_time)
        gt_form.addRow("Frame Number:", self._lbl_frame)
        gt_form.addRow("Target World Pos:", self._lbl_pos)
        gt_form.addRow("Target Velocity:", self._lbl_vel)
        gt_form.addRow("True Projected (u, v):", self._lbl_cam_pixel)
        gt_form.addRow("Camera FOV Status:", self._lbl_fov_status)
        sidebar_layout.addWidget(gt_box)

        # Button & Combo Style Helpers
        btn_style = f"QPushButton {{ background-color: {COLOR_FIELD_RAISED}; color: {COLOR_TEXT_PRIMARY}; border: 1px solid {COLOR_HAIRLINE_BORDER_HEX}; border-radius: 4px; padding: 8px; font-weight: bold; font-family: {FONT_HEADLINE}; }} QPushButton:hover {{ background-color: #2a2a30; border-color: {COLOR_LOCK_CYAN}; }}"
        combo_style = f"QComboBox {{ background-color: {COLOR_VOID}; color: {COLOR_TEXT_PRIMARY}; border: 1px solid {COLOR_HAIRLINE_BORDER_HEX}; border-radius: 3px; padding: 4px; font-family: {FONT_BODY}; }}"

        # --- 4b. Video Input Source & Ingestion (ISRO Evaluation-2) ---
        src_box = QGroupBox("Video Input Source (ISRO Evaluation-2)", self)
        src_box.setStyleSheet(gb_style)
        src_form = QFormLayout(src_box)
        src_form.setSpacing(6)

        self._combo_input_source = QComboBox(self)
        self._combo_input_source.addItems(["VIRTUAL_CAMERA", "EXTERNAL_VIDEO"])
        self._combo_input_source.setStyleSheet(combo_style)
        self._combo_input_source.currentTextChanged.connect(self._on_input_source_changed)
        src_form.addRow("Input Mode:", self._combo_input_source)

        self._btn_load_video = QPushButton("📁 Load External MP4...", self)
        self._btn_load_video.setStyleSheet(btn_style)
        self._btn_load_video.clicked.connect(self._on_load_video_clicked)
        src_form.addRow("Test Video:", self._btn_load_video)

        self._lbl_video_info = QLabel("")
        self._lbl_video_info.setWordWrap(True)
        self._lbl_video_info.setStyleSheet(f"font-family: {FONT_TELEMETRY}; color: {COLOR_TEXT_SECONDARY}; font-size: 11px;")
        self._update_source_info_display()
        src_form.addRow("Source Info:", self._lbl_video_info)

        self._btn_export_video_log = QPushButton("📊 Export Centroid Log (CSV)", self)
        self._btn_export_video_log.setStyleSheet(btn_style)
        self._btn_export_video_log.clicked.connect(self._on_export_centroid_csv_clicked)
        src_form.addRow("Centroid Log:", self._btn_export_video_log)

        sidebar_layout.addWidget(src_box)

        # --- 5. Configuration & Presets Form Box ---
        cfg_box = QGroupBox("Configuration Presets", self)
        cfg_box.setStyleSheet(gb_style)
        cfg_form = QFormLayout(cfg_box)
        cfg_form.setSpacing(6)

        self._combo_perc_mode = QComboBox(self)
        self._combo_perc_mode.addItems(["HYBRID", "SOTA_FOURIER_GMM", "NEURAL", "CLASSICAL"])
        self._combo_perc_mode.setStyleSheet(combo_style)

        self._combo_perc_mode.currentTextChanged.connect(self._on_perc_mode_changed)
        cfg_form.addRow("Perception Engine:", self._combo_perc_mode)

        self._combo_estimator = QComboBox(self)
        self._combo_estimator.addItems(["IMM_ADAPTIVE_EKF", "STANDARD_EKF"])
        self._combo_estimator.setStyleSheet(combo_style)
        self._combo_estimator.currentTextChanged.connect(self._on_estimator_changed)
        cfg_form.addRow("State Estimator:", self._combo_estimator)

        self._combo_controller = QComboBox(self)
        self._combo_controller.addItems(["PID", "ADRC_NONLINEAR", "LQG"])
        self._combo_controller.setStyleSheet(combo_style)

        self._combo_controller.currentTextChanged.connect(self._on_controller_changed)
        cfg_form.addRow("Controller Mode:", self._combo_controller)

        self._combo_method = QComboBox(self)
        self._combo_method.addItems(["weighted_cog", "gaussian_fit", "geometric"])
        self._combo_method.setStyleSheet(combo_style)
        self._combo_method.currentTextChanged.connect(self._on_method_changed)
        cfg_form.addRow("Centroid Method:", self._combo_method)

        self._combo_preset = QComboBox(self)
        self._combo_preset.addItems(["NOMINAL", "DIFFICULT", "SEVERE", "ADVERSARIAL", "RECOVERY"])
        self._combo_preset.setCurrentText("NOMINAL")
        self._combo_preset.setStyleSheet(combo_style)
        self._combo_preset.currentTextChanged.connect(self._on_preset_changed)
        cfg_form.addRow("Disturbance Preset:", self._combo_preset)

        self._combo_traj = QComboBox(self)
        self._combo_traj.addItems(["figure8", "sinusoidal", "circular", "straight", "random", "spiral"])
        self._combo_traj.setStyleSheet(combo_style)
        self._combo_traj.currentTextChanged.connect(lambda _: self._reset_sim())
        cfg_form.addRow("Trajectory:", self._combo_traj)

        spin_style = f"QSpinBox, QDoubleSpinBox {{ background-color: {COLOR_VOID}; color: {COLOR_TEXT_PRIMARY}; border: 1px solid {COLOR_HAIRLINE_BORDER_HEX}; border-radius: 3px; padding: 4px; font-family: {FONT_TELEMETRY}; }}"

        self._spin_seed = QSpinBox(self)
        self._spin_seed.setRange(0, 999999)
        self._spin_seed.setValue(42)
        self._spin_seed.setStyleSheet(spin_style)
        self._spin_seed.valueChanged.connect(lambda _: self._reset_sim())
        cfg_form.addRow("Random Seed:", self._spin_seed)

        self._spin_duration = QDoubleSpinBox(self)
        self._spin_duration.setRange(1.0, 3600.0)
        self._spin_duration.setValue(40.0)
        self._spin_duration.setSuffix(" s")
        self._spin_duration.setStyleSheet(spin_style)
        self._spin_duration.valueChanged.connect(lambda _: self._reset_sim())
        cfg_form.addRow("Duration:", self._spin_duration)

        self._combo_beacon_shape = QComboBox(self)
        self._combo_beacon_shape.addItems(["Circular (Gaussian)", "Square (Box)"])
        self._combo_beacon_shape.setStyleSheet(combo_style)
        self._combo_beacon_shape.currentTextChanged.connect(lambda _: self._reset_sim())
        cfg_form.addRow("Beacon Shape:", self._combo_beacon_shape)

        self._spin_beacon_size = QSpinBox(self)
        self._spin_beacon_size.setRange(5, 20)
        self._spin_beacon_size.setValue(10)
        self._spin_beacon_size.setSuffix(" px")
        self._spin_beacon_size.setStyleSheet(spin_style)
        self._spin_beacon_size.valueChanged.connect(lambda _: self._reset_sim())
        cfg_form.addRow("Beacon Size:", self._spin_beacon_size)

        sidebar_layout.addWidget(cfg_box)

        # --- 6. Execution & Export Action Controls ---
        btn_style = f"QPushButton {{ background-color: {COLOR_FIELD_RAISED}; color: {COLOR_TEXT_PRIMARY}; border: 1px solid {COLOR_HAIRLINE_BORDER_HEX}; border-radius: 4px; padding: 8px; font-weight: bold; font-family: {FONT_HEADLINE}; }} QPushButton:hover {{ background-color: #2a2a30; border-color: {COLOR_LOCK_CYAN}; }}"

        btn_row1 = QHBoxLayout()
        self._btn_play = QPushButton("▶ Resume", self)
        self._btn_play.setStyleSheet(btn_style)
        self._btn_play.clicked.connect(self._toggle_play)
        btn_row1.addWidget(self._btn_play)

        self._btn_reset = QPushButton("↺ Reset", self)
        self._btn_reset.setStyleSheet(btn_style)
        self._btn_reset.clicked.connect(self._reset_sim)
        btn_row1.addWidget(self._btn_reset)
        sidebar_layout.addLayout(btn_row1)

        btn_row2 = QHBoxLayout()
        self._btn_snap_clean = QPushButton("📷 Save Clean", self)
        self._btn_snap_clean.setStyleSheet(btn_style)
        self._btn_snap_clean.clicked.connect(self._save_clean_snapshot)
        btn_row2.addWidget(self._btn_snap_clean)

        self._btn_snap_dist = QPushButton("📷 Save Tracking", self)
        self._btn_snap_dist.setStyleSheet(btn_style)
        self._btn_snap_dist.clicked.connect(self._save_disturbed_snapshot)
        btn_row2.addWidget(self._btn_snap_dist)
        sidebar_layout.addLayout(btn_row2)

        self._btn_export = QPushButton("💾 Export Ground Truth (CSV)", self)
        self._btn_export.setStyleSheet(btn_style)
        self._btn_export.clicked.connect(self._export_data)
        sidebar_layout.addWidget(self._btn_export)

        self._btn_gen_report = QPushButton("📊 Export Engineering Report", self)
        self._btn_gen_report.setStyleSheet(f"QPushButton {{ background-color: #1e2d42; color: {COLOR_LOCK_CYAN}; border: 1px solid {COLOR_LOCK_CYAN}; border-radius: 4px; padding: 8px; font-weight: bold; font-family: {FONT_HEADLINE}; }} QPushButton:hover {{ background-color: #283d5a; }}")
        self._btn_gen_report.clicked.connect(self._generate_engineering_report)
        sidebar_layout.addWidget(self._btn_gen_report)

        self._btn_test_blackout = QPushButton("⚡ Suppress Detection (Test Loss)", self)
        self._btn_test_blackout.setCheckable(True)
        self._btn_test_blackout.setStyleSheet(f"QPushButton {{ background-color: #3a2024; color: {COLOR_LOST_RED}; border: 1px solid {COLOR_LOST_RED}; border-radius: 4px; padding: 8px; font-weight: bold; font-family: {FONT_HEADLINE}; }} QPushButton:checked {{ background-color: {COLOR_LOST_RED}; color: #ffffff; }}")
        self._btn_test_blackout.clicked.connect(self._toggle_blackout_test)
        sidebar_layout.addWidget(self._btn_test_blackout)

        self._lbl_status = QLabel("Status: Ready (Paused)", self)
        self._lbl_status.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-style: italic; font-family: {FONT_BODY};")
        sidebar_layout.addWidget(self._lbl_status)

        sidebar_layout.addStretch()
        scroll_area.setWidget(scroll_content)
        main_split.addWidget(scroll_area, stretch=3)

        root_layout.addLayout(main_split, stretch=1)

        # Bottom Event Timeline Strip
        self.event_timeline = EventTimelineWidget(self)
        root_layout.addWidget(self.event_timeline)

    # --------------------------------------------------------------------------
    # Configuration & Control Event Handlers
    # --------------------------------------------------------------------------
    def _update_detectors(self) -> None:
        self._centroid_method = self._combo_method.currentText()
        self._perception_mode = self._combo_perc_mode.currentText()
        cent_cfg = CentroidConfig(method=self._centroid_method)
        self._classical_detector = ClassicalBeaconDetector(
            DetectorConfig(centroid=cent_cfg, perception_mode="CLASSICAL")
        )
        self._neural_detector = NeuralBeaconDetector(
            DetectorConfig(centroid=cent_cfg, perception_mode="NEURAL")
        )
        self._hybrid_detector = HybridBeaconDetector(
            DetectorConfig(centroid=cent_cfg, perception_mode="HYBRID")
        )
        self._sota_detector = SOTABeaconDetector(
            DetectorConfig(centroid=cent_cfg, perception_mode="SOTA_FOURIER_GMM")
        )
        if self._perception_mode == "SOTA_FOURIER_GMM":
            self._detector = self._sota_detector
        elif self._perception_mode == "NEURAL":
            self._detector = self._neural_detector
        elif self._perception_mode == "HYBRID":
            self._detector = self._hybrid_detector
        else:
            self._detector = self._classical_detector

    def _on_perc_mode_changed(self, mode_str: str) -> None:
        self._update_detectors()
        self._reset_sim()

    def _on_estimator_changed(self, est_str: str) -> None:
        self._reset_sim()

    def _on_controller_changed(self, ctrl_str: str) -> None:
        self._reset_sim()

    def _on_method_changed(self, method_name: str) -> None:
        self._update_detectors()
        self._reset_sim()

    def _on_preset_changed(self, preset_name: str) -> None:
        if self._combo_preset.currentText() != preset_name:
            self._combo_preset.setCurrentText(preset_name)
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
            if self._input_source == "EXTERNAL_VIDEO":
                if self._external_video is None or not self._external_video.is_open:
                    self._on_load_video_clicked()
                    if self._external_video is None or not self._external_video.is_open:
                        return
                self._external_video.resume()
                self._lbl_status.setText("Status: Playing External Video...")
                self._update_source_info_display()
            else:
                self._lbl_status.setText("Status: Simulating & Tracking...")
            self._is_paused = False
            self._btn_play.setText("⏸ Pause")
            self._sim_timer.start()
        else:
            self._is_paused = True
            self._btn_play.setText("▶ Resume")
            self._lbl_status.setText("Status: Paused")
            self._sim_timer.stop()
            if self._input_source == "EXTERNAL_VIDEO" and self._external_video:
                self._external_video.pause()
                self._update_source_info_display()

    def _toggle_blackout_test(self, checked: bool) -> None:
        self._suppress_detection_test = checked
        if self._input_source == "EXTERNAL_VIDEO" and self._external_video:
            curr_t = self._external_video.timestamp
        else:
            curr_t = self._engine.clock.current_time if self._engine else 0.0
        if checked:
            self.event_timeline.add_event(curr_t, "DEGRADED", "Forced detection blackout test activated")
            self._btn_test_blackout.setText("⚡ Detection SUPPRESSED (Active Test)")
        else:
            self.event_timeline.add_event(curr_t, "REACQUIRE", "Detection blackout test deactivated")
            self._btn_test_blackout.setText("⚡ Suppress Detection (Test Loss)")

    def _reset_sim(self) -> None:
        self._sim_timer.stop()
        self._is_paused = True
        self._btn_play.setText("▶ Resume")

        if self._input_source == "EXTERNAL_VIDEO" and self._external_video is not None:
            self._external_video.reset()
            self._video_log_records.clear()
            self.event_timeline.clear_events()
            self.event_timeline.add_event(0.0, "SEARCH", f"Video stream reset to frame 0 ({self._external_video.filename})")
            packet = self._external_video.read_frame()
            if packet.valid and packet.frame is not None:
                self._video_last_frame = packet.frame
                self._external_video.seek(0)
                disp_clean = cv2.cvtColor(packet.frame, cv2.COLOR_GRAY2BGR) if packet.frame.ndim == 2 else packet.frame.copy()
                self._render_opencv_to_label(disp_clean, self._clean_cam_label)
                self._render_opencv_to_label(disp_clean, self._dist_cam_label)
                self._lbl_frame.setText("0")
                self._lbl_time.setText("0.000 s")
            self._lbl_status.setText(f"Status: Video Reset (Frame 0: {self._external_video.filename})")
            self._update_source_info_display()
            return

        self._lbl_status.setText("Status: Reset")

        from simulator.core.config import TargetConfig, TargetInitialPosition, CameraConfig
        traj_name = self._combo_traj.currentText()
        is_circle = "Circular" in self._combo_beacon_shape.currentText()
        b_size = self._spin_beacon_size.value()

        cam_cfg = CameraConfig(
            width=self._config.camera.width,
            height=self._config.camera.height,
            fov_horizontal_deg=self._config.camera.fov_horizontal_deg,
            fov_vertical_deg=self._config.camera.fov_vertical_deg,
            update_rate_hz=self._config.camera.update_rate_hz,
            rate_limit_deg_s=self._config.camera.rate_limit_deg_s,
            initial_pan_deg=self._config.camera.initial_pan_deg,
            initial_tilt_deg=self._config.camera.initial_tilt_deg,
            max_initial_offset_deg=1.5,   # Seed-derived random offset ±1.5° so SEARCH is exercised
            auto_align_boresight=False,   # Do NOT auto-align — camera must search for beacon
        )

        new_config = AppConfig(
            world=self._config.world,
            camera=cam_cfg,
            target=TargetConfig(
                size_px=b_size,
                intensity=self._config.target.intensity,
                initial_position=TargetInitialPosition(x=None, y=None),  # Seed-derived position
                psf_model="gaussian" if is_circle else "box",
                psf_sigma_px=max(1.0, b_size / 6.0),
                psf_background_adu=self._config.target.psf_background_adu,
            ),
            simulation=SimulationConfig(
                frequency_hz=self._config.simulation.frequency_hz,
                seed=self._spin_seed.value(),
                duration_seconds=self._spin_duration.value(),
            ),
            trajectory=TrajectoryConfig(
                type=traj_name,
                straight=self._config.trajectory.straight,
                circular=CircularTrajectoryConfig(radius=120.0, angular_velocity=0.6)
                if traj_name == "circular"
                else self._config.trajectory.circular,
                figure8=FigureEightTrajectoryConfig(amplitude_x=220.0, amplitude_y=140.0, angular_velocity=0.6)
                if traj_name == "figure8"
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

        est_str = self._combo_estimator.currentText()
        ctrl_str = self._combo_controller.currentText()
        # Full mapping: PID → PID, ADRC_NONLINEAR → ADRC, LQG → LQG
        if ctrl_str == "ADRC_NONLINEAR":
            c_type = "ADRC"
        elif ctrl_str == "LQG":
            c_type = "LQG"
        else:
            c_type = "PID"

        self._update_detectors()
        self._track = Track(track_id=1, filter_type=est_str)
        self._pat_mgr = PATModeManager()
        self._pat_ctrl = PATCameraController(controller_type=c_type)
        self._last_estimate = None
        self._last_pat_mode = PATMode.SEARCH
        self._search_start_time = 0.0

        self.event_timeline.clear_events()
        self.event_timeline.add_event(0.0, "SEARCH", "System reset to initial SEARCH state")
        self._update_ui_displays()

    def _on_reset_clicked(self) -> None:
        """Alias for _reset_sim for backward compatibility."""
        self._reset_sim()

    # --------------------------------------------------------------------------
    # External Video Ingestion Handlers (ISRO Evaluation-2 / Phase 1B)
    # --------------------------------------------------------------------------
    def _update_source_info_display(self) -> None:
        """Update Source Info UI with dynamic metadata according to Phase 1B Step 3."""
        if self._input_source == "EXTERNAL_VIDEO" and self._external_video is not None and self._external_video.is_open:
            v = self._external_video
            info_text = (
                f"File: {v.filename}\n"
                f"Resolution: {v.width}x{v.height}\n"
                f"FPS: {v.fps:.2f} FPS\n"
                f"Duration: {v.duration:.2f}s\n"
                f"Frames: {v.frame_count}\n"
                f"Status: {v.status}"
            )
            if self._video_gt_data:
                info_text += f"\n✓ Ground Truth ({len(self._video_gt_data)} frames)"
        else:
            cam_w = self._config.camera.width
            cam_h = self._config.camera.height
            fps = float(self._config.simulation.frequency_hz)
            duration = float(self._config.simulation.duration_seconds)
            total_f = int(self._config.simulation.total_frames)
            sim_status = "RUNNING" if (self._engine and self._engine.is_running and not self._is_paused) else "READY"
            info_text = (
                f"File: N/A (Internal Simulation)\n"
                f"Resolution: {cam_w}x{cam_h}\n"
                f"FPS: {fps:.2f} FPS\n"
                f"Duration: {duration:.2f}s\n"
                f"Frames: {total_f}\n"
                f"Status: {sim_status}"
            )
        self._lbl_video_info.setText(info_text)

    def _on_input_source_changed(self, mode: str) -> None:
        self._input_source = mode
        if mode == "EXTERNAL_VIDEO":
            if self._external_video is None or not self._external_video.is_open:
                self._on_load_video_clicked()
            else:
                self._lbl_status.setText(f"Status: Video Mode [{self._external_video.filename}]")
                self._update_source_info_display()
        else:
            self._lbl_status.setText("Status: Virtual Camera Simulation")
            self._reset_sim()
            self._update_source_info_display()

    def _on_load_video_clicked(self) -> None:
        default_dir = "data/samples" if os.path.exists("data/samples") else ""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Test Video for Tracking Evaluation (ISRO PS-2)",
            default_dir,
            "Video Files (*.mp4 *.avi *.mov *.mkv);;All Files (*.*)",
        )
        if not file_path:
            if self._external_video is None or not self._external_video.is_open:
                self._combo_input_source.blockSignals(True)
                self._combo_input_source.setCurrentText("VIRTUAL_CAMERA")
                self._combo_input_source.blockSignals(False)
                self._input_source = "VIRTUAL_CAMERA"
                self._update_source_info_display()
            return

        self.load_video_source(file_path)

    def load_video_source(self, file_path: str) -> bool:
        """Load and initialize an external video file for live beacon tracking."""
        try:
            if self._external_video is not None:
                self._external_video.close()

            vsource = ExternalVideoSource(file_path)
            if not vsource.open():
                QMessageBox.critical(self, "Video Load Error", f"Failed to open or validate video file:\n{file_path}")
                return False

            self._external_video = vsource
            self._video_source = vsource  # Alias for backward compatibility
            self._video_path = file_path
            self._video_log_records = []
            self._input_source = "EXTERNAL_VIDEO"

            self._combo_input_source.blockSignals(True)
            self._combo_input_source.setCurrentText("EXTERNAL_VIDEO")
            self._combo_input_source.blockSignals(False)

            # Check for accompanying ground truth CSV
            self._video_gt_data = {}
            base_no_ext = os.path.splitext(file_path)[0]
            gt_candidates = [f"{base_no_ext}_gt.csv", f"{base_no_ext}.csv"]
            for cand in gt_candidates:
                if os.path.isfile(cand):
                    try:
                        with open(cand, "r", encoding="utf-8") as f:
                            reader = csv.DictReader(f)
                            for row in reader:
                                f_idx = int(row.get("frame_idx", row.get("frame", -1)))
                                u_val = float(row.get("ground_truth_u", row.get("true_u", row.get("u", 0.0))))
                                v_val = float(row.get("ground_truth_v", row.get("true_v", row.get("v", 0.0))))
                                if f_idx >= 0:
                                    self._video_gt_data[f_idx] = (u_val, v_val)
                    except Exception:
                        pass
                    break

            self._update_source_info_display()

            # Dynamic timer interval based on video native FPS
            timer_interval_ms = max(1, int(round(1000.0 / max(vsource.fps, 1.0))))
            self._sim_timer.setInterval(timer_interval_ms)

            # Timeline event
            self.event_timeline.clear_events()
            self.event_timeline.add_event(
                0.0,
                "SEARCH",
                f"Loaded test video: {vsource.filename} ({vsource.frame_count} frames @ {vsource.fps:.1f} FPS)",
            )

            # Read first frame to prime the viewports without running tracking
            packet = self._external_video.read_frame()
            if packet.valid and packet.frame is not None:
                self._video_last_frame = packet.frame
                self._external_video.seek(0)
                disp_clean = cv2.cvtColor(packet.frame, cv2.COLOR_GRAY2BGR) if packet.frame.ndim == 2 else packet.frame.copy()
                self._render_opencv_to_label(disp_clean, self._clean_cam_label)
                self._render_opencv_to_label(disp_clean, self._dist_cam_label)
                self._lbl_frame.setText("0")
                self._lbl_time.setText("0.000 s")

            self._is_paused = True
            self._btn_play.setText("▶ Resume")
            self._lbl_status.setText(f"Status: Video Ready ({vsource.filename})")
            return True
        except Exception as ex:
            QMessageBox.critical(self, "Video Load Failed", f"Error loading video:\n{str(ex)}")
            return False

    def _execute_video_step(self, step_start_t: float) -> None:
        """Execute a single frame decode and display step on the external video stream."""
        if self._external_video is None or not self._external_video.is_open:
            self._sim_timer.stop()
            self._is_paused = True
            self._btn_play.setText("▶ Resume")
            self._lbl_status.setText("Status: No video source loaded")
            self._update_source_info_display()
            return

        # FPS Tracking
        self._frame_count += 1
        now = time.time()
        dt_fps = now - self._last_fps_calc_time
        if dt_fps >= 1.0:
            self._current_fps = self._frame_count / dt_fps
            self._frame_count = 0
            self._last_fps_calc_time = now

        packet = self._external_video.read_frame()
        if not packet.valid or packet.frame is None or self._external_video.is_eof:
            self._sim_timer.stop()
            self._is_paused = True
            self._btn_play.setText("▶ Resume")
            self._lbl_status.setText(f"Status: Video Complete ({packet.frame_id} frames)")
            self._update_source_info_display()
            self.event_timeline.add_event(
                packet.timestamp,
                "TRACK COMPLETE",
                f"External video stream complete ({packet.frame_id} frames).",
            )
            return

        self._video_last_frame = packet.frame
        frame = packet.frame
        timestamp = packet.timestamp
        frame_idx = packet.frame_id

        # Update frame & time telemetry readouts
        self._lbl_time.setText(f"{timestamp:.3f} s")
        self._lbl_frame.setText(str(frame_idx))

        # 1. Optical Detection (if detector active)
        detection_res = None
        meas_pixel = None
        if hasattr(self, "_detector") and self._detector is not None:
            detection_res = self._detector.detect(frame, timestamp=timestamp, collect_diagnostics=True)
            if detection_res and detection_res.detected:
                meas_pixel = detection_res.centroid

        # 2. Kalman Filter Estimation Step (no physical gimbal moving, rates=0)
        estimate = None
        if hasattr(self, "_track") and self._track is not None:
            estimate = self._track.step(
                measurement=meas_pixel if not self._suppress_detection_test else None,
                confidence=detection_res.confidence if (detection_res and not self._suppress_detection_test) else 0.0,
                timestamp=timestamp,
                gimbal_pan_rate=0.0,
                gimbal_tilt_rate=0.0,
            )
            self._last_estimate = estimate

        # 3. PAT Mode Manager Step
        pat_state = None
        if hasattr(self, "_pat_mgr") and self._pat_mgr is not None and estimate is not None:
            fps = max(self._external_video.fps, 1.0)
            dt_step = 1.0 / fps
            cov_trace = float(estimate.position_uncertainty**2)
            is_measurement_accepted = (
                detection_res is not None
                and detection_res.detected
                and not self._suppress_detection_test
                and estimate.filter_status != EstimatorStatus.REJECTED_MEASUREMENT
            )
            valid_confidence = detection_res.confidence if (detection_res and is_measurement_accepted) else 0.0
            pat_state = self._pat_mgr.process_step(
                dt=dt_step,
                timestamp_s=timestamp,
                detection_valid=is_measurement_accepted,
                detection_confidence=valid_confidence,
                mahalanobis_d2=estimate.mahalanobis_distance**2,
                covariance_trace=cov_trace,
                estimated_u_px=estimate.estimated_x,
                estimated_v_px=estimate.estimated_y,
                estimated_vx_px_s=estimate.estimated_vx,
                estimated_vy_px_s=estimate.estimated_vy,
                current_pan_deg=0.0,
                current_tilt_deg=0.0,
                suppress_detection=self._suppress_detection_test,
            )

        # 4. Pointing Error & Centroid Error calculation
        gt_pixel = self._video_gt_data.get(frame_idx, None)
        pixel_error = None
        if gt_pixel and meas_pixel:
            pixel_error = math.hypot(meas_pixel[0] - gt_pixel[0], meas_pixel[1] - gt_pixel[1])

        latency_ms = (time.perf_counter() - step_start_t) * 1000.0

        # 5. Append record to video log
        rec = {
            "frame_idx": frame_idx,
            "timestamp_s": round(timestamp, 4),
            "detected": 1 if (detection_res and detection_res.detected) else 0,
            "centroid_u": round(float(meas_pixel[0]), 3) if meas_pixel else "",
            "centroid_v": round(float(meas_pixel[1]), 3) if meas_pixel else "",
            "estimated_u": round(float(estimate.estimated_x), 3) if estimate else "",
            "estimated_v": round(float(estimate.estimated_y), 3) if estimate else "",
            "estimated_vx": round(float(estimate.estimated_vx), 3) if estimate else "",
            "estimated_vy": round(float(estimate.estimated_vy), 3) if estimate else "",
            "ground_truth_u": round(float(gt_pixel[0]), 3) if gt_pixel else "",
            "ground_truth_v": round(float(gt_pixel[1]), 3) if gt_pixel else "",
            "centroid_error_px": round(float(pixel_error), 3) if pixel_error is not None else "",
            "confidence": round(float(detection_res.confidence), 4) if detection_res else 0.0,
            "snr_db": round(float(getattr(detection_res, "snr_db", 0.0)), 2) if detection_res else 0.0,
            "pat_mode": pat_state.mode.value if pat_state else "SEARCH",
            "latency_ms": round(latency_ms, 2),
            "fps": round(self._current_fps, 1),
        }
        self._video_log_records.append(rec)

        # 6. Render Viewports
        disp_clean = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR) if frame.ndim == 2 else frame.copy()
        cv2.line(disp_clean, (320 - 15, 240), (320 + 15, 240), (180, 160, 100), 1)
        cv2.line(disp_clean, (320, 240 - 15), (320, 240 + 15), (180, 160, 100), 1)
        if gt_pixel:
            cv2.circle(disp_clean, (int(gt_pixel[0]), int(gt_pixel[1])), 8, (0, 255, 0), 1)
            cv2.putText(disp_clean, "GT", (int(gt_pixel[0]) + 10, int(gt_pixel[1]) - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1)
            self._lbl_pos.setText(f"u: {gt_pixel[0]:.1f} | v: {gt_pixel[1]:.1f} px")
            self._lbl_cam_pixel.setText(f"u: {gt_pixel[0]:.2f} | v: {gt_pixel[1]:.2f} px")
            self._lbl_fov_status.setText("INSIDE FOV")
            self._lbl_fov_status.setStyleSheet(f"font-family: {FONT_TELEMETRY}; color: {COLOR_CONFIRM_GREEN}; font-weight: bold;")
        else:
            self._lbl_pos.setText("N/A (External Video)")
            self._lbl_cam_pixel.setText("u: N/A | v: N/A px")
            self._lbl_fov_status.setText("UNKNOWN")
            self._lbl_fov_status.setStyleSheet(f"font-family: {FONT_TELEMETRY}; color: {COLOR_TEXT_SECONDARY};")

        self._render_opencv_to_label(disp_clean, self._clean_cam_label)

        annotated_frame = frame.copy()
        annotated_frame = draw_tracking_annotations(
            frame=annotated_frame,
            estimate=estimate,
            ground_truth_pos=gt_pixel,
            measurement_pos=meas_pixel,
            detection_result=detection_res,
        )
        self._render_opencv_to_label(annotated_frame, self._dist_cam_label)

        # Telemetry readouts
        if pat_state is not None:
            self._lbl_pat_mode.setText(pat_state.mode.value)
            self._lbl_pat_quality.setText(f"{pat_state.track_quality * 100.0:.1f}%")
            self._lbl_pat_error.setText(f"Pan: {pat_state.pan_error_deg:+.2f}° | Tilt: {pat_state.tilt_error_deg:+.2f}°")
        else:
            self._lbl_pat_mode.setText("SEARCH")

        if detection_res is not None:
            self._lbl_perc_lock.setText("LOCKED" if detection_res.detected else "SEARCHING")
            self._lbl_perc_lock.setStyleSheet(f"font-family: {FONT_TELEMETRY}; color: {COLOR_CONFIRM_GREEN if detection_res.detected else COLOR_LOST_RED}; font-weight: bold;")
            if meas_pixel:
                self._lbl_perc_centroid.setText(f"u: {meas_pixel[0]:.2f} | v: {meas_pixel[1]:.2f} px")
            else:
                self._lbl_perc_centroid.setText("u: N/A | v: N/A px")
            self._lbl_perc_conf.setText(f"{detection_res.confidence * 100.0:.1f}%")
            self._lbl_perc_latency.setText(f"{detection_res.processing_time_ms:.1f} ms")

        # Status update
        total_latency = (time.perf_counter() - step_start_t) * 1000.0
        fps_display = self._current_fps if self._current_fps > 0 else packet.source_fps
        self._lbl_status.setText(f"External Video: Frame {frame_idx}/{self._external_video.frame_count} | {fps_display:.1f} FPS | Latency: {total_latency:.1f} ms")
        self._update_source_info_display()

    def _on_export_centroid_csv_clicked(self) -> None:
        """Export frame-by-frame centroid tracking and error log to CSV."""
        if not self._video_log_records:
            QMessageBox.information(
                self,
                "No Video Log Data",
                "No video tracking data available to export.\n\n"
                "Please select 'EXTERNAL_VIDEO', load a test MP4 video, and run playback first.",
            )
            return

        default_name = "isro_centroid_tracking_log.csv"
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Centroid Tracking Log (ISRO Evaluation-2)",
            default_name,
            "CSV Files (*.csv);;All Files (*.*)",
        )
        if not file_path:
            return

        try:
            fieldnames = [
                "frame_idx",
                "timestamp_s",
                "detected",
                "centroid_u",
                "centroid_v",
                "estimated_u",
                "estimated_v",
                "estimated_vx",
                "estimated_vy",
                "ground_truth_u",
                "ground_truth_v",
                "centroid_error_px",
                "confidence",
                "snr_db",
                "pat_mode",
                "latency_ms",
                "fps",
            ]
            with open(file_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(self._video_log_records)

            # Compute summary stats if errors are present
            valid_errors = [float(r["centroid_error_px"]) for r in self._video_log_records if r["centroid_error_px"] != ""]
            stats_msg = f"Successfully exported {len(self._video_log_records)} frame records to:\n{file_path}\n"
            if valid_errors:
                rmse = math.sqrt(sum(e**2 for e in valid_errors) / len(valid_errors))
                mean_err = sum(valid_errors) / len(valid_errors)
                max_err = max(valid_errors)
                stats_msg += f"\nTracking Accuracy Summary:\n• Mean Centroid Error: {mean_err:.3f} px\n• RMSE Error: {rmse:.3f} px\n• Peak Error: {max_err:.3f} px"

            QMessageBox.information(self, "Centroid Log Exported", stats_msg)
        except Exception as ex:
            QMessageBox.critical(self, "Export Failed", f"Failed to export centroid CSV:\n{str(ex)}")

    def apply_mission_config(self, config: AppConfig) -> None:
        """Apply resolved mission config from Mission Screen and initialize simulation."""
        self._sim_timer.stop()
        self._is_paused = True
        self._btn_play.setText("▶ Resume")
        self._lbl_status.setText(f"Status: Loaded Mission [{config.trajectory.type.upper()}]")

        self._config = config

        # Block signals during widget sync to prevent redundant resets
        self._combo_traj.blockSignals(True)
        self._combo_preset.blockSignals(True)
        self._spin_seed.blockSignals(True)
        self._spin_duration.blockSignals(True)

        preset_name = getattr(config.disturbance, "preset", None) or getattr(config, "preset", None)
        if not preset_name and config.disturbance is not None:
            if not getattr(config.disturbance, "enabled", False):
                preset_name = "NOMINAL"
            elif getattr(config.disturbance, "atmosphere", None) and config.disturbance.atmosphere.condition == "haze":
                preset_name = "DIFFICULT"
            elif getattr(config.disturbance, "atmosphere", None) and config.disturbance.atmosphere.condition == "fog":
                preset_name = "SEVERE"
            elif getattr(config.disturbance, "atmosphere", None) and config.disturbance.atmosphere.condition == "low_light":
                preset_name = "RECOVERY"
            elif getattr(config.disturbance, "atmosphere", None) and config.disturbance.atmosphere.condition == "rain":
                preset_name = "ADVERSARIAL"
            elif getattr(config.disturbance, "gaussian", None) and config.disturbance.gaussian.sigma >= 19.0:
                preset_name = "ADVERSARIAL"
            else:
                preset_name = "NOMINAL"

        preset_str = preset_name if preset_name else "CUSTOM"

        try:
            traj_type = config.trajectory.type
            idx = self._combo_traj.findText(traj_type)
            if idx >= 0:
                self._combo_traj.setCurrentIndex(idx)

            if preset_name:
                idx_preset = self._combo_preset.findText(preset_name)
                if idx_preset >= 0:
                    self._combo_preset.setCurrentIndex(idx_preset)

            if config.simulation.seed is not None:
                self._spin_seed.setValue(config.simulation.seed)
            if config.simulation.duration_seconds is not None:
                self._spin_duration.setValue(config.simulation.duration_seconds)

            if config.target is not None:
                self._spin_beacon_size.blockSignals(True)
                self._combo_beacon_shape.blockSignals(True)
                try:
                    if hasattr(config.target, "size_px") and config.target.size_px is not None:
                        self._spin_beacon_size.setValue(max(5, min(20, int(config.target.size_px))))
                    if getattr(config.target, "psf_model", "box") == "gaussian":
                        self._combo_beacon_shape.setCurrentText("Circular (Gaussian)")
                    else:
                        self._combo_beacon_shape.setCurrentText("Square (Box)")
                finally:
                    self._spin_beacon_size.blockSignals(False)
                    self._combo_beacon_shape.blockSignals(False)
        finally:
            self._combo_traj.blockSignals(False)
            self._combo_preset.blockSignals(False)
            self._spin_seed.blockSignals(False)
            self._spin_duration.blockSignals(False)

        # Initialize real engine and controllers
        self._engine = SimulationEngine(self._config)
        self._engine.initialize()
        self._track.reset()
        self._pat_mgr = PATModeManager()
        _ctrl_str_m = self._combo_controller.currentText()
        _c_type_m = "ADRC" if _ctrl_str_m == "ADRC_NONLINEAR" else ("LQG" if _ctrl_str_m == "LQG" else "PID")
        self._pat_ctrl = PATCameraController(controller_type=_c_type_m)
        self._last_estimate = None
        self._last_pat_mode = PATMode.SEARCH
        self._search_start_time = 0.0

        self.event_timeline.clear_events()
        self.event_timeline.add_event(
            0.0,
            "SEARCH",
            f"Mission launched: {config.trajectory.type.upper()} ({preset_str})",
        )
        self._update_ui_displays()

    # --------------------------------------------------------------------------
    # Simulation Tick Execution
    # --------------------------------------------------------------------------
    def _on_sim_step(self) -> None:
        if self._input_source == "EXTERNAL_VIDEO":
            self._execute_video_step(time.perf_counter())
            return

        if not self._engine.is_running:
            self._sim_timer.stop()
            self._is_paused = True
            self._btn_play.setText("▶ Resume")
            self._lbl_status.setText("Status: Simulation Complete")
            return
        self._execute_sim_step()

    def _execute_sim_step(self) -> None:
        step_start_t = time.perf_counter()

        # FPS Tracking
        self._frame_count += 1
        now = time.time()
        dt_fps = now - self._last_fps_calc_time
        if dt_fps >= 1.0:
            self._current_fps = self._frame_count / dt_fps
            self._frame_count = 0
            self._last_fps_calc_time = now

        # 1. Advance simulation step (steps target trajectory AND camera gimbal to t_k)
        self._engine.step()

        state = self._engine.get_current_state()
        dist_cam_frame = self._engine.get_disturbed_frame()
        camera = self._engine.camera

        # 1. Perception Detection & Kalman Filter Estimation Step
        # Only provide estimator prediction to perception once track is firmly established
        # in TRACK or DEGRADED mode with age > 2, so uninitialized / zero-velocity states
        # do not falsely reject the true optical beacon during initial search and acquisition.
        if (
            self._last_estimate
            and self._last_estimate.track_age > 2
            and self._pat_mgr.state.mode in (PATMode.TRACK, PATMode.DEGRADED)
        ):
            est_pred = (self._last_estimate.predicted_x, self._last_estimate.predicted_y)
            est_cov = self._last_estimate.covariance[:2, :2] if hasattr(self._last_estimate, "covariance") else None
            vel_hint = math.hypot(self._last_estimate.estimated_vx, self._last_estimate.estimated_vy)
        else:
            est_pred = None
            est_cov = None
            vel_hint = 0.0

        if camera.is_new_observation:
            detection_res = self._detector.detect(
                dist_cam_frame,
                timestamp=state.timestamp,
                collect_diagnostics=True,
                estimator_prediction=est_pred,
                prediction_covariance=est_cov,
                velocity_hint_px_s=vel_hint,
            )
            is_measurement_accepted = (
                detection_res.detected
                and not self._suppress_detection_test
            )
            meas = detection_res.centroid if is_measurement_accepted else None
            conf = detection_res.confidence if is_measurement_accepted else 0.0
            estimate = self._track.step(
                measurement=meas,
                confidence=conf,
                timestamp=state.timestamp,
                gimbal_pan_rate=camera.gimbal.actual_pan_rate,
                gimbal_tilt_rate=camera.gimbal.actual_tilt_rate,
                is_sensor_step=True,
            )
        else:
            detection_res = self._last_detection if hasattr(self, "_last_detection") and self._last_detection is not None else DetectionResult(
                detected=False, centroid=None, bbox=None, confidence=0.0, processing_time_ms=0.0, candidate_count=0, method_used="none", timestamp=state.timestamp
            )
            is_measurement_accepted = False
            estimate = self._track.step(
                measurement=None,
                confidence=0.0,
                timestamp=state.timestamp,
                gimbal_pan_rate=camera.gimbal.actual_pan_rate,
                gimbal_tilt_rate=camera.gimbal.actual_tilt_rate,
                is_sensor_step=False,
            )
        self._last_detection = detection_res
        self._last_estimate = estimate

        # 3. PAT State Machine & Control Loop
        dt_step = 1.0 / self._config.simulation.frequency_hz
        cov_trace = float(estimate.position_uncertainty**2)
        _current_mode = self._pat_mgr.state.mode
        if _current_mode == PATMode.SEARCH:
            search_pan_r, search_tilt_r = self._pat_mgr.search_manager.get_command(
                dt_step, camera.gimbal.pan_deg, camera.gimbal.tilt_deg
            )
        else:
            search_pan_r, search_tilt_r = 0.0, 0.0

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
            is_new_frame=camera.is_new_observation,
        )

        # 4. Compute control command & set rate on camera.gimbal
        # Use reacquire rate commands computed directly by mode_manager.process_step (no double-stepping)
        cmd_pan_rate, cmd_tilt_rate, _, _, _, _, _ = self._pat_ctrl.compute_control_command(
            dt=dt_step,
            pat_state=pat_state,
            search_pan_rate=search_pan_r,
            search_tilt_rate=search_tilt_r,
            reacquire_pan_rate=pat_state.reacquire_pan_rate,
            reacquire_tilt_rate=pat_state.reacquire_tilt_rate,
            estimated_vx_px_s=estimate.estimated_vx,
            estimated_vy_px_s=estimate.estimated_vy,
            gimbal=camera.gimbal,
        )

        # Wire gimbal rate command explicitly so camera physically tracks
        camera.gimbal.set_rate_command(cmd_pan_rate, cmd_tilt_rate)

        # Log timeline transitions
        if pat_state.mode != self._last_pat_mode:
            ev_type = pat_state.mode.value
            if pat_state.mode == PATMode.TRACK and self._last_pat_mode == PATMode.REACQUIRE:
                ev_type = "TRACK RESTORED"
            elif pat_state.mode == PATMode.ACQUIRE and detection_res.detected:
                self.event_timeline.add_event(state.timestamp, "CANDIDATE FOUND", "Optical beacon detected in sensor FOV")

            self.event_timeline.add_event(
                state.timestamp,
                ev_type,
                f"PAT state transition: {self._last_pat_mode.value if self._last_pat_mode else 'NONE'} → {pat_state.mode.value} ({pat_state.transition_reason})",
            )
            self._last_pat_mode = pat_state.mode

        latency_ms = (time.perf_counter() - step_start_t) * 1000.0

        # Ground truth projection strictly at CURRENT timestamp t_k using camera pose at t_k
        if camera is not None and state is not None:
            _, _, u_true, v_true, in_fov = camera.project_target(state.x, state.y)
            gt_pos = (u_true, v_true) if in_fov else None
        else:
            gt_pos = None

        self.track_data_ready.emit(
            dist_cam_frame,
            detection_res,
            estimate,
            pat_state,
            gt_pos,
            state.timestamp if state is not None else 0.0,
        )

        # Update Displays & Readouts for current frame at t_k (zero 1-frame lag)
        self._update_ui_displays(
            pat_state=pat_state,
            detection_res=detection_res,
            estimate=estimate,
            cmd_pan_rate=cmd_pan_rate,
            cmd_tilt_rate=cmd_tilt_rate,
            latency_ms=latency_ms,
        )


    # --------------------------------------------------------------------------
    # Real Telemetry & Frame Display Updates
    # --------------------------------------------------------------------------
    def _update_ui_displays(
        self,
        pat_state: Optional[PATState] = None,
        detection_res: Optional[DetectionResult] = None,
        estimate: Optional[StateEstimate] = None,
        cmd_pan_rate: float = 0.0,
        cmd_tilt_rate: float = 0.0,
        latency_ms: float = 0.0,
    ) -> None:
        state = self._engine.get_current_state() if self._engine else None
        world_frame = self._engine.get_current_frame() if self._engine else None
        clean_frame = self._engine.get_clean_frame() if self._engine else None
        dist_frame = self._engine.get_disturbed_frame() if self._engine else None
        camera = self._engine.camera if self._engine else None
        self._update_source_info_display()

        # 1. Update Clean Frame Viewport (Pure Uncorrupted Camera Observation)
        if clean_frame is not None:
            disp_clean = cv2.cvtColor(clean_frame, cv2.COLOR_GRAY2BGR) if clean_frame.ndim == 2 else clean_frame.copy()
            cx_i, cy_i = int(camera.intrinsics.cx) if camera else 320, int(camera.intrinsics.cy) if camera else 240
            cv2.line(disp_clean, (cx_i - 15, cy_i), (cx_i + 15, cy_i), (180, 160, 100), 1)
            cv2.line(disp_clean, (cx_i, cy_i - 15), (cx_i, cy_i + 15), (180, 160, 100), 1)
            self._render_opencv_to_label(disp_clean, self._clean_cam_label)

        # 2. Update Perception Tracking Feed Viewport
        if dist_frame is not None and camera is not None and state is not None:
            annotated_frame = dist_frame.copy()
            _, _, u_true, v_true, in_fov = camera.project_target(state.x, state.y)
            gt_pixel = (u_true, v_true) if in_fov else None
            meas_pixel = detection_res.centroid if (detection_res and detection_res.detected) else None

            annotated_frame = draw_tracking_annotations(
                frame=annotated_frame,
                estimate=estimate,
                ground_truth_pos=gt_pixel,
                measurement_pos=meas_pixel,
                detection_result=detection_res,
            )
            self._render_opencv_to_label(annotated_frame, self._dist_cam_label)

        # 3. Update Macro World Overview
        if world_frame is not None:
            boresight = camera.get_boresight_world_pos() if camera else (1000.0, 1000.0)
            target_pos = (state.x, state.y) if state else None
            path_history = self._engine._path_history if self._engine else []
            self.world_panel.update_world_display(
                world_frame=world_frame,
                target_pos=target_pos,
                boresight_pos=boresight,
                path_history=path_history,
                pat_state=pat_state,
            )

        # 4. Update Telemetry Readout Panels
        in_fov = False
        u_true, v_true = 0.0, 0.0
        if state is not None and camera is not None:
            _, _, u_true, v_true, in_fov = camera.project_target(state.x, state.y)
            self._lbl_time.setText(f"{state.timestamp:.3f} s")
            self._lbl_frame.setText(str(self._engine.clock.current_frame if self._engine else 0))
            self._lbl_pos.setText(f"X: {state.x:.2f} | Y: {state.y:.2f} px")
            self._lbl_vel.setText(f"Vx: {state.vx:+.2f} | Vy: {state.vy:+.2f} px/s")
            self._lbl_cam_pixel.setText(f"u: {u_true:+.2f} | v: {v_true:+.2f} px")
            self._lbl_fov_status.setText("INSIDE FOV" if in_fov else "OUTSIDE FOV")
            self._lbl_fov_status.setStyleSheet(f"font-family: {FONT_TELEMETRY}; color: {COLOR_CONFIRM_GREEN if in_fov else COLOR_LOST_RED}; font-weight: bold;")

        if pat_state is not None:
            self._lbl_pat_mode.setText(pat_state.mode.value)
            self._lbl_pat_quality.setText(f"{pat_state.track_quality * 100.0:.1f}%")
            self._lbl_pat_error.setText(f"Pan: {pat_state.pan_error_deg:+.2f}° | Tilt: {pat_state.tilt_error_deg:+.2f}°")
            self._lbl_pat_cmd_rate.setText(f"Pan: {cmd_pan_rate:+.2f}°/s | Tilt: {cmd_tilt_rate:+.2f}°/s")
            if camera:
                self._lbl_pat_act_rate.setText(f"Pan: {camera.gimbal.actual_pan_rate:+.2f}°/s | Tilt: {camera.gimbal.actual_tilt_rate:+.2f}°/s")
            self._lbl_pat_sat.setText("YES" if pat_state.is_saturated else "NO")

        if estimate is not None:
            self._lbl_est_status.setText(estimate.filter_status.value)
            self._lbl_est_pos.setText(f"u: {estimate.estimated_x:.2f} | v: {estimate.estimated_y:.2f} px")
            self._lbl_est_vel.setText(f"Vu: {estimate.estimated_vx:+.2f} | Vv: {estimate.estimated_vy:+.2f} px/s")
            self._lbl_est_unc.setText(f"pos: ±{estimate.position_uncertainty:.2f} px | vel: ±{estimate.velocity_uncertainty:.2f} px/s")
            inno_norm = float(np.linalg.norm(estimate.innovation)) if estimate.innovation is not None else 0.0
            self._lbl_est_inno.setText(f"||y||: {inno_norm:.2f} px | d²: {estimate.mahalanobis_distance**2:.2f}")
            self._lbl_est_latency.setText(f"{estimate.processing_time_ms:.1f} ms")

        if detection_res is not None:
            # Physically truthful lock state
            if not in_fov:
                self._lbl_perc_lock.setText("LOST (OUT OF FOV)")
                self._lbl_perc_lock.setStyleSheet(f"font-family: {FONT_TELEMETRY}; color: {COLOR_LOST_RED}; font-weight: bold;")
            elif pat_state is not None:
                if pat_state.mode == PATMode.TRACK:
                    self._lbl_perc_lock.setText("LOCKED")
                    self._lbl_perc_lock.setStyleSheet(f"font-family: {FONT_TELEMETRY}; color: {COLOR_CONFIRM_GREEN}; font-weight: bold;")
                elif pat_state.mode == PATMode.ACQUIRE:
                    self._lbl_perc_lock.setText("ACQUIRING")
                    self._lbl_perc_lock.setStyleSheet(f"font-family: {FONT_TELEMETRY}; color: {COLOR_DISTURBANCE_AMBER}; font-weight: bold;")
                elif pat_state.mode in (PATMode.DEGRADED, PATMode.REACQUIRE):
                    self._lbl_perc_lock.setText(pat_state.mode.value)
                    self._lbl_perc_lock.setStyleSheet(f"font-family: {FONT_TELEMETRY}; color: {COLOR_DISTURBANCE_AMBER}; font-weight: bold;")
                else:
                    self._lbl_perc_lock.setText("SEARCHING")
                    self._lbl_perc_lock.setStyleSheet(f"font-family: {FONT_TELEMETRY}; color: {COLOR_LOST_RED}; font-weight: bold;")
            else:
                self._lbl_perc_lock.setText("LOCKED" if detection_res.detected else "SEARCHING")
                self._lbl_perc_lock.setStyleSheet(f"font-family: {FONT_TELEMETRY}; color: {COLOR_CONFIRM_GREEN if detection_res.detected else COLOR_LOST_RED}; font-weight: bold;")

            if detection_res.centroid:
                u, v = detection_res.centroid
                self._lbl_perc_centroid.setText(f"u: {u:.2f} | v: {v:.2f} px")
            else:
                self._lbl_perc_centroid.setText("u: N/A | v: N/A px")

            # Dynamic Ground-Truth Subpixel Error (diagnostic evaluation only)
            if not in_fov:
                self._lbl_perc_error.setText("N/A (OUTSIDE FOV)")
            elif detection_res.detected and detection_res.centroid:
                subpix_err = math.hypot(detection_res.centroid[0] - u_true, detection_res.centroid[1] - v_true)
                self._lbl_perc_error.setText(f"{subpix_err:.3f} px")
            else:
                self._lbl_perc_error.setText("N/A (NO DETECTION)")

            self._lbl_perc_conf.setText(f"{detection_res.confidence * 100.0:.1f}%")
            self._lbl_perc_latency.setText(f"{detection_res.processing_time_ms:.1f} ms ({self._current_fps:.1f} FPS)")

        # Update Disturbance telemetry labels from engine telemetry object
        telem = self._engine.last_disturbance_telemetry if self._engine else None
        if telem and telem.disturbance_enabled:
            self._lbl_dt_status.setText("ACTIVE")
            self._lbl_dt_status.setStyleSheet(f"font-family: {FONT_TELEMETRY}; color: {COLOR_DISTURBANCE_AMBER}; font-weight: bold;")
            self._lbl_sp.setText(f"{telem.salt_pepper_probability * 100.0:.1f}%" if telem.salt_pepper_enabled else "OFF")
            self._lbl_gauss.setText(f"σ = {telem.gaussian_sigma:.1f} px" if telem.gaussian_enabled else "OFF")
            self._lbl_poisson.setText(f"ON (peak={telem.poisson_parameter:.0f})" if telem.poisson_enabled else "OFF")
            self._lbl_jitter.setText(f"dx: {telem.camera_jitter_x:+.1f} | dy: {telem.camera_jitter_y:+.1f} px" if telem.camera_jitter_enabled else "OFF")
            self._lbl_platform.setText(f"ox: {telem.platform_offset_x:+.1f} | oy: {telem.platform_offset_y:+.1f} px" if telem.platform_motion_enabled else "OFF")
            self._lbl_atmos.setText(f"{telem.atmosphere_condition.upper()} (c={telem.contrast_factor:.2f})")
        else:
            self._lbl_dt_status.setText("NOMINAL")
            self._lbl_dt_status.setStyleSheet(f"font-family: {FONT_TELEMETRY}; color: {COLOR_TEXT_SECONDARY}; font-weight: bold;")
            self._lbl_sp.setText("OFF")
            self._lbl_gauss.setText("OFF")
            self._lbl_poisson.setText("OFF")
            self._lbl_jitter.setText("OFF")
            self._lbl_platform.setText("OFF")
            self._lbl_atmos.setText("CLEAR")

    def _render_opencv_to_label(self, frame_bgr: np.ndarray, label: QLabel) -> None:
        """Render BGR or Grayscale numpy image array into PySide6 QLabel pixmap.
        Uses FastTransformation to keep real-time rendering smooth and lag-free.
        """
        if len(frame_bgr.shape) == 2:
            h, w = frame_bgr.shape
            # Ensure contiguous memory for QImage
            contiguous = np.ascontiguousarray(frame_bgr)
            qimg = QImage(contiguous.data, w, h, w, QImage.Format_Grayscale8)
        else:
            h, w, ch = frame_bgr.shape
            rgb_frame = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
            contiguous = np.ascontiguousarray(rgb_frame)
            qimg = QImage(contiguous.data, w, h, ch * w, QImage.Format_RGB888)
        pix = QPixmap.fromImage(qimg)
        # FastTransformation avoids bilinear interpolation overhead for live feeds
        scaled_pix = pix.scaled(label.size(), Qt.KeepAspectRatio, Qt.FastTransformation)
        label.setPixmap(scaled_pix)

    # --------------------------------------------------------------------------
    # Exports & Snapshots
    # --------------------------------------------------------------------------
    def _save_clean_snapshot(self) -> None:
        if self._engine:
            clean_frame = self._engine.get_clean_frame()
            out_p = Path("clean_frame.png").resolve()
            cv2.imwrite(str(out_p), clean_frame)
            self._lbl_status.setText(f"Saved: {out_p.name}")

    def _save_disturbed_snapshot(self) -> None:
        if self._engine:
            dist_frame = self._engine.get_disturbed_frame()
            out_p = Path("disturbed_frame.png").resolve()
            cv2.imwrite(str(out_p), dist_frame)
            self._lbl_status.setText(f"Saved: {out_p.name}")

    def _export_data(self) -> None:
        if self._engine:
            out_p = Path("ground_truth.csv").resolve()
            self._engine.export_ground_truth_csv(str(out_p))
            self._lbl_status.setText(f"Exported: {out_p.name}")

    def _generate_engineering_report(self) -> None:
        try:
            from analysis.report_generator import EngineeringReportGenerator
            out_path = Path("AUTOMATED_ENGINEERING_REPORT.md").resolve()
            generator = EngineeringReportGenerator()
            generator.generate_report(str(out_path))

            QMessageBox.information(
                self,
                "Report Export Successful",
                f"Statistical Engineering Validation Report exported successfully!\n\nPath: {out_path}",
            )
            self._lbl_status.setText(f"Exported: {out_path.name}")
        except Exception as e:
            QMessageBox.critical(self, "Export Failed", f"Could not generate report: {e}")
