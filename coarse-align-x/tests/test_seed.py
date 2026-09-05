"""Tests for deterministic SeedManager."""

import pytest
import numpy as np
from simulator.core.seed_manager import SeedManager


class TestSeedManager:
    """Validate deterministic random number generation."""

    def test_initialization(self):
        sm = SeedManager(seed=42)
        assert sm.seed == 42
        assert sm.root_rng is not None

    def test_negative_seed_rejected(self):
        with pytest.raises(ValueError, match="Seed must be non-negative"):
            SeedManager(seed=-1)

    def test_identical_seed_produces_identical_sequences(self):
        sm1 = SeedManager(seed=12345)
        sm2 = SeedManager(seed=12345)

        rng1 = sm1.get_rng("test_stream")
        rng2 = sm2.get_rng("test_stream")

        vals1 = rng1.uniform(0.0, 1.0, size=100)
        vals2 = rng2.uniform(0.0, 1.0, size=100)

        np.testing.assert_array_equal(vals1, vals2)

    def test_different_seeds_produce_different_sequences(self):
        sm1 = SeedManager(seed=100)
        sm2 = SeedManager(seed=200)

        rng1 = sm1.get_rng("stream")
        rng2 = sm2.get_rng("stream")

        vals1 = rng1.uniform(0.0, 1.0, size=100)
        vals2 = rng2.uniform(0.0, 1.0, size=100)

        assert not np.array_equal(vals1, vals2)

    def test_idempotent_get_rng(self):
        sm = SeedManager(seed=42)
        rng_a = sm.get_rng("alpha")
        rng_b = sm.get_rng("alpha")
        assert rng_a is rng_b

    def test_independent_child_streams(self):
        sm = SeedManager(seed=42)
        rng1 = sm.get_rng("stream1")
        rng2 = sm.get_rng("stream2")

        v1 = rng1.uniform(0.0, 1.0, size=50)
        v2 = rng2.uniform(0.0, 1.0, size=50)

        # Streams spawned from different indices should not be identical
        assert not np.array_equal(v1, v2)

    def test_reset_reproduces_exact_sequence(self):
        sm = SeedManager(seed=999)
        rng = sm.get_rng("reset_test")
        first_draw = rng.normal(0.0, 1.0, size=50)

        sm.reset()
        rng_after_reset = sm.get_rng("reset_test")
        second_draw = rng_after_reset.normal(0.0, 1.0, size=50)

        np.testing.assert_array_equal(first_draw, second_draw)
