from dataclasses import dataclass, field

@dataclass(frozen=True)
class TurbulenceConfig:
    """Configuration for Kolmogorov turbulence layer.

    All fields have safe defaults that keep turbulence disabled.
    """
    enabled: bool = False
    wavelength_m: float = 1.55e-6  # 1550 nm default
    aperture_diameter_m: float = 0.10  # 10 cm default
    cn2: float = 1.0e-14  # m^(-2/3) – project engineering default
    path_length_m: float = 10000.0  # 10 km default atmospheric path
    wind_speed_m_s: float = 5.0
    correlation_time_s: float | None = None  # auto‑computed if None
    tip_tilt_enabled: bool = True
    psf_broadening_enabled: bool = True
    scintillation_enabled: bool = True
    strong_fluctuation_clamp: float = 0.8

