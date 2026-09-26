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
    Single-axis Active Disturbance Rejection Controller for velocity-commanded optical tracking gimbals.
    Upgraded to a 2nd-order Non-Linear Extended State Observer (NLESO) with Han's fal() error compression
    and actuator anti-windup rate feedback.
    """

    def __init__(
        self,
        b0: float = 1.0,
        omega_o: float = 12.0,
        omega_c: float = 2.8,
        output_limit: float = 20.0,
        alpha1: float = 0.75,
        alpha2: float = 0.50,
        delta: float = 0.05,
    ):
        """
        Args:
            b0: System input gain estimate (deg/s per unit rate command).
            omega_o: Observer bandwidth (rad/s). Tuned for discrete 60Hz stability (< Nyquist / 10).
            omega_c: Controller bandwidth (rad/s). Sets closed-loop error response speed.
            output_limit: Maximum allowed rate command output in deg/s.
            alpha1: Non-linear position error exponent for NLESO z1 state (0 < alpha1 < 1).
            alpha2: Non-linear disturbance error exponent for NLESO z2 state (0 < alpha2 < 1).
            delta: Linear threshold boundary in degrees (fine boresight region).
        """
        self.b0 = float(b0)
        self.omega_o = float(omega_o)
        self.omega_c = float(omega_c)
        self.output_limit = float(output_limit)
        self.alpha1 = float(alpha1)
        self.alpha2 = float(alpha2)
        self.delta = float(delta)

        # 1st-order system NLESO observer gains: (s + omega_o)^2 = s^2 + 2*w_o*s + w_o^2
        self.beta1 = 2.0 * self.omega_o
        self.beta2 = self.omega_o ** 2

        # State feedback proportional gain via bandwidth parameterization
        self.kp = self.omega_c

        # Internal state vector:
        # z1 = estimate of pointing error (deg)
        # z2 = estimate of total lumped disturbance rate f (deg/s)
        self.z1 = 0.0
        self.z2 = 0.0
        self.last_u = 0.0
        self.u_act = 0.0
        self.tau_actuator = 0.0167  # Physical motor acceleration lag (~16.7 ms)
        self.initialized = False

    def reset(self) -> None:
        self.z1 = 0.0
        self.z2 = 0.0
        self.last_u = 0.0
        self.u_act = 0.0
        self.initialized = False

    def compute(
        self,
        error: float,
        dt: float,
        gain_scale: float = 1.0,
        actual_rate: Optional[float] = None,
    ) -> float:
        """
        Computes rate control command using NLESO-based Active Disturbance Rejection.

        Args:
            error: Current position error (deg).
            dt: Timestep (seconds).
            gain_scale: Scale factor for controller bandwidth (from GainScheduler).
            actual_rate: Optional measured gimbal angular velocity (deg/s) for anti-windup.

        Returns:
            Commanded angular velocity rate (deg/s).
        """
        if dt <= 0.0:
            return 0.0

        if not self.initialized:
            self.z1 = float(error)
            self.z2 = 0.0
            self.last_u = 0.0
            self.u_act = float(actual_rate) if actual_rate is not None else 0.0
            self.initialized = True

        # Actuator Anti-Windup: use actual physical gimbal velocity if available,
        # otherwise propagate internal 1st-order rate-lag model with saturation
        if actual_rate is not None:
            u_plant = float(actual_rate)
            self.u_act = u_plant
        else:
            du = (self.last_u - self.u_act) * (dt / max(1e-4, self.tau_actuator))
            self.u_act = float(np.clip(self.u_act + du, -self.output_limit, self.output_limit))
            u_plant = self.u_act

        # 1. Update Non-Linear Extended State Observer (NLESO)
        # Bound innovation to prevent numerical overflow under extreme glitches
        obs_err = float(np.clip(error - self.z1, -15.0, 15.0))

        # Han's fal() non-linear error compression
        fal1 = fal(obs_err, alpha=self.alpha1, delta=self.delta)
        fal2 = fal(obs_err, alpha=self.alpha2, delta=self.delta)

        # 1st-order plant dynamics with physical plant feedback:
        # dz1 = -b0 * u_plant + z2 + beta1 * fal1
        # dz2 = beta2 * fal2
        dz1 = -self.b0 * u_plant + self.z2 + self.beta1 * fal1
        dz2 = self.beta2 * fal2

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
        """Returns the real-time estimated lumped disturbance f(t) in deg/s."""
        return self.z2


class DualAxisADRCController:
    """
    Dual-axis (Pan / Tilt) Active Disturbance Rejection Controller for optical tracking gimbals.
    Equipped with 2-axis NLESO observers and real-time disturbance estimation telemetry.
    """

    def __init__(
        self,
        max_pan_rate_deg_s: float = 20.0,
        max_tilt_rate_deg_s: float = 20.0,
        b0: float = 1.0,
        omega_o: float = 12.0,
        omega_c: float = 2.8,
        alpha1: float = 0.75,
        alpha2: float = 0.50,
        delta: float = 0.05,
    ):
        self.pan_adrc = ADRCAxisController(
            b0=b0,
            omega_o=omega_o,
            omega_c=omega_c,
            output_limit=max_pan_rate_deg_s,
            alpha1=alpha1,
            alpha2=alpha2,
            delta=delta,
        )
        self.tilt_adrc = ADRCAxisController(
            b0=b0,
            omega_o=omega_o,
            omega_c=omega_c,
            output_limit=max_tilt_rate_deg_s,
            alpha1=alpha1,
            alpha2=alpha2,
            delta=delta,
        )

    def reset(self) -> None:
        self.pan_adrc.reset()
        self.tilt_adrc.reset()

    def compute(
        self,
        pan_error_deg: float,
        tilt_error_deg: float,
        dt: float,
        gain_scale: float = 1.0,
        actual_pan_rate: Optional[float] = None,
        actual_tilt_rate: Optional[float] = None,
    ) -> Tuple[float, float]:
        """
        Computes pan and tilt angular velocity commands with active disturbance rejection.

        Args:
            pan_error_deg: Pointing error along pan axis in degrees.
            tilt_error_deg: Pointing error along tilt axis in degrees.
            dt: Timestep in seconds.
            gain_scale: Bandwidth scaling factor from GainScheduler.
            actual_pan_rate: Optional physical gimbal pan velocity for anti-windup.
            actual_tilt_rate: Optional physical gimbal tilt velocity for anti-windup.

        Returns:
            Tuple of (cmd_pan, cmd_tilt) in deg/s.
        """
        cmd_pan = self.pan_adrc.compute(
            pan_error_deg, dt, gain_scale=gain_scale, actual_rate=actual_pan_rate
        )
        cmd_tilt = self.tilt_adrc.compute(
            tilt_error_deg, dt, gain_scale=gain_scale, actual_rate=actual_tilt_rate
        )
        return cmd_pan, cmd_tilt

    def get_estimated_disturbances(self) -> Tuple[float, float]:
        """Returns the real-time estimated lumped disturbances (pan, tilt) in deg/s."""
        return (
            self.pan_adrc.get_estimated_disturbance(),
            self.tilt_adrc.get_estimated_disturbance(),
        )
