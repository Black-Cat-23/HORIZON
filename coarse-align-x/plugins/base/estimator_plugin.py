from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Any

# Reuse PluginMetadata defined in detector_plugin.py
from .detector_plugin import PluginMetadata

class EstimatorPlugin(ABC):
    """Abstract base class for custom state estimators.

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

        ``config`` contains items such as ``initial_x``/``initial_y`` and
        ``dt_nominal``.
        """
        ...

    @abstractmethod
    def predict(self, dt: float) -> Dict[str, Any]:
        """Predict state forward by *dt* seconds.

        Returns a dict with keys: ``estimated_x``, ``estimated_y``,
        ``estimated_vx``, ``estimated_vy``, ``covariance_xx``,
        ``covariance_yy``, ``filter_status``.
        """
        ...

    @abstractmethod
    def update(self, measurement: Dict[str, Any], timestamp: float) -> Dict[str, Any]:
        """Update the estimator with a new detection.

        ``measurement`` follows the detector output schema. Returns the
        same dict as ``predict``.
        """
        ...

    @abstractmethod
    def reset(self) -> None:
        """Reset internal state (called on experiment reset/seek)."""
        ...

    def teardown(self) -> None:
        """Optional cleanup (called on application exit)."""
        pass

