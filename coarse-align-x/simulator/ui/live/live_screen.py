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
import math
from pathlib import Path
import sys
import time
from typing import Optional
import cv2
import numpy as np

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
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

        from simulator.core.config import TargetConfig, TargetInitialPosition
        self._config = AppConfig(
            target=TargetConfig(initial_position=TargetInitialPosition(x=1000.0, y=1000.0)),
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
        self._perception_mode = "SOTA_FOURIER_GMM"
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
        self._detector = self._sota_detector

        # Tracker & PAT Subsystems
        self._track = Track(track_id=1, filter_type="IMM_ADAPTIVE_EKF")
        self._pat_mgr = PATModeManager()
        self._pat_ctrl = PATCameraController(controller_type="ADRC")

        self._suppress_detection_test = False
        self._last_estimate: Optional[StateEstimate] = None
        self._last_pat_mode: Optional[PATMode] = PATMode.SEARCH
        self._search_start_time: float = 0.0
        self._frame_count: int = 0
        self._last_fps_calc_time: float = time.time()
        self._current_fps: float = 0.0
        self._is_paused = True

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

        # --- 5. Configuration & Presets Form Box ---
        cfg_box = QGroupBox("Configuration Presets", self)
        cfg_box.setStyleSheet(gb_style)
        cfg_form = QFormLayout(cfg_box)
        cfg_form.setSpacing(6)

        combo_style = f"QComboBox {{ background-color: {COLOR_VOID}; color: {COLOR_TEXT_PRIMARY}; border: 1px solid {COLOR_HAIRLINE_BORDER_HEX}; border-radius: 3px; padding: 4px; font-family: {FONT_BODY}; }}"

        self._combo_perc_mode = QComboBox(self)
        self._combo_perc_mode.addItems(["SOTA_FOURIER_GMM", "HYBRID", "NEURAL", "CLASSICAL"])
        self._combo_perc_mode.setStyleSheet(combo_style)
        self._combo_perc_mode.currentTextChanged.connect(self._on_perc_mode_changed)
        cfg_form.addRow("Perception Engine:", self._combo_perc_mode)

        self._combo_estimator = QComboBox(self)
        self._combo_estimator.addItems(["IMM_ADAPTIVE_EKF", "STANDARD_EKF"])
        self._combo_estimator.setStyleSheet(combo_style)
        self._combo_estimator.currentTextChanged.connect(self._on_estimator_changed)
        cfg_form.addRow("State Estimator:", self._combo_estimator)

        self._combo_controller = QComboBox(self)
        self._combo_controller.addItems(["ADRC_NONLINEAR", "PID"])
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
    def _on_perc_mode_changed(self, mode_str: str) -> None:
        self._perception_mode = mode_str
        if mode_str == "SOTA_FOURIER_GMM":
            self._detector = self._sota_detector
        elif mode_str == "NEURAL":
            self._detector = self._neural_detector
        elif mode_str == "HYBRID":
            self._detector = self._hybrid_detector
        else:
            self._detector = self._classical_detector
        self._lbl_status.setText(f"Perception Mode: {mode_str}")
        self._update_ui_displays()

    def _on_estimator_changed(self, est_str: str) -> None:
        self._track = Track(track_id=1, filter_type=est_str)
        self._lbl_status.setText(f"State Estimator: {est_str}")
        self._update_ui_displays()

    def _on_controller_changed(self, ctrl_str: str) -> None:
        c_type = "ADRC" if ctrl_str == "ADRC_NONLINEAR" else "PID"
        self._pat_ctrl.controller_type = c_type
        self._lbl_status.setText(f"Controller Mode: {ctrl_str}")
        self._update_ui_displays()

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
        self._update_ui_displays()

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
            self._is_paused = False
            self._btn_play.setText("⏸ Pause")
            self._lbl_status.setText("Status: Simulating & Tracking...")
            self._sim_timer.start()
        else:
            self._is_paused = True
            self._btn_play.setText("▶ Resume")
            self._lbl_status.setText("Status: Paused")
            self._sim_timer.stop()

    def _toggle_blackout_test(self, checked: bool) -> None:
        self._suppress_detection_test = checked
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
        self._lbl_status.setText("Status: Reset")

        from simulator.core.config import TargetConfig, TargetInitialPosition
        traj_name = self._combo_traj.currentText()
        new_config = AppConfig(
            world=self._config.world,
            camera=self._config.camera,
            target=TargetConfig(
                size_px=self._config.target.size_px,
                intensity=self._config.target.intensity,
                initial_position=TargetInitialPosition(x=1000.0, y=1000.0),
                psf_model=self._config.target.psf_model,
                psf_sigma_px=self._config.target.psf_sigma_px,
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
        self._track.reset()
        self._pat_mgr = PATModeManager()
        self._pat_ctrl = PATCameraController()
        self._last_estimate = None
        self._last_pat_mode = PATMode.SEARCH
        self._search_start_time = 0.0

        self.event_timeline.clear_events()
        self.event_timeline.add_event(0.0, "SEARCH", "System reset to initial SEARCH state")
        self._update_ui_displays()

    # --------------------------------------------------------------------------
    # Simulation Tick Execution
    # --------------------------------------------------------------------------
    def _on_sim_step(self) -> None:
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

        state = self._engine.get_current_state()
        dist_cam_frame = self._engine.get_disturbed_frame()
        camera = self._engine.camera

        # 1. Perception Detection on current disturbed frame
        detection_res = self._detector.detect(dist_cam_frame, timestamp=state.timestamp, collect_diagnostics=True)

        # 2. Kalman Filter Estimation Step
        estimate = self._track.step(
            measurement=detection_res.centroid if (detection_res.detected and not self._suppress_detection_test) else None,
            confidence=detection_res.confidence if not self._suppress_detection_test else 0.0,
            timestamp=state.timestamp,
            gimbal_pan_rate=camera.gimbal.actual_pan_rate,
            gimbal_tilt_rate=camera.gimbal.actual_tilt_rate,
        )
        self._last_estimate = estimate

        # 3. PAT State Machine & Control Loop
        dt_step = 1.0 / self._config.simulation.frequency_hz
        cov_trace = float(estimate.position_uncertainty**2)
        search_pan_r, search_tilt_r = self._pat_mgr.search_manager.get_command(
            dt_step, camera.gimbal.pan_deg, camera.gimbal.tilt_deg
        )
        reacq_pan_r, reacq_tilt_r, _ = self._pat_mgr.reacquisition_manager.process_step(
            dt_step, camera.gimbal.pan_deg, camera.gimbal.tilt_deg
        )

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

        # 4. Compute control command & set rate on camera.gimbal
        cmd_pan_rate, cmd_tilt_rate, _, _, _, _, _ = self._pat_ctrl.compute_control_command(
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

        # 5. Advance simulation step (steps target trajectory AND camera gimbal ONCE per dt)
        self._engine.step()

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

        # Emit live data signal so Track screen can update without a separate engine
        camera_state = self._engine.camera if self._engine else None
        if camera_state is not None and state is not None:
            _, _, u_true, v_true, in_fov = camera_state.project_target(state.x, state.y)
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

        # Update Displays & Readouts (skip heavy render if step ran over budget)
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
            self._lbl_perc_lock.setText("LOCKED" if detection_res.detected else "SEARCHING")
            self._lbl_perc_lock.setStyleSheet(f"font-family: {FONT_TELEMETRY}; color: {COLOR_CONFIRM_GREEN if detection_res.detected else COLOR_LOST_RED}; font-weight: bold;")
            if detection_res.centroid:
                u, v = detection_res.centroid
                self._lbl_perc_centroid.setText(f"u: {u:.2f} | v: {v:.2f} px")
            else:
                self._lbl_perc_centroid.setText("u: N/A | v: N/A px")

            if isinstance(detection_res.diagnostics, dict):
                subpix_err = detection_res.diagnostics.get("subpixel_error_gt", 0.0)
            else:
                subpix_err = getattr(detection_res.diagnostics, "subpixel_error_gt", 0.0)
            self._lbl_perc_error.setText(f"{subpix_err:.3f} px")
            self._lbl_perc_conf.setText(f"{detection_res.confidence * 100.0:.1f}%")
            self._lbl_perc_latency.setText(f"{detection_res.processing_time_ms:.1f} ms ({self._current_fps:.1f} FPS)")

        if state is not None and camera is not None:
            _, _, u_true, v_true, in_fov = camera.project_target(state.x, state.y)
            self._lbl_time.setText(f"{state.timestamp:.3f} s")
            self._lbl_frame.setText(str(self._engine.clock.current_frame if self._engine else 0))
            self._lbl_pos.setText(f"X: {state.x:.2f} | Y: {state.y:.2f} px")
            self._lbl_vel.setText(f"Vx: {state.vx:+.2f} | Vy: {state.vy:+.2f} px/s")
            self._lbl_cam_pixel.setText(f"u: {u_true:+.2f} | v: {v_true:+.2f} px")
            self._lbl_fov_status.setText("INSIDE FOV" if in_fov else "OUTSIDE FOV")
            self._lbl_fov_status.setStyleSheet(f"font-family: {FONT_TELEMETRY}; color: {COLOR_CONFIRM_GREEN if in_fov else COLOR_LOST_RED}; font-weight: bold;")

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
