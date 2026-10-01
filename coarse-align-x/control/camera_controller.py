"""
PAT Mode and Confidence-Aware Camera Controller with Predictive Pointing & Anti-Hunting Smoothing.
HORIZON — SIH 2026 PS SIH26169 (PDF Section 6.6)
"""

from __future__ import annotations

import math
from typing import Tuple, Dict, Any, Optional
import numpy as np

from pat.state import PATMode, PATState
from pat.thresholds import PATThresholds
from .pid import PIDController
from .feedforward import VelocityFeedForward, SCurveFeedForward
from .saturation import ControllerSaturation
from .actuator_interface import ActuatorInterface
from .gain_scheduler import GainScheduler, ScheduledGains
from .adrc_controller import DualAxisADRCController
from .smith_predictor import SmithPredictor
from .lqg_controller import LQGController


class PATCameraController:
    """
    Master closed-loop camera controller combining:
    1. Mode-dependent Gain Scheduling with Uncertainty-Aware scaling.
    2. Predictive Pointing & Kinematic Delay Compensation (Smith Predictor & Forward Extrapolation).
    3. Active Disturbance Rejection Control (ADRC), Linear PID, or Optimal LQG regulation.
    4. Angular velocity S-Curve feedforward anticipation.
    5. Anti-Hunting Command Smoothing filter to eliminate noise-induced jitter.
    6. Actuator slew-rate and acceleration saturation limits.
    """

    def __init__(
        self,
        thresholds: Optional[PATThresholds] = None,
        scheduler: Optional[GainScheduler] = None,
        controller_type: str = "PID",
        lead_time_s: float = 0.05,
        smoothing_factor: float = 0.85,
        max_rate_change_deg_s2: float = 800.0,
    ):
        self.thresholds = thresholds or PATThresholds()
        self.scheduler = scheduler or GainScheduler()
        self.controller_type = controller_type
        self.lead_time_s = float(lead_time_s)
        self.smoothing_factor = float(smoothing_factor)
        self.max_rate_change_deg_s2 = float(max_rate_change_deg_s2)

        # Base PID controllers with physical rate limits
        self.pan_pid = PIDController(kp=1.5, ki=0.08, kd=0.12, output_limit=self.thresholds.max_pan_rate_deg_s)
        self.tilt_pid = PIDController(kp=1.5, ki=0.08, kd=0.12, output_limit=self.thresholds.max_tilt_rate_deg_s)

        # Active Disturbance Rejection Controller (ADRC)
        self.adrc = DualAxisADRCController(
            max_pan_rate_deg_s=self.thresholds.max_pan_rate_deg_s,
            max_tilt_rate_deg_s=self.thresholds.max_tilt_rate_deg_s,
        )

        # Optimal LQG Controllers
        self.lqg_pan = LQGController()
        self.lqg_tilt = LQGController()

        # Smith Predictor Latency Compensator
        self.smith_predictor = SmithPredictor()

        # Feedforward Controllers
        self.feedforward = VelocityFeedForward(kff_pan=0.6, kff_tilt=0.6, enabled=True)
        self.scurve_ff = SCurveFeedForward(kff_pan=0.6, kff_tilt=0.6, max_accel_deg_s2=max_rate_change_deg_s2, max_jerk_deg_s3=4000.0, enabled=True)

        self.saturation = ControllerSaturation(
            max_pan_rate_deg_s=self.thresholds.max_pan_rate_deg_s,
            max_tilt_rate_deg_s=self.thresholds.max_tilt_rate_deg_s,
        )
        self.actuator_interface = ActuatorInterface()
        self.active_gains: ScheduledGains = self.scheduler.gains_inactive

        # Command smoothing state
        self._prev_cmd_pan = 0.0
        self._prev_cmd_tilt = 0.0
        # Effective acceleration limit is mode-adaptive:
        # In TRACK (steady-state): 800 deg/s² — firm smoothing prevents jitter chasing
        # In ACQUIRE/REACQUIRE: effectively unlimited — fast pull-in response required
        self._track_mode_rate_limit = float(max_rate_change_deg_s2)  # used only in TRACK

    def reset(self) -> None:
        self.pan_pid.reset()
        self.tilt_pid.reset()
        self.adrc.reset()
        self.smith_predictor.reset()
        self.scurve_ff.reset()
        self.active_gains = self.scheduler.gains_inactive
        self._prev_cmd_pan = 0.0
        self._prev_cmd_tilt = 0.0
        self._track_mode_rate_limit = self.max_rate_change_deg_s2

    def compute_control_command(
        self,
        dt: float,
        pat_state: PATState,
        search_pan_rate: float,
        search_tilt_rate: float,
        reacquire_pan_rate: float,
        reacquire_tilt_rate: float,
        estimated_vx_px_s: float = 0.0,
        estimated_vy_px_s: float = 0.0,
        estimated_omega_x_deg_s: Optional[float] = None,
        estimated_omega_y_deg_s: Optional[float] = None,
        gimbal: Optional[Any] = None,
        measured_latency_s: Optional[float] = None,
        platform_vx_px_s: float = 0.0,
        platform_vy_px_s: float = 0.0,
    ) -> Tuple[float, float, float, float, float, float, bool]:
        """
        Calculates commanded pan and tilt rates with dynamic predictive delay compensation,
        relative kinematic forward extrapolation, and command smoothing.

        Returns:
            Tuple[cmd_pan_rate, cmd_tilt_rate, pid_pan, pid_tilt, ff_pan, ff_tilt, is_saturated]
        """
        mode = pat_state.mode

        if mode == PATMode.SEARCH:
            cmd_pan = search_pan_rate
            cmd_tilt = search_tilt_rate
            pid_pan, pid_tilt = 0.0, 0.0
            ff_pan, ff_tilt = 0.0, 0.0
            self.reset()

        elif mode == PATMode.REACQUIRE:
            if reacquire_pan_rate != 0.0 or reacquire_tilt_rate != 0.0:
                cmd_pan = reacquire_pan_rate
                cmd_tilt = reacquire_tilt_rate
            else:
                # Inertial momentum coasting: decay last command smoothly by 0.95 to maintain target inside FOV
                cmd_pan = self._prev_cmd_pan * 0.95
                cmd_tilt = self._prev_cmd_tilt * 0.95
            pid_pan, pid_tilt = 0.0, 0.0
            ff_pan, ff_tilt = 0.0, 0.0
            self._prev_cmd_pan = cmd_pan
            self._prev_cmd_tilt = cmd_tilt

        elif mode in (PATMode.ACQUIRE, PATMode.TRACK, PATMode.DEGRADED):
            # 1. Compute scheduled gains tailored to current tracking regime and confidence
            gains = self.scheduler.get_gains(
                mode=mode,
                track_quality=pat_state.track_quality,
                continuous_interpolation=True,
            )
            self.active_gains = gains

            # 2. Determine target angular velocity using pinhole optics
            fx_px = (640.0 / 2.0) / math.tan(math.radians(4.0 / 2.0))
            fy_px = (480.0 / 2.0) / math.tan(math.radians(3.0 / 2.0))

            if estimated_omega_x_deg_s is not None:
                pan_vel_deg_s = float(estimated_omega_x_deg_s)
            else:
                pan_vel_deg_s = math.degrees(math.atan(estimated_vx_px_s / fx_px))

            if estimated_omega_y_deg_s is not None:
                tilt_vel_deg_s = float(estimated_omega_y_deg_s)
            else:
                tilt_vel_deg_s = math.degrees(math.atan(estimated_vy_px_s / fy_px))

            # Platform kinematic rate from onboard IMU telemetry
            plat_pan_vel_deg_s = math.degrees(math.atan(platform_vx_px_s / fx_px))
            plat_tilt_vel_deg_s = math.degrees(math.atan(platform_vy_px_s / fy_px))

            # 3. Closed-Loop Regulation (ADRC, LQG, or PID)
            act_pan_r = gimbal.actual_pan_rate if gimbal is not None else self._prev_cmd_pan
            act_tilt_r = gimbal.actual_tilt_rate if gimbal is not None else self._prev_cmd_tilt

            # 3. Calculate target angular velocity S-Curve feedforward & platform feedforward
            ff_quality = float(np.clip(pat_state.track_quality, 0.2, 1.0)) if not pat_state.prediction_only else 0.4
            self.scurve_ff.enabled = (gains.kff > 0.0)
            self.scurve_ff.kff_pan = gains.kff * ff_quality
            self.scurve_ff.kff_tilt = gains.kff * ff_quality
            ff_pan, ff_tilt = self.scurve_ff.compute(pan_vel_deg_s, tilt_vel_deg_s, dt=dt)
            k_plat_ff = 1.0 if mode in (PATMode.TRACK, PATMode.ACQUIRE, PATMode.DEGRADED) else 0.0
            plat_ff_pan = k_plat_ff * plat_pan_vel_deg_s
            plat_ff_tilt = k_plat_ff * plat_tilt_vel_deg_s

            if self.controller_type == "ADRC":
                # ADRC's Extended State Observer (ESO) observes lumped disturbance dynamics.
                # In 2-DOF ADRC, total gimbal rate = feedback (ADRC) + feedforward (target + platform).
                # To prevent the ESO from misidentifying feedforward as an external disturbance,
                # the ESO observes the feedback velocity component: actual_rate - plat_ff - ff.
                adrc_scale = gains.kp / max(1e-3, self.scheduler.gains_track.kp)
                eso_pan_rate = act_pan_r - plat_ff_pan - ff_pan
                eso_tilt_rate = act_tilt_r - plat_ff_tilt - ff_tilt
                pid_pan, pid_tilt = self.adrc.compute(
                    pat_state.pan_error_deg,
                    pat_state.tilt_error_deg,
                    dt,
                    gain_scale=adrc_scale,
                    actual_pan_rate=eso_pan_rate,
                    actual_tilt_rate=eso_tilt_rate,
                )
                raw_cmd_pan = pid_pan + ff_pan + plat_ff_pan
                raw_cmd_tilt = pid_tilt + ff_tilt + plat_ff_tilt
            else:
                # Dynamic Transport Delay Measurement & Relative Kinematic Forward Extrapolation
                if measured_latency_s is not None and measured_latency_s > 0.0:
                    tau_motor = 0.0167  # Physical actuator acceleration time constant (~16.7 ms)
                    base_latency = measured_latency_s + 0.5 * dt + tau_motor
                else:
                    base_latency = self.lead_time_s

                # Uncertainty-weighted attenuation to prevent over-projection under noisy/degraded conditions
                q_factor = float(np.clip(pat_state.track_quality, 0.0, 1.0))
                eff_lead_time = base_latency * q_factor

                # Relative velocity between moving target, platform motion, and gimbal
                # Clamped to ±2.5 deg/s to prevent optical high-frequency jitter from blowing up predictive projection
                max_rel_vel = 2.5  # deg/s
                rel_pan_vel = float(np.clip((pan_vel_deg_s + plat_pan_vel_deg_s) - act_pan_r, -max_rel_vel, max_rel_vel))
                rel_tilt_vel = float(np.clip((tilt_vel_deg_s + plat_tilt_vel_deg_s) - act_tilt_r, -max_rel_vel, max_rel_vel))

                # Relative kinematic extrapolation: true pointing error projected to actuation instant
                pan_error_pred = pat_state.pan_error_deg + rel_pan_vel * eff_lead_time
                tilt_error_pred = pat_state.tilt_error_deg + rel_tilt_vel * eff_lead_time

                # Pass through modernized continuous-time Smith Predictor
                pan_error_pred, tilt_error_pred = self.smith_predictor.predict_error(
                    pan_error_pred, tilt_error_pred, self._prev_cmd_pan, self._prev_cmd_tilt, dt, latency_s=eff_lead_time
                )

                if self.controller_type == "LQG":
                    pid_pan = self.lqg_pan.compute(pan_error_pred, rel_pan_vel, dt)
                    pid_tilt = self.lqg_tilt.compute(tilt_error_pred, rel_tilt_vel, dt)
                else:
                    # Calculate PID pointing error commands using scheduled gains
                    pid_pan = self.pan_pid.compute(
                        pan_error_pred,
                        dt,
                        kp=gains.kp,
                        ki=gains.ki,
                        kd=gains.kd,
                    )
                    pid_tilt = self.tilt_pid.compute(
                        tilt_error_pred,
                        dt,
                        kp=gains.kp,
                        ki=gains.ki,
                        kd=gains.kd,
                    )

                raw_cmd_pan = pid_pan + ff_pan + plat_ff_pan
                raw_cmd_tilt = pid_tilt + ff_tilt + plat_ff_tilt

            # 6. Mode-Adaptive Anti-Hunting Command Rate-of-Change Damping Filter
            # In TRACK (steady-state): tight smoothing (800 deg/s²) damps noise chatter
            # In ACQUIRE/DEGRADED: looser limit (3000 deg/s²) ensures fast pull-in response
            # This prevents the old 120 deg/s² clamp from creating a 1-2 frame dead-band
            # during acquisition and reacquisition phases.
            if mode == PATMode.TRACK and pat_state.track_quality > 0.6:
                eff_accel_limit = self._track_mode_rate_limit  # 800 deg/s² — steady-state
            else:
                eff_accel_limit = 3000.0  # near-instantaneous response for pull-in

            max_delta = eff_accel_limit * dt
            delta_pan = float(np.clip(raw_cmd_pan - self._prev_cmd_pan, -max_delta, max_delta))
            delta_tilt = float(np.clip(raw_cmd_tilt - self._prev_cmd_tilt, -max_delta, max_delta))

            cmd_pan = self._prev_cmd_pan + delta_pan
            cmd_tilt = self._prev_cmd_tilt + delta_tilt

            self._prev_cmd_pan = cmd_pan
            self._prev_cmd_tilt = cmd_tilt

        else:
            cmd_pan, cmd_tilt = 0.0, 0.0
            pid_pan, pid_tilt = 0.0, 0.0
            ff_pan, ff_tilt = 0.0, 0.0
            self.reset()

        # 7. Apply actuator rate saturation limits
        actual_cmd_pan, actual_cmd_tilt, is_saturated = self.saturation.apply(cmd_pan, cmd_tilt)
        pat_state.is_saturated = is_saturated

        # 8. Dispatch command to gimbal actuator interface
        if gimbal is not None:
            gimbal.set_rate_command(actual_cmd_pan, actual_cmd_tilt)
        else:
            self.actuator_interface.send_rate_command(actual_cmd_pan, actual_cmd_tilt)

        return (actual_cmd_pan, actual_cmd_tilt, pid_pan, pid_tilt, ff_pan, ff_tilt, is_saturated)

    def get_estimated_disturbance(self) -> Tuple[float, float]:
        """Returns the real-time estimated lumped disturbance rates (pan, tilt) in deg/s."""
        if hasattr(self, "adrc") and hasattr(self.adrc, "get_estimated_disturbances"):
            return self.adrc.get_estimated_disturbances()
        return (0.0, 0.0)
