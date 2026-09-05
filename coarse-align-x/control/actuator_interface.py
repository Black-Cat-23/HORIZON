"""
Actuator Interface Adapter for Camera Gimbal Integration.
HORIZON Phase 6
"""

from typing import Tuple, Optional
from simulator.camera.gimbal import CameraGimbal


class ActuatorInterface:
    """
    Interface adapter for communicating controller velocity commands to the physical CameraGimbal.
    Enforces hardware abstraction layer compliance.
    """

    def __init__(self, gimbal: Optional[CameraGimbal] = None):
        self.gimbal = gimbal or CameraGimbal()

    def send_rate_command(self, pan_rate_deg_s: float, tilt_rate_deg_s: float) -> Tuple[float, float]:
        """
        Sends commanded rates to gimbal and returns commanded rates recorded by the physical model.
        """
        self.gimbal.set_rate_command(pan_rate_deg_s, tilt_rate_deg_s)
        return (self.gimbal.commanded_pan_rate, self.gimbal.commanded_tilt_rate)

    def update_actuator(self, dt: float) -> Tuple[float, float, float, float]:
        """
        Advances gimbal dynamics by timestep dt.
        
        Returns:
            Tuple[pan_deg, tilt_deg, actual_pan_rate_deg_s, actual_tilt_rate_deg_s]
        """
        self.gimbal.step(dt)
        return (
            self.gimbal.pan_deg,
            self.gimbal.tilt_deg,
            self.gimbal.actual_pan_rate,
            self.gimbal.actual_tilt_rate,
        )
