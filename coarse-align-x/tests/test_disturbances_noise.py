"""
HORIZON Phase 3 Unit Tests: Sensor Noise Models
======================================================
Formal mathematical and statistical testing for:
  - Salt & Pepper noise
  - Gaussian noise (sigma <= 20 px enforced)
  - Poisson shot noise
"""

import numpy as np
import pytest

from simulator.core.seed_manager import SeedManager
from simulator.disturbances.config import (
    DisturbanceConfig,
    GaussianNoiseConfig,
    PoissonNoiseConfig,
    SaltPepperConfig,
    validate_disturbance_config,
)
from simulator.disturbances.noise import (
    apply_gaussian_noise,
    apply_poisson_noise,
    apply_salt_and_pepper_noise,
)


class TestSaltAndPepperNoise:
    """Mathematical and statistical validation of Salt & Pepper noise."""

    def test_zero_probability_identity(self):
        seed_mgr = SeedManager(seed=42)
        rng = seed_mgr.get_rng("salt_pepper")
        frame = np.full((480, 640), 128, dtype=np.uint8)

        out = apply_salt_and_pepper_noise(frame, probability=0.0, rng=rng)
        assert np.array_equal(out, frame)

    def test_shape_and_dtype_preserved(self):
        seed_mgr = SeedManager(seed=42)
        rng = seed_mgr.get_rng("salt_pepper")
        frame = np.random.default_rng(1).integers(0, 256, size=(480, 640), dtype=np.uint8)

        out = apply_salt_and_pepper_noise(frame, probability=0.10, rng=rng)
        assert out.shape == (480, 640)
        assert out.dtype == np.uint8
        assert out.min() >= 0
        assert out.max() <= 255

    def test_statistical_rate_ten_percent(self):
        seed_mgr = SeedManager(seed=123)
        rng = seed_mgr.get_rng("salt_pepper")
        # Use constant mid-gray so salt (255) and pepper (0) are distinct
        frame = np.full((1000, 1000), 128, dtype=np.uint8)
        p = 0.10

        out = apply_salt_and_pepper_noise(frame, probability=p, rng=rng)

        salt_count = np.count_nonzero(out == 255)
        pepper_count = np.count_nonzero(out == 0)
        total_corrupted = salt_count + pepper_count
        total_pixels = frame.size

        corrupted_ratio = total_corrupted / total_pixels
        salt_ratio = salt_count / total_pixels
        pepper_ratio = pepper_count / total_pixels

        # Allow 3-sigma tolerance for 1M pixels: std = sqrt(p*(1-p)/N) ≈ 0.0003
        assert pytest.approx(p, abs=0.005) == corrupted_ratio
        assert pytest.approx(p / 2.0, abs=0.005) == salt_ratio
        assert pytest.approx(p / 2.0, abs=0.005) == pepper_ratio

    def test_deterministic_output(self):
        frame = np.full((480, 640), 100, dtype=np.uint8)

        rng1 = SeedManager(seed=99).get_rng("salt_pepper")
        out1 = apply_salt_and_pepper_noise(frame, 0.10, rng1)

        rng2 = SeedManager(seed=99).get_rng("salt_pepper")
        out2 = apply_salt_and_pepper_noise(frame, 0.10, rng2)

        assert np.array_equal(out1, out2)


