import numpy as np
from math import pi, sqrt, log

# Physical constants
C_LIGHT = 299_792_458.0  # m/s

def compute_wavenumber(wavelength_m: float) -> float:
    """Return optical wavenumber k = 2π / λ (rad/m)."""
    return 2.0 * pi / wavelength_m

def fried_parameter(cn2: float, wavelength_m: float, path_length_m: float) -> float:
    """Compute Fried parameter r0.

    r0 = (0.423 * k**2 * Cn2 * L) ** (-3/5)
    where k = 2π / λ.
    Returns r0 in meters.
    """
    k = compute_wavenumber(wavelength_m)
    value = 0.423 * (k ** 2) * cn2 * path_length_m
    if value <= 0:
        raise ValueError("Invalid inputs produce non‑positive Fried parameter argument")
    return value ** (-3.0 / 5.0)

def seeing_fwhm_arcsec(r0_m: float, wavelength_m: float) -> float:
    """Seeing (full‑width half‑maximum) in arcseconds.

    seeing_FWHM = 0.98 * λ / r0  (radians)
    Convert to arcseconds.
    """
    if r0_m <= 0:
        raise ValueError("r0 must be positive for seeing calculation")
    fwhm_rad = 0.98 * wavelength_m / r0_m
    return fwhm_rad * (180.0 / np.pi) * 3600.0

def tip_tilt_std_px(r0_m: float, aperture_m: float, wavelength_m: float, fov_deg: float, frame_width_px: int) -> float:
    """Tip‑tilt standard deviation in pixel units.

    σ²_tt = 0.36 * (D / r0)^(5/3) * (λ / D)²  (rad²)
    Convert rad -> pixels using FOV.
    """
    if r0_m <= 0 or aperture_m <= 0:
        raise ValueError("r0 and aperture must be positive")
    sigma_tt_rad2 = 0.36 * (aperture_m / r0_m) ** (5.0 / 3.0) * (wavelength_m / aperture_m) ** 2
    sigma_tt_rad = sqrt(sigma_tt_rad2)
    fov_rad = np.deg2rad(fov_deg)
    pixels_per_rad = frame_width_px / fov_rad
    return sigma_tt_rad * pixels_per_rad

def ryotv_variance(cn2: float, wavelength_m: float, path_length_m: float) -> float:
    """Rytov variance σ²_R for a plane wave.

    σ²_R = 1.23 * Cn² * k^(7/6) * L^(11/6)
    """
    k = compute_wavenumber(wavelength_m)
    return 1.23 * cn2 * (k ** (7.0 / 6.0)) * (path_length_m ** (11.0 / 6.0))

def correlation_time(r0_m: float, wind_speed_m_s: float) -> float:
    """Approximate correlation time τ = r0 / wind_speed."""
    if wind_speed_m_s <= 0:
        raise ValueError("wind_speed must be positive")
    return r0_m / wind_speed_m_s

__all__ = [
    "fried_parameter",
    "seeing_fwhm_arcsec",
    "tip_tilt_std_px",
    "ryotv_variance",
    "correlation_time",
]

