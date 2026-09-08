"""
Control Package Initialization.
HORIZON Phase 6
"""

from .pid import PIDController
from .feedforward import VelocityFeedForward
from .saturation import ControllerSaturation
from .actuator_interface import ActuatorInterface
from .gain_scheduler import GainScheduler, ScheduledGains
from .adrc_controller import ADRCAxisController, DualAxisADRCController
from .camera_controller import PATCameraController

__all__ = [
    "PIDController",
    "VelocityFeedForward",
    "ControllerSaturation",
    "ActuatorInterface",
    "GainScheduler",
    "ScheduledGains",
    "ADRCAxisController",
    "DualAxisADRCController",
    "PATCameraController",
]
