"""
Experiment Manifest and Seed System
===================================
Immutable experiment configurations and deterministic seed generation.
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
import os
import subprocess
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional


def get_git_commit_hash() -> str:
    """Retrieve current git commit hash if in a git repository."""
    try:
        commit = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], stderr=subprocess.DEVNULL, text=True
        ).strip()
        return commit
    except Exception:
        return "UNCOMMITTED_OR_NO_GIT"


class DeterministicSeedSystem:
    """Master-to-trial seed generator producing deterministic seeds.

    Formula: SHA256(master_seed || ":" || scenario_id || ":" || trial_index) % 2^31
    """

    def __init__(self, master_seed: int = 42, scenario_id: str = "nominal") -> None:
        self.master_seed = int(master_seed)
        self.scenario_id = str(scenario_id)

    def get_trial_seed(self, trial_index: int) -> int:
        """Derive deterministic unique 32-bit seed for a specific trial index."""
        seed_key = f"{self.master_seed}:{self.scenario_id}:{trial_index}".encode("utf-8")
        hash_digest = hashlib.sha256(seed_key).hexdigest()
        # Convert first 8 hex characters to int within 31-bit range for standard PRNG compatibility
        trial_seed = int(hash_digest[:8], 16) % (2**31 - 1)
        return trial_seed


def compute_config_hash(config_dict: Dict[str, Any]) -> str:
    """Compute SHA-256 hash of a configuration dictionary to freeze parameters."""
    json_str = json.dumps(config_dict, sort_keys=True, default=str)
    return hashlib.sha256(json_str.encode("utf-8")).hexdigest()[:16]


@dataclass(frozen=True)
class ExperimentManifest:
    """Immutable manifest for a single experiment or Monte Carlo trial."""

    experiment_id: str
    algorithm: str  # "B0", "B1", "B2", "OURS"
    master_seed: int
    trial_seed: int
    trial_index: int
    scenario_id: str
    simulation_duration: float
    simulation_frequency: float

    # Fully resolved configuration sub-trees
    camera_configuration: Dict[str, Any]
    target_configuration: Dict[str, Any]
    trajectory_configuration: Dict[str, Any]
    disturbance_configuration: Dict[str, Any]
    perception_configuration: Dict[str, Any]
    estimator_configuration: Dict[str, Any]
    controller_configuration: Dict[str, Any]

    algorithm_config_hash: str = "FROZEN_DEFAULT"
    software_version: str = "1.0.0"
    git_commit: str = field(default_factory=get_git_commit_hash)
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        """Convert manifest to serializable dictionary."""
        return asdict(self)

    def to_json(self, indent: int = 2) -> str:
        """Serialize manifest to JSON string."""
        return json.dumps(self.to_dict(), indent=indent)

    def save(self, file_path: str | Path) -> None:
        """Save manifest to a JSON file."""
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(self.to_json())

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ExperimentManifest:
        """Construct manifest from dictionary."""
        return cls(**data)

    @classmethod
    def load(cls, file_path: str | Path) -> ExperimentManifest:
        """Load manifest from JSON file."""
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls.from_dict(data)
