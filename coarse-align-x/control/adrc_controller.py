"""
Active Disturbance Rejection Control (ADRC) for Camera Gimbal Tracking.
HORIZON Phase 12 Upgrade: SOTA Active Disturbance Rejection Control with Extended State Observer (ESO).

ADRC models system dynamics with lumped disturbance:
    y'' = b0 * u + f(t, y, y', u)
where f represents total platform jitter, wind sway, friction, and model mismatch.
An Extended State Observer (ESO) estimates [y, y', f] in real time, allowing direct
disturbance rejection via control law:
    u = (u0 - z3) / b0
"""

from typing import Tuple, Optional
import numpy as np


class ADRCAxisController:
    """
    Single-axis Active Disturbance Rejection Controller using a 3rd-order Linear
    Extended State Observer (LESO) for disturbance estimation and state feedback control.
    """

    def __init__(
        self,
        b0: float = 1.0,
        omega_o: float = 60.0,
        omega_c: float = 20.0,
        output_limit: float = 20.0,
    ):
        """
        Args:
            b0: System input gain estimate (deg/s^2 per unit control input).
            omega_o: Observer bandwidth (rad/s). Higher values track fast disturbances.
            omega_c: Controller bandwidth (rad/s). Sets closed-loop error response speed.
            output_limit: Maximum allowed rate command output in deg/s.
        """
        self.b0 = b0
        self.omega_o = omega_o
        self.omega_c = omega_c
        self.output_limit = output_limit

        # Compute LESO observer gains via bandwidth parameterization (Hurwitz placement)
        # Characteristic polynomial: (s + omega_o)^3 = s^3 + 3*w_o*s^2 + 3*w_o^2*s + w_o^3
        self.beta1 = 3.0 * omega_o
        self.beta2 = 3.0 * (omega_o ** 2)
        self.beta3 = omega_o ** 3

        # Compute state feedback controller gains via pole placement at -omega_c
        # (s + omega_c)^2 = s^2 + 2*w_c*s + w_c^2
        self.kp = omega_c ** 2
        self.kd = 2.0 * omega_c

        # Internal state vector: z1 = estimate of y (error), z2 = estimate of y_dot, z3 = estimate of disturbance f
        self.z1 = 0.0
        self.z2 = 0.0
        self.z3 = 0.0
        self.last_u = 0.0
        self.initialized = False

    def reset(self) -> None:
        self.z1 = 0.0
        self.z2 = 0.0
        self.z3 = 0.0
        self.last_u = 0.0
        self.initialized = False

    def compute(self, error: float, dt: float, gain_scale: float = 1.0) -> float:
        """
        Computes rate control command using ADRC with disturbance rejection.

        Args:
            error: Current position error (deg).
            dt: Timestep (seconds).
            gain_scale: Scale factor for controller bandwidth (used in degraded mode).

        Returns:
            Commanded angular velocity rate (deg/s).
        """
        if dt <= 0.0:
            return 0.0

        if not self.initialized:
            self.z1 = error
            self.z2 = 0.0
            self.z3 = 0.0
            self.initialized = True

        # 1. Update Linear Extended State Observer (LESO) via Euler integration
        obs_err = error - self.z1

        dz1 = self.z2 + self.beta1 * obs_err
        dz2 = self.z3 + self.b0 * self.last_u + self.beta2 * obs_err
        dz3 = self.beta3 * obs_err

        self.z1 += dz1 * dt
        self.z2 += dz2 * dt
        self.z3 += dz3 * dt

        # 2. State Feedback Control Law with scaled bandwidth
        kp_eff = self.kp * gain_scale
        kd_eff = self.kd * np.sqrt(gain_scale)

        # Reference error e = error - z1, error derivative = -z2
        u0 = kp_eff * self.z1 - kd_eff * self.z2

        # 3. Disturbance Compensation
        u_raw = (u0 - self.z3) / self.b0 if abs(self.b0) > 1e-6 else u0

        # Saturation clamping
        u_clamped = float(np.clip(u_raw, -self.output_limit, self.output_limit))
        self.last_u = u_clamped

        return u_clamped

    def get_estimated_disturbance(self) -> float:
        """Returns the real-time estimated lumped disturbance f(t)."""
        return self.z3


class DualAxisADRCController:
    """
    Dual-axis (Pan / Tilt) Active Disturbance Rejection Controller for optical tracking gimbals.
    """

    def __init__(
        self,
        max_pan_rate_deg_s: float = 20.0,
        max_tilt_rate_deg_s: float = 20.0,
        b0: float = 1.0,
        omega_o: float = 60.0,
        omega_c: float = 20.0,
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
