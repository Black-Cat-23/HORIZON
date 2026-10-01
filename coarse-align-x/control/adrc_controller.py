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
        omega_o: float = 22.0,
        omega_c: float = 10.0,
        output_limit: float = 20.0,
        alpha1: float = 1.0,
        alpha2: float = 1.0,
        delta: float = 0.1,
    ):
        """
        Args:
            b0: System input gain estimate (deg/s per unit rate command).
            omega_o: Observer bandwidth (rad/s). 22 rad/s provides critically damped discrete ESO dynamics
                     at 60 Hz (discrete pole modulus |z| ≈ 0.63 << 1.0), preventing numerical limit-cycle chatter.
            omega_c: Controller bandwidth (rad/s). 10 rad/s (τ = 100ms) for ISRO benchmark compliance.
            output_limit: Maximum allowed rate command output in deg/s.
            alpha1: Error exponent for ESO z1 state (alpha1=1.0 ensures continuous linear discrete stability).
            alpha2: Disturbance exponent for ESO z2 state (alpha2=1.0 ensures bounded disturbance estimation).
            delta: Linear threshold boundary in degrees.
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
        self.z2_filtered = 0.0
        self.tau_dist_filter = 0.005  # High-fidelity cutoff to decouple 30+ Hz sensor jitter without phase lagging 2-12 Hz disturbance rejection
        self.last_u = 0.0
        self.u_act = 0.0
        self.tau_actuator = 0.0167  # Physical motor acceleration lag (~16.7 ms)
        self.initialized = False

    def reset(self) -> None:
        self.z1 = 0.0
        self.z2 = 0.0
        self.z2_filtered = 0.0
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
            self.z1 = 0.0
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
        # Bound innovation — ESO clip tuned for omega_o=40 (2-3× faster than controller bandwidth)
        # ±25 deg clip prevents observer rail saturation during fast manoeuvres and disturbance bursts.
        obs_err = float(np.clip(error - self.z1, -25.0, 25.0))

        # Han's fal() non-linear error compression
        fal1 = fal(obs_err, alpha=self.alpha1, delta=self.delta)
        fal2 = fal(obs_err, alpha=self.alpha2, delta=self.delta)

        # Adaptive discrete stability limit:
        # Guarantees discrete observer pole modulus |1 - beta1*dt| < 0.70 across any frame rate (30 Hz to 120 Hz)
        w_o_eff = min(self.omega_o, 0.65 / max(1e-4, dt))
        beta1_eff = 2.0 * w_o_eff
        beta2_eff = w_o_eff ** 2

        # 1st-order plant dynamics with physical plant feedback:
        # dz1 = -b0 * u_plant + z2 + beta1 * fal1
        # dz2 = beta2 * fal2
        dz1 = -self.b0 * u_plant + self.z2 + beta1_eff * fal1
        dz2 = beta2_eff * fal2

        # Actuator Anti-Windup on disturbance state z2:
        # If output was saturated in the same direction, freeze disturbance integration to prevent overshoot
        if abs(self.last_u) >= (self.output_limit - 1e-3) and (dz2 * self.last_u > 0.0):
            dz2 = 0.0

        # Physical state bounds: pointing error within ±10.0 deg, lumped disturbance within physical gimbal rate limits (±self.output_limit)
        self.z1 = float(np.clip(self.z1 + dz1 * dt, -10.0, 10.0))
        self.z2 = float(np.clip(self.z2 + dz2 * dt, -self.output_limit, self.output_limit))

        # 1st-order low-pass filter on disturbance rate to decouple 30 Hz white-noise jitter from coarse mechanical gimbal
        gamma = dt / max(1e-4, (self.tau_dist_filter + dt))
        self.z2_filtered += gamma * (self.z2 - self.z2_filtered)

        # 2. State Feedback Control Law with scaled bandwidth
        kp_limit = min(self.kp * min(max(gain_scale, 0.1), 3.0), 0.65 / max(1e-4, dt))
        u0 = kp_limit * self.z1

        # 3. Active Disturbance Rejection Compensation:
        # In steady-state tracking basin (|obs_err| < 0.25 deg), use z2_filtered to prevent high-frequency mechanical hunting
        u_dist = self.z2_filtered if abs(obs_err) < 0.25 else self.z2
        u_raw = (u0 + u_dist) / self.b0 if abs(self.b0) > 1e-6 else u0

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
        b0: float = 0.75,
        omega_o: float = 32.0,
        omega_c: float = 20.0,
        alpha1: float = 1.0,
        alpha2: float = 1.0,
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
