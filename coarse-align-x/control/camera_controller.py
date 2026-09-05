"""
PAT Mode-Aware Camera Controller.
HORIZON Phase 6
"""

from typing import Tuple, Dict, Any, Optional
from pat.state import PATMode, PATState
from pat.thresholds import PATThresholds
from .pid import PIDController
from .feedforward import VelocityFeedForward
from .saturation import ControllerSaturation
from .actuator_interface import ActuatorInterface


class PATCameraController:
    """
    Master closed-loop camera controller combining PID control, velocity feedforward,
    actuator saturation limiting, and mode-dependent control output generation.
    """

    def __init__(self, thresholds: Optional[PATThresholds] = None):
        self.thresholds = thresholds or PATThresholds()
        
        self.pan_pid = PIDController(kp=1.2, ki=0.05, kd=0.15, output_limit=self.thresholds.max_pan_rate_deg_s)
        self.tilt_pid = PIDController(kp=1.2, ki=0.05, kd=0.15, output_limit=self.thresholds.max_tilt_rate_deg_s)
        
        self.feedforward = VelocityFeedForward(kff_pan=0.5, kff_tilt=0.5, enabled=False)
        self.saturation = ControllerSaturation(
            max_pan_rate_deg_s=self.thresholds.max_pan_rate_deg_s,
            max_tilt_rate_deg_s=self.thresholds.max_tilt_rate_deg_s,
        )
        self.actuator_interface = ActuatorInterface()

    def reset(self) -> None:
        self.pan_pid.reset()
        self.tilt_pid.reset()

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
        gimbal: Optional[Any] = None,
    ) -> Tuple[float, float, float, float, float, float, bool]:
        """
        Calculates commanded pan and tilt rates based on current PAT mode.
        
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
            # Scale gain during DEGRADED tracking
            gain_scale = self.thresholds.degraded_gain_scale if mode == PATMode.DEGRADED else 1.0

            # Calculate PID pointing error commands
            pid_pan = self.pan_pid.compute(pat_state.pan_error_deg, dt, gain_scale=gain_scale)
            pid_tilt = self.tilt_pid.compute(pat_state.tilt_error_deg, dt, gain_scale=gain_scale)

            # Convert pixel velocity estimate to angular velocity estimate for feed-forward
            pan_vel_deg_s = estimated_vx_px_s * (self.thresholds.max_pan_rate_deg_s / 640.0)
            tilt_vel_deg_s = estimated_vy_px_s * (self.thresholds.max_tilt_rate_deg_s / 480.0)
            ff_pan, ff_tilt = self.feedforward.compute(pan_vel_deg_s, tilt_vel_deg_s)

            cmd_pan = pid_pan + ff_pan
            cmd_tilt = pid_tilt + ff_tilt

        else:
            cmd_pan, cmd_tilt = 0.0, 0.0
            pid_pan, pid_tilt = 0.0, 0.0
            ff_pan, ff_tilt = 0.0, 0.0

        # Apply actuator rate saturation limits
        actual_cmd_pan, actual_cmd_tilt, is_saturated = self.saturation.apply(cmd_pan, cmd_tilt)
        pat_state.is_saturated = is_saturated

        # Dispatch command to gimbal actuator interface
        if gimbal is not None:
            gimbal.set_rate_command(actual_cmd_pan, actual_cmd_tilt)
        else:
            self.actuator_interface.send_rate_command(actual_cmd_pan, actual_cmd_tilt)

        return (actual_cmd_pan, actual_cmd_tilt, pid_pan, pid_tilt, ff_pan, ff_tilt, is_saturated)
