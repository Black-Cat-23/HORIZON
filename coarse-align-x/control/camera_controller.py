"""
PAT Mode and Confidence-Aware Camera Controller.
HORIZON — SIH 2026 PS SIH26169 (PDF Section 6.6)
"""

from typing import Tuple, Dict, Any, Optional
from pat.state import PATMode, PATState
from pat.thresholds import PATThresholds
from .pid import PIDController
from .feedforward import VelocityFeedForward
from .saturation import ControllerSaturation
from .actuator_interface import ActuatorInterface
from .gain_scheduler import GainScheduler, ScheduledGains


class PATCameraController:
    """
    Master closed-loop camera controller combining mode-dependent Gain Scheduling,
    PID error regulation, angular velocity feedforward, actuator saturation limiting,
    and gimbal interface dispatch.
    """

    def __init__(
        self,
        thresholds: Optional[PATThresholds] = None,
        scheduler: Optional[GainScheduler] = None,
    ):
        self.thresholds = thresholds or PATThresholds()
        self.scheduler = scheduler or GainScheduler()
        
        # Base PID controllers with physical rate limits
        self.pan_pid = PIDController(kp=1.5, ki=0.08, kd=0.12, output_limit=self.thresholds.max_pan_rate_deg_s)
        self.tilt_pid = PIDController(kp=1.5, ki=0.08, kd=0.12, output_limit=self.thresholds.max_tilt_rate_deg_s)
        
        self.feedforward = VelocityFeedForward(kff_pan=0.6, kff_tilt=0.6, enabled=False)
        self.saturation = ControllerSaturation(
            max_pan_rate_deg_s=self.thresholds.max_pan_rate_deg_s,
            max_tilt_rate_deg_s=self.thresholds.max_tilt_rate_deg_s,
        )
        self.actuator_interface = ActuatorInterface()
        self.active_gains: ScheduledGains = self.scheduler.gains_inactive

    def reset(self) -> None:
        self.pan_pid.reset()
        self.tilt_pid.reset()
        self.active_gains = self.scheduler.gains_inactive

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
        Calculates commanded pan and tilt rates based on current PAT mode and Gain Scheduling.
        
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
            cmd_pan = reacquire_pan_rate
            cmd_tilt = reacquire_tilt_rate
            pid_pan, pid_tilt = 0.0, 0.0
            ff_pan, ff_tilt = 0.0, 0.0
            self.reset()

        elif mode in (PATMode.ACQUIRE, PATMode.TRACK, PATMode.DEGRADED):
            # Compute scheduled gains tailored to current tracking regime and confidence
            gains = self.scheduler.get_gains(
                mode=mode,
                track_quality=pat_state.track_quality,
                continuous_interpolation=True,
            )
            self.active_gains = gains

            # Calculate PID pointing error commands using scheduled gains
            pid_pan = self.pan_pid.compute(
                pat_state.pan_error_deg,
                dt,
                kp=gains.kp,
                ki=gains.ki,
                kd=gains.kd,
            )
            pid_tilt = self.tilt_pid.compute(
                pat_state.tilt_error_deg,
                dt,
                kp=gains.kp,
                ki=gains.ki,
                kd=gains.kd,
            )

            # Determine target angular velocity: use direct 6-state IMM rate if provided, else convert pixel velocity
            if estimated_omega_x_deg_s is not None:
                pan_vel_deg_s = float(estimated_omega_x_deg_s)
            else:
                pan_vel_deg_s = estimated_vx_px_s * (self.thresholds.max_pan_rate_deg_s / 640.0)

            if estimated_omega_y_deg_s is not None:
                tilt_vel_deg_s = float(estimated_omega_y_deg_s)
            else:
                tilt_vel_deg_s = estimated_vy_px_s * (self.thresholds.max_tilt_rate_deg_s / 480.0)

            # Apply scheduled feed-forward gain
            self.feedforward.enabled = (gains.kff > 0.0)
            self.feedforward.kff_pan = gains.kff
            self.feedforward.kff_tilt = gains.kff
            ff_pan, ff_tilt = self.feedforward.compute(pan_vel_deg_s, tilt_vel_deg_s)

            cmd_pan = pid_pan + ff_pan
            cmd_tilt = pid_tilt + ff_tilt

        else:
            cmd_pan, cmd_tilt = 0.0, 0.0
            pid_pan, pid_tilt = 0.0, 0.0
            ff_pan, ff_tilt = 0.0, 0.0
            self.reset()

        # Apply actuator rate saturation limits
        actual_cmd_pan, actual_cmd_tilt, is_saturated = self.saturation.apply(cmd_pan, cmd_tilt)
        pat_state.is_saturated = is_saturated

        # Dispatch command to gimbal actuator interface
        if gimbal is not None:
            gimbal.set_rate_command(actual_cmd_pan, actual_cmd_tilt)
        else:
            self.actuator_interface.send_rate_command(actual_cmd_pan, actual_cmd_tilt)

        return (actual_cmd_pan, actual_cmd_tilt, pid_pan, pid_tilt, ff_pan, ff_tilt, is_saturated)
