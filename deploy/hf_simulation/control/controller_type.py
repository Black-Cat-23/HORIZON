from enum import Enum

class ControllerType(str, Enum):
    PID = "PID"
    PID_LOOKAHEAD = "PID_LOOKAHEAD"
    MPC = "MPC"
    MPC_LOOKAHEAD = "MPC_LOOKAHEAD"