class TestGaussianNoise:
    """Formal mathematical validation of Gaussian sensor noise."""

    def test_sigma_zero_identity(self):
        rng = SeedManager(seed=42).get_rng("gaussian")
        frame = np.full((480, 640), 150, dtype=np.uint8)

        out = apply_gaussian_noise(frame, sigma=0.0, rng=rng)
        assert np.array_equal(out, frame)

    def test_sigma_upper_bound_enforced(self):
        rng = SeedManager(seed=42).get_rng("gaussian")
        frame = np.full((100, 100), 128, dtype=np.uint8)

        # Sigma 20 is valid
        out = apply_gaussian_noise(frame, sigma=20.0, rng=rng)
        assert out.shape == frame.shape

        # Sigma 20.01 must be rejected per SIH specification
        with pytest.raises(ValueError, match=r"\[0\.0, 20\.0\]"):
            apply_gaussian_noise(frame, sigma=20.01, rng=rng)

        # Negative sigma must be rejected
        with pytest.raises(ValueError, match=r"\[0\.0, 20\.0\]"):
            apply_gaussian_noise(frame, sigma=-1.0, rng=rng)

    def test_empirical_standard_deviation_matches_configured(self):
        # Use large sample to verify sample std matches configured sigma
        frame = np.full((1000, 1000), 128, dtype=np.uint8)
        sigma = 10.0
        rng = SeedManager(seed=777).get_rng("gaussian")

        out = apply_gaussian_noise(frame, sigma=sigma, rng=rng)
        diff = out.astype(np.float64) - frame.astype(np.float64)

        measured_std = np.std(diff)
        measured_mean = np.mean(diff)

        assert pytest.approx(0.0, abs=0.1) == measured_mean
        assert pytest.approx(sigma, rel=0.03) == measured_std

    def test_clipping_bounds_respected(self):
        # Test extreme frames near boundaries 0 and 255
        frame_low = np.zeros((200, 200), dtype=np.uint8)
        frame_high = np.full((200, 200), 255, dtype=np.uint8)
        rng = SeedManager(seed=42).get_rng("gaussian")

        out_low = apply_gaussian_noise(frame_low, sigma=20.0, rng=rng)
        out_high = apply_gaussian_noise(frame_high, sigma=20.0, rng=rng)

        assert out_low.min() >= 0
        assert out_low.max() <= 255
        assert out_high.min() >= 0
        assert out_high.max() <= 255
        assert out_low.dtype == np.uint8
        assert out_high.dtype == np.uint8

    def test_deterministic_output(self):
        frame = np.full((480, 640), 120, dtype=np.uint8)

        rng1 = SeedManager(seed=55).get_rng("gaussian")
        out1 = apply_gaussian_noise(frame, 15.0, rng1)

        rng2 = SeedManager(seed=55).get_rng("gaussian")
        out2 = apply_gaussian_noise(frame, 15.0, rng2)

        assert np.array_equal(out1, out2)


class TestPoissonNoise:
    """Mathematical validation of Poisson photon shot noise."""

    def test_shape_and_dtype_preserved(self):
        frame = np.full((480, 640), 120, dtype=np.uint8)
        rng = SeedManager(seed=42).get_rng("poisson")

        out = apply_poisson_noise(frame, peak_photons=50.0, rng=rng)
        assert out.shape == (480, 640)
        assert out.dtype == np.uint8
        assert out.min() >= 0
        assert out.max() <= 255

    def test_invalid_peak_photons_rejected(self):
        frame = np.full((50, 50), 100, dtype=np.uint8)
        rng = SeedManager(seed=42).get_rng("poisson")

        with pytest.raises(ValueError, match="peak_photons must be > 0.0"):
            apply_poisson_noise(frame, peak_photons=0.0, rng=rng)

        with pytest.raises(ValueError, match="peak_photons must be > 0.0"):
            apply_poisson_noise(frame, peak_photons=-5.0, rng=rng)

    def test_variance_scaling_with_photon_count(self):
        # Higher peak_photons (higher exposure) -> lower relative variance
        frame = np.full((500, 500), 128, dtype=np.uint8)

        rng1 = SeedManager(seed=101).get_rng("poisson")
        low_exposure = apply_poisson_noise(frame, peak_photons=20.0, rng=rng1)
        var_low = np.var(low_exposure.astype(np.float64))

        rng2 = SeedManager(seed=101).get_rng("poisson")
        high_exposure = apply_poisson_noise(frame, peak_photons=200.0, rng=rng2)
        var_high = np.var(high_exposure.astype(np.float64))

        # Relative shot noise variance must be significantly higher at low photon count
        assert var_low > var_high

    def test_deterministic_output(self):
        frame = np.full((480, 640), 140, dtype=np.uint8)

        rng1 = SeedManager(seed=333).get_rng("poisson")
        out1 = apply_poisson_noise(frame, peak_photons=60.0, rng=rng1)

        rng2 = SeedManager(seed=333).get_rng("poisson")
        out2 = apply_poisson_noise(frame, peak_photons=60.0, rng=rng2)

        assert np.array_equal(out1, out2)
