from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Any

# Reuse PluginMetadata defined in detector_plugin.py
from .detector_plugin import PluginMetadata

class ControllerPlugin(ABC):
    """Abstract base class for custom camera controllers.

    Implementations must inherit from this class and provide concrete
    implementations of all abstract methods. The plugin system will call
    these methods during simulation.
    """

    @abstractmethod
    def metadata(self) -> PluginMetadata:
        """Return the plugin's metadata."""
        ...

    @abstractmethod
    def initialize(self, config: Dict[str, Any]) -> None:
        """Initialize the plugin before the first frame.

        ``config`` contains items such as ``max_pan_rate_deg_s`` and
        ``max_tilt_rate_deg_s``.
        """
        ...

    @abstractmethod
    def compute(self, state_estimate: Dict[str, Any], camera_state: Dict[str, Any], dt: float) -> Dict[str, Any]:
        """Compute a camera command for the given state.

        Returns a dict with keys ``commanded_pan_rate`` and
        ``commanded_tilt_rate``.
        """
        ...

    @abstractmethod
    def reset(self) -> None:
        """Reset internal state (called on experiment reset/seek)."""
        ...

    def teardown(self) -> None:
        """Optional cleanup (called on application exit)."""
        pass

