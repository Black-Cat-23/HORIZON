"""
HORIZON Sensor Noise Engines
===================================
Stochastic sensor noise models conforming to official SIH26169 specifications:
  - Salt & Pepper impulse noise (configurable probability, default ~10%)
  - Additive Gaussian sensor noise (strictly 0 <= sigma <= 20 pixels)
  - Poisson photon-counting shot noise

All random operations derive strictly from isolated deterministic NumPy child
generators. No global np.random state is accessed.
"""

from __future__ import annotations

import numpy as np


def apply_salt_and_pepper_noise(
    frame: np.ndarray,
    probability: float,
    rng: np.random.Generator,
) -> np.ndarray:
    """Apply true Salt & Pepper impulse noise to an image frame.

    For every pixel selected by probability:
      - Salt (50% of chosen): set to maximum intensity (255)
      - Pepper (50% of chosen): set to minimum intensity (0)

    Args:
        frame: Grayscale uint8 frame (e.g. 480×640).
        probability: Fraction of pixels to corrupt (0.0 to 1.0).
        rng: Deterministic NumPy Generator child stream.

    Returns:
        Corrupted uint8 frame of identical dimensions.
    """
    if probability <= 0.0:
        return frame.copy()

    # Probability clamped to [0.0, 1.0]
    p = min(max(float(probability), 0.0), 1.0)
    out = frame.copy()

    # Generate uniform random values per pixel
    rand_vals = rng.random(size=frame.shape, dtype=np.float32)

    # Salt: rand_vals < p / 2.0 -> 255
    # Pepper: p / 2.0 <= rand_vals < p -> 0
    half_p = p / 2.0
    out[rand_vals < half_p] = 255
    out[(rand_vals >= half_p) & (rand_vals < p)] = 0

    return out


def apply_gaussian_noise(
    frame: np.ndarray,
    sigma: float,
    rng: np.random.Generator,
) -> np.ndarray:
    """Apply additive zero-mean Gaussian sensor noise: N(0, sigma^2).

    Intermediate computations are performed in float64, then strictly clipped
    to [0, 255] and converted back to uint8.

    Args:
        frame: Grayscale uint8 frame (480×640).
        sigma: Standard deviation in pixel intensity units.
               Official SIH maximum: 20.0 pixels.
        rng: Deterministic NumPy Generator child stream.

    Returns:
        Noisy uint8 frame with values in [0, 255].

    Raises:
        ValueError: If sigma < 0.0 or sigma > 20.0.
    """
    if sigma < 0.0 or sigma > 20.0:
        raise ValueError(
            f"Gaussian noise sigma must be in [0.0, 20.0] pixels per official SIH specification, got {sigma}"
        )

    if sigma == 0.0:
        return frame.copy()

    noise = rng.normal(loc=0.0, scale=float(sigma), size=frame.shape)
    noisy_float = frame.astype(np.float64) + noise
    clipped = np.clip(noisy_float, 0.0, 255.0)
    return np.rint(clipped).astype(np.uint8)


def apply_poisson_noise(
    frame: np.ndarray,
    peak_photons: float,
    rng: np.random.Generator,
) -> np.ndarray:
    """Apply Poisson photon-counting shot noise.

    Physical photon mapping model:
      Let I in [0, 255] be pixel intensity.
      Expected photon count: lambda = I * (peak_photons / 255.0)
      Measured photon count: k ~ Poisson(lambda)
      Re-scaled intensity:   I_out = k * (255.0 / peak_photons)

    Args:
        frame: Grayscale uint8 frame (480×640).
        peak_photons: Maximum expected photon count corresponding to intensity 255.
                      Must be > 0.0.
        rng: Deterministic NumPy Generator child stream.

    Returns:
        Corrupted uint8 frame.
    """
    if peak_photons <= 0.0:
        raise ValueError(f"peak_photons must be > 0.0, got {peak_photons}")

    scale = float(peak_photons) / 255.0
    lam = frame.astype(np.float64) * scale

    # rng.poisson requires non-negative lam. Non-zero elements sampled:
    # np.random.Generator.poisson handles array lam natively.
    photons = rng.poisson(lam=lam)

    # Reconstruct intensity
    out_float = photons.astype(np.float64) / scale
    clipped = np.clip(out_float, 0.0, 255.0)
    return np.rint(clipped).astype(np.uint8)
