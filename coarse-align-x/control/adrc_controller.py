"""
Active Disturbance Rejection Control (ADRC) for Camera Gimbal Tracking.
HORIZON Phase 12 Upgrade: SOTA Active Disturbance Rejection Control with Extended State Observer (ESO).

For rate-controlled optical tracking gimbals, pointing kinematics follow a 1st-order system:
    y_dot = -b0 * u + f(t)
where:
    y: pointing error (deg)
    u: commanded angular slew rate (deg/s)
    b0: actuator rate-response scale factor (~1.0 deg/s per unit command)
    f(t): lumped disturbance (target angular velocity + platform vibration + atmospheric drift)

A 2nd-order Linear Extended State Observer (LESO) estimates in real-time:
    z1 ≈ y (smoothed pointing error)
    z2 ≈ f (total disturbance rate)

Disturbance cancellation & proportional tracking control law:
    u0 = omega_c * z1
    u = (u0 + z2) / b0
"""

from typing import Tuple, Optional
import math
import numpy as np


def fal(e: float, alpha: float = 0.5, delta: float = 0.05) -> float:
    """Non-linear fal function for Extended State Observer (NLESO)."""
    abs_e = abs(e)
    if abs_e > delta:
        return math.copysign(abs_e ** alpha, e)
    else:
        return e / (delta ** (1.0 - alpha))


class ADRCAxisController:
    """
    Single-axis Active Disturbance Rejection Controller for velocity-commanded gimbals.
    Uses a 2nd-order Linear Extended State Observer (LESO) with Hurwitz bandwidth parameterization.
    """

    def __init__(
        self,
        b0: float = 1.0,
        omega_o: float = 10.0,
        omega_c: float = 2.5,
        output_limit: float = 20.0,
    ):
        """
        Args:
            b0: System input gain estimate (deg/s per unit rate command).
            omega_o: Observer bandwidth (rad/s). Tuned for discrete 60Hz stability.
            omega_c: Controller bandwidth (rad/s). Sets closed-loop error response speed.
            output_limit: Maximum allowed rate command output in deg/s.
        """
        self.b0 = b0
        self.omega_o = omega_o
        self.omega_c = omega_c
        self.output_limit = output_limit

        # 1st-order system LESO observer gains: (s + omega_o)^2 = s^2 + 2*w_o*s + w_o^2
        self.beta1 = 2.0 * omega_o
        self.beta2 = omega_o ** 2

        # State feedback proportional gain via bandwidth parameterization
        self.kp = omega_c

        # Internal state vector: z1 = estimate of pointing error, z2 = estimate of total disturbance rate f
        self.z1 = 0.0
        self.z2 = 0.0
        self.last_u = 0.0
        self.initialized = False

    def reset(self) -> None:
        self.z1 = 0.0
        self.z2 = 0.0
        self.last_u = 0.0
        self.initialized = False

    def compute(self, error: float, dt: float, gain_scale: float = 1.0) -> float:
        """
        Computes rate control command using ADRC with active disturbance rejection.

        Args:
            error: Current position error (deg).
            dt: Timestep (seconds).
            gain_scale: Scale factor for controller bandwidth (from GainScheduler).

        Returns:
            Commanded angular velocity rate (deg/s).
        """
        if dt <= 0.0:
            return 0.0

        if not self.initialized:
            self.z1 = float(error)
            self.z2 = 0.0
            self.last_u = 0.0
            self.initialized = True

        # 1. Update Linear Extended State Observer (LESO)
        # Clamp is wide (±15°) to allow convergence from large initial pointing errors
        obs_err = float(np.clip(error - self.z1, -15.0, 15.0))

        # 1st-order plant dynamics: dz1 = -b0 * u + z2 + beta1 * obs_err
        dz1 = -self.b0 * self.last_u + self.z2 + self.beta1 * obs_err
        dz2 = self.beta2 * obs_err

        self.z1 = float(np.clip(self.z1 + dz1 * dt, -20.0, 20.0))
        self.z2 = float(np.clip(self.z2 + dz2 * dt, -100.0, 100.0))

        # 2. State Feedback Control Law with scaled bandwidth
        kp_eff = self.kp * min(max(gain_scale, 0.2), 1.5)
        u0 = kp_eff * self.z1

        # 3. Active Disturbance Rejection Compensation
        u_raw = (u0 + self.z2) / self.b0 if abs(self.b0) > 1e-6 else u0

        # Saturation clamping
        u_clamped = float(np.clip(u_raw, -self.output_limit, self.output_limit))
        self.last_u = u_clamped

        return u_clamped

    def get_estimated_disturbance(self) -> float:
        """Returns the real-time estimated lumped disturbance f(t)."""
        return self.z2


class DualAxisADRCController:
    """
    Dual-axis (Pan / Tilt) Active Disturbance Rejection Controller for optical tracking gimbals.
    """

    def __init__(
        self,
        max_pan_rate_deg_s: float = 20.0,
        max_tilt_rate_deg_s: float = 20.0,
        b0: float = 1.0,
        omega_o: float = 10.0,
        omega_c: float = 2.5,
    ):
        self.pan_adrc = ADRCAxisController(b0=b0, omega_o=omega_o, omega_c=omega_c, output_limit=max_pan_rate_deg_s)
        self.tilt_adrc = ADRCAxisController(b0=b0, omega_o=omega_o, omega_c=omega_c, output_limit=max_tilt_rate_deg_s)

    def reset(self) -> None:
        self.pan_adrc.reset()
        self.tilt_adrc.reset()

    def compute(
        self,
        pan_error_deg: float,
        tilt_error_deg: float,
        dt: float,
        gain_scale: float = 1.0,
    ) -> Tuple[float, float]:
        """
        Computes pan and tilt angular velocity commands with disturbance rejection.
        """
        cmd_pan = self.pan_adrc.compute(pan_error_deg, dt, gain_scale=gain_scale)
        cmd_tilt = self.tilt_adrc.compute(tilt_error_deg, dt, gain_scale=gain_scale)
        return cmd_pan, cmd_tilt
