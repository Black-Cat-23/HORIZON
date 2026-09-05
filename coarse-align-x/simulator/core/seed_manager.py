"""
HORIZON Deterministic Seed Manager
===========================================
Manages deterministic random number generation using NumPy's modern
Generator API with SeedSequence for reproducible experiments and
independent child RNG streams.

No uncontrolled calls to np.random global state are made.
"""

from __future__ import annotations

import logging
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)


class SeedManager:
    """Deterministic random seed manager for reproducible experiments.

    Uses NumPy's SeedSequence to create independent, deterministic RNG
    streams. Each named child stream is spawned from the root seed,
    ensuring that:
      - Identical seed → identical outputs
      - Different seed → different stochastic behavior
      - Child streams do not interfere with each other

    Usage:
        seed_mgr = SeedManager(seed=42)
        trajectory_rng = seed_mgr.get_rng("trajectory")
        placement_rng = seed_mgr.get_rng("placement")
    """

    def __init__(self, seed: int) -> None:
        """Initialize with a global experiment seed.

        Args:
            seed: Global seed for the experiment. Must be non-negative.

        Raises:
            ValueError: If seed is negative.
        """
        if seed < 0:
            raise ValueError(f"Seed must be non-negative, got {seed}")

        self._seed: int = seed
        self._seed_sequence: np.random.SeedSequence = np.random.SeedSequence(
            seed
        )
        self._root_rng: np.random.Generator = np.random.default_rng(
            self._seed_sequence
        )
        self._children: dict[str, np.random.Generator] = {}
        self._spawn_counter: int = 0

        logger.debug("SeedManager initialized with seed=%d", seed)

    @property
    def seed(self) -> int:
        """The global experiment seed."""
        return self._seed

    @property
    def root_rng(self) -> np.random.Generator:
        """The root RNG (prefer named children for specific modules)."""
        return self._root_rng

    def get_rng(self, name: str) -> np.random.Generator:
        """Get a deterministic RNG for a named module/component.

        Each unique name always produces the same RNG stream for the
        same global seed. Calling get_rng with the same name returns
        the previously created RNG (idempotent).

        Args:
            name: Descriptive name for the RNG stream
                  (e.g., 'trajectory', 'placement', 'noise').

        Returns:
            A deterministic numpy Generator for the named stream.
        """
        if name in self._children:
            return self._children[name]

        # Spawn a new child SeedSequence
        child_ss = self._seed_sequence.spawn(self._spawn_counter + 1)[
            self._spawn_counter
        ]
        self._spawn_counter += 1

        child_rng = np.random.default_rng(child_ss)
        self._children[name] = child_rng

        logger.debug(
            "Created child RNG '%s' (spawn index %d)",
            name, self._spawn_counter - 1,
        )
        return child_rng

    def reset(self) -> None:
        """Reset the seed manager to its initial state.

        Recreates the root SeedSequence and clears all child RNGs,
        so the same sequence of get_rng() calls will produce
        identical RNG streams.
        """
        self._seed_sequence = np.random.SeedSequence(self._seed)
        self._root_rng = np.random.default_rng(self._seed_sequence)
        self._children.clear()
        self._spawn_counter = 0
        logger.debug("SeedManager reset with seed=%d", self._seed)

    def __repr__(self) -> str:
        children = list(self._children.keys())
        return (
            f"SeedManager(seed={self._seed}, "
            f"children={children})"
        )
