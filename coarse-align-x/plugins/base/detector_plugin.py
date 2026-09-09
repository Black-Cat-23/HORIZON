from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Any

@dataclass
class PluginMetadata:
    """Metadata describing a plugin.

    Attributes:
        name: Human‑readable name of the plugin.
        version: Semantic version string, e.g. "1.0.0".
        author: Author or organization.
        description: Short description of what the plugin does.
        plugin_type: One of "detector", "estimator", "controller".
        requires_gpu: Whether the plugin needs GPU resources.
        min_fps: Minimum acceptable frames‑per‑second for real‑time operation.
    """
    name: str
    version: str
    author: str
    description: str
    plugin_type: str  # "detector" | "estimator" | "controller"
    requires_gpu: bool = False
    min_fps: float = 20.0

class DetectorPlugin(ABC):
    """Abstract base class for custom beacon detectors.

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

        The ``config`` dict contains simulation‑level parameters such as
        image dimensions and camera field of view.
        """
        ...

    @abstractmethod
    def detect(self, frame: Any, timestamp: float) -> Dict[str, Any]:
        """Process a single frame and return detection results.

        Args:
            frame: A 2‑D ``uint8`` NumPy array (height x width) representing
                the grayscale camera image.
            timestamp: Simulation time in seconds.

        Returns:
            A dictionary with the keys defined in the spec, e.g.
            ``detected``, ``centroid_x``, ``centroid_y``, ``bbox_x``,
            ``bbox_y``, ``bbox_width``, ``bbox_height``, ``confidence``,
            ``candidate_count``, ``processing_time_ms``.
        """
        ...

    @abstractmethod
    def reset(self) -> None:
        """Reset internal state (called on experiment reset/seek)."""
        ...

    def teardown(self) -> None:
        """Optional cleanup (called on application exit)."""
        pass

