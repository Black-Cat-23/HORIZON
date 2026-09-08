"""
PAT Configuration Thresholds and Engineering Parameters.
HORIZON Phase 6
"""

from dataclasses import dataclass


@dataclass
class PATThresholds:
    """
    Project engineering thresholds for PAT mode transitions and controller safety.
    All parameters are documented engineering parameters for the SIL simulation platform.
    """
    # Acquisition thresholds
    acquire_required_frames: int = 3          # N consecutive valid detections required to transition ACQUIRE -> TRACK
    min_acquisition_confidence: float = 0.35  # Minimum perception confidence required for candidate consideration

    # Degradation & Loss thresholds
    degraded_miss_frames: int = 2             # Missed frames before entering DEGRADED mode
    reacquire_trigger_frames: int = 5         # Consecutive misses or lost association to trigger REACQUIRE
    maximum_prediction_frames: int = 30       # Maximum purely estimated prediction frames before full SEARCH fallback
    reacquire_timeout_s: float = 8.0          # Max duration allowed in REACQUIRE mode before reset to SEARCH

    # Quality & Covariance thresholds
    min_track_quality: float = 0.30           # Track quality below which system enters DEGRADED
    max_position_covariance_px2: float = 2500.0  # (50px 1-sigma)^2 max covariance limit
    max_mahalanobis_gate: float = 16.0        # Outlier gate threshold

    # Controller limits
    max_pan_rate_deg_s: float = 20.0          # Maximum pan slew rate (degrees/sec)
    max_tilt_rate_deg_s: float = 20.0         # Maximum tilt slew rate (degrees/sec)
    degraded_gain_scale: float = 0.5          # Gain scale factor during DEGRADED tracking to avoid chasing noise
