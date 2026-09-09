"""Look‑ahead feed‑forward helper.

This module provides a simple utility to compute a latency‑compensated target
position that can be used by both the PID and MPC controllers. The function
operates only on the estimator output – no ground‑truth leakage.
"""

from typing import Tuple, Dict
import numpy as np

def apply_lookahead(state: Dict[str, float], latency_seconds: float, max_offset_px: float = 50.0, degraded_factor: float = 1.0) -> Tuple[float, float]:
    """Return a look‑ahead target position (x, y) in pixel coordinates.

    Args:
        state: Dictionary containing at least ``pos_x``, ``pos_y`` (pixels) and
            ``vel_x``, ``vel_y`` (pixels/s). Optional ``cov_pos`` (position
            covariance scalar) can be used to attenuate the look‑ahead when the
            estimate is uncertain.
        latency_seconds: System latency Δt to compensate for.
        max_offset_px: Maximum allowed displacement from the current estimate.
        degraded_factor: Multiplier applied in DEGRADED PAT state (default 1.0).

    Returns:
        (lookahead_x, lookahead_y) – the compensated target position.
    """
    # Base offset = velocity * latency
    vx = state.get("vel_x", 0.0)
    vy = state.get("vel_y", 0.0)
    offset_x = vx * latency_seconds * degraded_factor
    offset_y = vy * latency_seconds * degraded_factor

    # Clamp to maximum offset to avoid runaway when velocity estimate is noisy
    offset_norm = np.hypot(offset_x, offset_y)
    if offset_norm > max_offset_px:
        scale = max_offset_px / offset_norm
        offset_x *= scale
        offset_y *= scale

    # Optional confidence scaling – if ``cov_pos`` is provided, reduce the
    # offset when uncertainty is high (simple linear attenuation).
    cov = state.get("cov_pos")
    if cov is not None:
        # Assume cov is variance; map [0, sigma_max] -> [1, 0]
        sigma_max = 1000.0  # placeholder – should be tuned per system
        confidence = max(0.0, min(1.0, 1.0 - np.sqrt(cov) / sigma_max))
        offset_x *= confidence
        offset_y *= confidence

    lookahead_x = state.get("pos_x", 0.0) + offset_x
    lookahead_y = state.get("pos_y", 0.0) + offset_y
    return lookahead_x, lookahead_y

