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
        max_rate_change_deg_s2: float = 120.0,
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

    def reset(self) -> None:
        self.pan_pid.reset()
        self.tilt_pid.reset()
        self.adrc.reset()
        self.smith_predictor.reset()
        self.scurve_ff.reset()
        self.active_gains = self.scheduler.gains_inactive
        self._prev_cmd_pan = 0.0
        self._prev_cmd_tilt = 0.0

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
    ) -> Tuple[float, float, float, float, float, float, bool]:
        """
        Calculates commanded pan and tilt rates with predictive delay compensation
        and command smoothing.

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

            # 3. Forward Kinematic Extrapolation & Smith Predictor Delay Compensation
            eff_lead_time = min(0.033, self.lead_time_s) * float(np.clip(pat_state.track_quality, 0.0, 1.0))
            pan_error_pred = pat_state.pan_error_deg + pan_vel_deg_s * eff_lead_time
            tilt_error_pred = pat_state.tilt_error_deg + tilt_vel_deg_s * eff_lead_time

            # Pass through Smith Predictor for internal plant delay compensation
            pan_error_pred, tilt_error_pred = self.smith_predictor.predict_error(
                pan_error_pred, tilt_error_pred, self._prev_cmd_pan, self._prev_cmd_tilt, dt
            )

            # 4. Closed-Loop Regulation (ADRC, LQG, or PID)
            # 4. Closed-Loop Regulation (ADRC, LQG, or PID)
            if self.controller_type == "ADRC":
                pid_pan, pid_tilt = self.adrc.compute(
                    pan_error_pred, tilt_error_pred, dt, gain_scale=gains.kp
                )
            elif self.controller_type == "LQG":
                act_pan_r = gimbal.actual_pan_rate if gimbal is not None else self._prev_cmd_pan
                act_tilt_r = gimbal.actual_tilt_rate if gimbal is not None else self._prev_cmd_tilt
                pan_err_vel = pan_vel_deg_s - act_pan_r
                tilt_err_vel = tilt_vel_deg_s - act_tilt_r
                pid_pan = self.lqg_pan.compute(pan_error_pred, pan_err_vel, dt)
                pid_tilt = self.lqg_tilt.compute(tilt_error_pred, tilt_err_vel, dt)
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

            # 5. Apply velocity feedforward anticipation (3rd-order Jerk-Limited S-Curve Profiler)
            ff_quality = float(np.clip(pat_state.track_quality, 0.2, 1.0)) if not pat_state.prediction_only else 0.4
            self.scurve_ff.enabled = (gains.kff > 0.0)
            self.scurve_ff.kff_pan = gains.kff * ff_quality
            self.scurve_ff.kff_tilt = gains.kff * ff_quality

            ff_pan, ff_tilt = self.scurve_ff.compute(pan_vel_deg_s, tilt_vel_deg_s, dt=dt)

            raw_cmd_pan = pid_pan + ff_pan
            raw_cmd_tilt = pid_tilt + ff_tilt

            # 6. Anti-Hunting Command Rate-of-Change Damping Filter
            # Limits commanded acceleration to prevent noise chatter
            max_delta = self.max_rate_change_deg_s2 * dt
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
