"""
Dual-Axis PID Controller with Anti-Windup and Derivative Filtering.
HORIZON Phase 6
"""

from typing import Tuple, Optional
import numpy as np


class PIDController:
    """
    Independent PID controller per axis (Pan / Tilt) with anti-windup clamping,
    first-order low-pass derivative filtering, gain scaling, and clean state resets.
    """

    def __init__(
        self,
        kp: float = 1.2,
        ki: float = 0.05,
        kd: float = 0.15,
        max_integral: float = 2.0,
        output_limit: float = 5.0,
        derivative_filter_tau: float = 0.02,
    ):
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.max_integral = max_integral
        self.output_limit = output_limit
        self.derivative_filter_tau = derivative_filter_tau

        self.integral = 0.0
        self.prev_error = 0.0
        self.filtered_derivative = 0.0
        self.initialized = False

    def reset(self) -> None:
        self.integral = 0.0
        self.prev_error = 0.0
        self.filtered_derivative = 0.0
        self.initialized = False

    def compute(
        self,
        error: float,
        dt: float,
        gain_scale: float = 1.0,
        kp: Optional[float] = None,
        ki: Optional[float] = None,
        kd: Optional[float] = None,
    ) -> float:
        """
        Computes control output u for a given error and timestep dt.
        
        Args:
            error: Pointing error in degrees.
            dt: Timestep in seconds.
            gain_scale: Scale factor for default gains (backward compatibility).
            kp: Explicit proportional gain override (from GainScheduler).
            ki: Explicit integral gain override (from GainScheduler).
            kd: Explicit derivative gain override (from GainScheduler).
            
        Returns:
            Commanded angular velocity rate in deg/s.
        """
        if dt <= 0.0:
            return 0.0

        active_kp = self.kp * gain_scale if kp is None else float(kp)
        active_ki = self.ki * gain_scale if ki is None else float(ki)
        active_kd = self.kd * gain_scale if kd is None else float(kd)

        # Proportional term
        p_term = active_kp * error

        # Integral term with anti-windup clamping (only accumulate when active_ki > 0 to prevent noise windup)
        if active_ki > 0.0:
            self.integral += error * dt
            self.integral = float(np.clip(self.integral, -self.max_integral, self.max_integral))
        i_term = active_ki * self.integral

        # Derivative term with first-order low-pass filter
        if not self.initialized:
            raw_derivative = 0.0
            self.initialized = True
        else:
            raw_derivative = (error - self.prev_error) / dt

        alpha = dt / (dt + self.derivative_filter_tau)
        self.filtered_derivative = (1.0 - alpha) * self.filtered_derivative + alpha * raw_derivative
        d_term = active_kd * self.filtered_derivative

        self.prev_error = error

        # Total PID output
        u = p_term + i_term + d_term

        # Output saturation safety clamp with anti-windup back-calculation
        u_clamped = float(np.clip(u, -self.output_limit, self.output_limit))
        if abs(u_clamped - u) > 1e-4 and (u * error > 0):
            self.integral -= error * dt
            self.integral = float(np.clip(self.integral, -self.max_integral, self.max_integral))

        return u_clamped
