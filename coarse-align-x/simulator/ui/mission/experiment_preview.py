"""HORIZON Phase 11.3 Experiment Preview Component
===================================================
Static (non-running) preview rendering mini 2000x2000 world map,
predicted target trajectory path, initial target position, and camera FOV footprint.
Purely static visualization generated from resolved AppConfig — does not execute simulation.
"""

from __future__ import annotations
from typing import Optional, List, Tuple
import math
import numpy as np
import matplotlib
matplotlib.use("Agg")
from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg
import matplotlib.patches as patches

from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from simulator.ui.foundation.tokens import (
    COLOR_FIELD,
    COLOR_HAIRLINE_BORDER_HEX,
    COLOR_LOCK_CYAN,
    COLOR_TEXT_PRIMARY,
    COLOR_TEXT_SECONDARY,
    COLOR_VOID,
    FONT_BODY,
    SPACING_8,
    SPACING_12,
)
from simulator.ui.foundation.primitives import PanelSurface, PanelVariant, SectionHeaderLabel
from simulator.core.config import AppConfig
from simulator.ui.mission.scenario_data import ScenarioDefinition, get_default_scenarios


class ExperimentPreviewWidget(PanelSurface):
    """Scientific Pre-Flight Spatial Trajectory & Optical Channel Corridor Preview."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(PanelVariant.FIELD, parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(SPACING_12, SPACING_12, SPACING_12, SPACING_12)
        layout.setSpacing(SPACING_8)

        # Header Title: "Pre-Flight Flight Geometry & Link Corridor"
        header = SectionHeaderLabel("Pre-Flight Flight Geometry & Optical Corridor", self)
        header.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY}; font-family: {FONT_BODY}; font-size: 13px; font-weight: 600;")
        layout.addWidget(header)

        self.canvas_label = QLabel(self)
        self.canvas_label.setMinimumSize(320, 280)
        self.canvas_label.setFixedHeight(305)
        self.canvas_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.canvas_label.setStyleSheet(
            f"background-color: {COLOR_VOID}; border: 1px solid {COLOR_HAIRLINE_BORDER_HEX}; border-radius: 4px;"
        )
        layout.addWidget(self.canvas_label)

        self._current_pixmap: Optional[QPixmap] = None

        # Auto-initialize with default scenario so display is NEVER blank on launch
        scens = get_default_scenarios()
        if scens:
            self.update_preview(scens[0], scens[0].config)

    def update_preview(self, scenario: ScenarioDefinition, config: AppConfig) -> None:
        """Render high-resolution scientific preview showing FPA sensor corridor and link elevation pass."""
        fig = Figure(figsize=(5.2, 3.6), facecolor="#0E1117", dpi=100)
        fig.subplots_adjust(left=0.13, right=0.87, top=0.90, bottom=0.16, hspace=0.50)

        gs = fig.add_gridspec(2, 1, height_ratios=[1.35, 1.0])
        ax_corridor = fig.add_subplot(gs[0, 0], facecolor="#0E1117")
        ax_pass = fig.add_subplot(gs[1, 0], facecolor="#0E1117")

        for ax in (ax_corridor, ax_pass):
            ax.tick_params(colors="#8A94A0", labelsize=8.0, pad=2)
            for spine in ax.spines.values():
                spine.set_color("#282E38")
                spine.set_linewidth(0.8)
            ax.grid(True, linestyle=":", color="#20242E", alpha=0.6, linewidth=0.7)

        # ----------------------------------------------------------------------
        # Subplot 1: Sensor Focal Plane Entry Corridor & Boresight Reticle
        # ----------------------------------------------------------------------
        traj_name = config.trajectory.type.capitalize()
        ax_corridor.set_title(
            f"FPA Sensor Entry Corridor  |  {scenario.mission_code} ({traj_name})  |  Range: {scenario.slant_range_km:.0f}km",
            color="#C9D1D9", fontsize=8.5, fontweight="bold", loc="left", pad=4,
        )

        pts = scenario.generate_preview_path(num_points=100, traj_type=config.trajectory.type)
        if pts and len(pts) > 1:
            x_pts = [p[0] for p in pts]
            y_pts = [p[1] for p in pts]
            ax_corridor.plot(x_pts, y_pts, color="#5B86AD", lw=1.5, label="Target Track")

            # Initial entry marker
            ax_corridor.plot([x_pts[0]], [y_pts[0]], marker="o", markersize=5, color="#4E8062", markeredgecolor="#F0F6FC")

            # Entry direction arrow
            dx = x_pts[min(5, len(x_pts)-1)] - x_pts[0]
            dy = y_pts[min(5, len(y_pts)-1)] - y_pts[0]
            mag = math.hypot(dx, dy)
            if mag > 1e-3:
                ax_corridor.arrow(x_pts[0], y_pts[0], dx/mag * 120, dy/mag * 120, head_width=45, head_length=45, fc="#4E8062", ec="#4E8062", alpha=0.85)

            # 3-sigma Initial Acquisition Uncertainty Ellipse
            unc_ellipse = patches.Ellipse((x_pts[0], y_pts[0]), width=180.0, height=120.0, angle=25.0, edgecolor="#A8824A", facecolor="none", linestyle="--", lw=1.0, alpha=0.8)
            ax_corridor.add_patch(unc_ellipse)

        # Center Boresight & Sensor FOV Footprint (640x480)
        bx, by = 1000.0, 1000.0
        fov_rect = patches.Rectangle((bx - 320, by - 240), 640, 480, edgecolor="#36506E", facecolor="#1F2D3D", alpha=0.15, linestyle="-", lw=1.2)
        ax_corridor.add_patch(fov_rect)
        ax_corridor.axhline(by, color="#484F58", linestyle=":", lw=0.9)
        ax_corridor.axvline(bx, color="#484F58", linestyle=":", lw=0.9)

        # FSM Capture Basin
        fsm_circle = patches.Circle((bx, by), 35.0, edgecolor="#4E8062", facecolor="none", linestyle="--", lw=1.1)
        ax_corridor.add_patch(fsm_circle)

        ax_corridor.set_xlim(300, 1700)
        ax_corridor.set_ylim(1700, 300)  # Inverted Y for optical sensor frame
        ax_corridor.set_xlabel("Focal Plane Azimuth [px]", color="#8A94A0", fontsize=7.5, labelpad=1)
        ax_corridor.set_ylabel("Focal Plane Elevation [px]", color="#8A94A0", fontsize=7.5, labelpad=1)

        # ----------------------------------------------------------------------
        # Subplot 2: Optical Channel Transmission & Pass Elevation Profile
        # ----------------------------------------------------------------------
        t_arr = np.linspace(0, max(5.0, config.simulation.duration_seconds), 60)
        elev_deg = 15.0 + 65.0 * np.sin(np.pi * t_arr / max(1.0, config.simulation.duration_seconds))
        
        preset_name = (getattr(config, "mission_preset_name", None) or "").upper()
        if preset_name in ("SEVERE", "ADVERSARIAL"):
            tau_base = 0.28
        elif preset_name == "DIFFICULT":
            tau_base = 0.52
        elif preset_name == "RECOVERY":
            tau_base = 0.42
        elif not config.disturbance.enabled:
            tau_base = 0.90
        else:
            tau_base = 0.60
            
        tau_t = tau_base * np.sin(np.radians(np.clip(elev_deg, 10.0, 90.0))) ** 0.3

        ax_pass.set_title(
            f"Channel Transmission τ_atm & Elevation  |  {scenario.channel_model}",
            color="#C9D1D9", fontsize=8.5, fontweight="bold", loc="left", pad=4,
        )
        ax_pass.plot(t_arr, elev_deg, color="#5B86AD", lw=1.3, label="Elevation [°]")
        ax_pass.set_ylabel("Elevation [°]", color="#5B86AD", fontsize=7.5, labelpad=1)
        ax_pass.set_ylim(0, 90.0)
        ax_pass.set_xlabel("Pass Timeline [s]", color="#8A94A0", fontsize=7.5, labelpad=1)

        ax_tau = ax_pass.twinx()
        ax_tau.tick_params(colors="#5B8B95", labelsize=8.0, pad=2)
        for spine in ax_tau.spines.values():
            spine.set_color("#282E38")
        ax_tau.plot(t_arr, tau_t * 100.0, color="#5B8B95", linestyle="--", lw=1.2, label="Transmission [%]")
        ax_tau.set_ylabel("τ_atm [%]", color="#5B8B95", fontsize=7.5, labelpad=1)
        ax_tau.set_ylim(0, 100.0)

        # Render Figure to QPixmap
        agg_canvas = FigureCanvasAgg(fig)
        agg_canvas.draw()
        rgba_buffer = agg_canvas.buffer_rgba()
        w, h = int(fig.get_size_inches()[0] * fig.dpi), int(fig.get_size_inches()[1] * fig.dpi)
        qimg = QImage(rgba_buffer, w, h, QImage.Format.Format_RGBA8888)
        self._current_pixmap = QPixmap.fromImage(qimg)

        lbl_size = self.canvas_label.size()
        target_size = lbl_size if (lbl_size.width() > 100 and lbl_size.height() > 100) else QSize(440, 275)
        scaled = self._current_pixmap.scaled(
            target_size,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.canvas_label.setPixmap(scaled)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if self._current_pixmap is not None:
            lbl_size = self.canvas_label.size()
            if lbl_size.width() > 50 and lbl_size.height() > 50:
                scaled = self._current_pixmap.scaled(
                    lbl_size,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
                self.canvas_label.setPixmap(scaled)
