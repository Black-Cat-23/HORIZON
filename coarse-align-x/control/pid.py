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

    def compute(self, error: float, dt: float, gain_scale: float = 1.0) -> float:
        """
        Computes control output u for a given error and timestep dt.
        
        Args:
            error: Pointing error in degrees.
            dt: Timestep in seconds.
            gain_scale: Scale factor for gains (used in DEGRADED tracking).
            
        Returns:
            Commanded angular velocity rate in deg/s.
        """
        if dt <= 0.0:
            return 0.0

        kp = self.kp * gain_scale
        ki = self.ki * gain_scale
        kd = self.kd * gain_scale

        # Proportional term
        p_term = kp * error

        # Integral term with anti-windup clamping
        self.integral += error * dt
        self.integral = float(np.clip(self.integral, -self.max_integral, self.max_integral))
        i_term = ki * self.integral

        # Derivative term with first-order low-pass filter
        if not self.initialized:
            raw_derivative = 0.0
            self.initialized = True
        else:
            raw_derivative = (error - self.prev_error) / dt

        alpha = dt / (dt + self.derivative_filter_tau)
        self.filtered_derivative = (1.0 - alpha) * self.filtered_derivative + alpha * raw_derivative
        d_term = kd * self.filtered_derivative

        self.prev_error = error

        # Total PID output
        u = p_term + i_term + d_term

        # Output saturation safety clamp
        u_clamped = float(np.clip(u, -self.output_limit, self.output_limit))
        return u_clamped
