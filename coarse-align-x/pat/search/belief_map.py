"""
Adaptive Belief-Map Search Strategy (PAT Mode 6.4 Differentiator).
HORIZON — SIH 2026 PS SIH26169

Maintains a 2D angular probability map (belief grid) over the Field of Regard (FOR).
Weak detections or candidate cues raise local posterior probability via Bayesian accumulation;
the camera dynamically concentrates search effort toward regions of high probability
rather than scanning rigidly and uniformly like Raster or Spiral baselines.
"""

from __future__ import annotations

import math
from typing import List, Tuple, Optional
import numpy as np

from .base import SearchStrategy


class BeliefMapSearchStrategy(SearchStrategy):
    """
    Adaptive 2D Bayesian Belief-Map Search Strategy.
    
    Attributes:
        span_pan_deg: Horizontal angular search extent in degrees.
        span_tilt_deg: Vertical angular search extent in degrees.
        grid_resolution_deg: Angular spacing per cell in degrees.
        scan_speed_deg_s: Commanded search rate magnitude in deg/s.
        prior_sigma_deg: Standard deviation of initial Gaussian prior around center.
        fov_radius_deg: Angular radius of camera instantaneous FOV footprint for negative evidence.
        discount_rate: Rate at which visited FOV cells lose belief if target is absent.
        evidence_gain: Multiplier for candidate detection likelihood update.
        max_search_time_s: Search timeout threshold in seconds.
    """

    def __init__(
        self,
        span_pan_deg: float = 10.0,
        span_tilt_deg: float = 8.0,
        grid_resolution_deg: float = 0.25,
        scan_speed_deg_s: float = 2.0,
        prior_sigma_deg: float = 1.5,
        fov_radius_deg: float = 1.0,
        discount_rate: float = 0.5,
        evidence_gain: float = 3.0,
        max_search_time_s: float = 25.0,
    ) -> None:
        self.span_pan_deg = float(span_pan_deg)
        self.span_tilt_deg = float(span_tilt_deg)
        self.grid_resolution_deg = float(grid_resolution_deg)
        self.scan_speed_deg_s = float(scan_speed_deg_s)
        self.prior_sigma_deg = float(prior_sigma_deg)
        self.fov_radius_deg = float(fov_radius_deg)
        self.discount_rate = float(discount_rate)
        self.evidence_gain = float(evidence_gain)
        self.max_search_time_s = float(max_search_time_s)

        self.center_pan_deg = 0.0
        self.center_tilt_deg = 0.0

        # Discretized grid coordinates
        self.pan_coords: np.ndarray = np.array([], dtype=float)
        self.tilt_coords: np.ndarray = np.array([], dtype=float)
        self.P_grid: np.ndarray = np.empty((0, 0), dtype=float)
        self.T_grid: np.ndarray = np.empty((0, 0), dtype=float)
        self.belief_grid: np.ndarray = np.empty((0, 0), dtype=float)

        self._elapsed_time_s: float = 0.0
        self._completed: bool = False
        self._trajectory_history: List[Tuple[float, float]] = []

        # Build initial grid
        self._initialize_grid()
        self.reset(self.center_pan_deg, self.center_tilt_deg)

    def _initialize_grid(self) -> None:
        """Initializes coordinate mesh based on angular bounds and resolution."""
        half_pan = self.span_pan_deg / 2.0
        half_tilt = self.span_tilt_deg / 2.0

        self.pan_coords = np.arange(
            self.center_pan_deg - half_pan,
            self.center_pan_deg + half_pan + 1e-5,
            self.grid_resolution_deg,
            dtype=float,
        )
        self.tilt_coords = np.arange(
            self.center_tilt_deg - half_tilt,
            self.center_tilt_deg + half_tilt + 1e-5,
            self.grid_resolution_deg,
            dtype=float,
        )

        self.P_grid, self.T_grid = np.meshgrid(self.pan_coords, self.tilt_coords)
        self.belief_grid = np.zeros_like(self.P_grid, dtype=float)

    def reset(self, center_pan_deg: float = 0.0, center_tilt_deg: float = 0.0) -> None:
        """
        Resets belief map centered around specified angular coordinates.
        Initializes a Gaussian prior distribution reflecting initial uncertainty.
        """
        self.center_pan_deg = float(center_pan_deg)
        self.center_tilt_deg = float(center_tilt_deg)

        self._initialize_grid()

        # Gaussian prior: exp(-0.5 * ((pan - center)^2 + (tilt - center)^2) / sigma^2)
        dist_sq = (self.P_grid - self.center_pan_deg) ** 2 + (self.T_grid - self.center_tilt_deg) ** 2
        sigma_sq = max(self.prior_sigma_deg ** 2, 1e-4)
        prior = np.exp(-0.5 * dist_sq / sigma_sq)

        # Normalize prior so sum(B) == 1.0
        prior_sum = float(np.sum(prior))
        if prior_sum > 0:
            self.belief_grid = prior / prior_sum
        else:
            self.belief_grid = np.ones_like(self.P_grid) / self.P_grid.size

        self._elapsed_time_s = 0.0
        self._completed = False
        self._trajectory_history = [(self.center_pan_deg, self.center_tilt_deg)]

    def update_belief(
        self,
        candidate_pan_deg: float,
        candidate_tilt_deg: float,
        confidence: float,
        uncertainty_deg: float = 0.5,
    ) -> None:
        """
        Performs Bayesian / evidence accumulation update upon receiving candidate detection or clue.
        
        Args:
            candidate_pan_deg: Estimated candidate pan coordinate in degrees.
            candidate_tilt_deg: Estimated candidate tilt coordinate in degrees.
            confidence: Perception / candidate confidence in [0.0, 1.0].
            uncertainty_deg: Spatial uncertainty (standard deviation) of the candidate cue.
        """
        if confidence <= 0.0 or self.belief_grid.size == 0:
            return

        conf_clipped = float(np.clip(confidence, 0.0, 1.0))
        sigma_sq = max(uncertainty_deg ** 2, 0.01)

        # Likelihood kernel centered at candidate
        d_sq = (self.P_grid - candidate_pan_deg) ** 2 + (self.T_grid - candidate_tilt_deg) ** 2
        kernel = np.exp(-0.5 * d_sq / sigma_sq)
        k_sum = float(np.sum(kernel))
        if k_sum > 0:
            kernel /= k_sum

        # Evidence accumulation: weak detections raise local probability,
        # concentrating probability mass where evidence accumulates.
        self.belief_grid += self.evidence_gain * conf_clipped * kernel

        # Re-normalize so sum(B) == 1.0
        total_mass = float(np.sum(self.belief_grid))
        if total_mass > 0:
            self.belief_grid /= total_mass

    def discount_visited(
        self,
        current_pan_deg: float,
        current_tilt_deg: float,
        dt: float,
    ) -> None:
        """
        Discounts belief in regions currently within camera FOV footprint.
        Represents negative information: 'if target was in clear view here, we would have seen it.'
        """
        if self.belief_grid.size == 0 or dt <= 0.0:
            return

        d_sq = (self.P_grid - current_pan_deg) ** 2 + (self.T_grid - current_tilt_deg) ** 2
        fov_sq = max(self.fov_radius_deg ** 2, 0.01)

        # Attenuation factor scaled by inspection duration dt
        visitation = np.exp(-0.5 * d_sq / fov_sq)
        decay = np.clip(self.discount_rate * dt, 0.0, 0.8)
        
        self.belief_grid *= (1.0 - decay * visitation)
        self.belief_grid = np.maximum(self.belief_grid, 1e-12)

        # Re-normalize
        total_mass = float(np.sum(self.belief_grid))
        if total_mass > 0:
            self.belief_grid /= total_mass

    def get_peak_location(self) -> Tuple[float, float, float]:
        """
        Returns (pan_deg, tilt_deg, peak_probability) corresponding to maximum belief cell.
        """
        if self.belief_grid.size == 0:
            return (self.center_pan_deg, self.center_tilt_deg, 0.0)

        max_idx = np.unravel_index(np.argmax(self.belief_grid), self.belief_grid.shape)
        peak_tilt = float(self.tilt_coords[max_idx[0]])
        peak_pan = float(self.pan_coords[max_idx[1]])
        peak_prob = float(self.belief_grid[max_idx])
        return (peak_pan, peak_tilt, peak_prob)

    def next_command(
        self,
        dt: float,
        current_pan_deg: float,
        current_tilt_deg: float,
    ) -> Tuple[float, float]:
        """
        Calculates commanded pan and tilt rates (deg/s) toward the peak of the belief map.
        """
        if self._completed or dt <= 0.0:
            return (0.0, 0.0)

        self._elapsed_time_s += dt
        if self._elapsed_time_s >= self.max_search_time_s:
            self._completed = True
            return (0.0, 0.0)

        # 1. Negative evidence discounting at current camera boresight
        self.discount_visited(current_pan_deg, current_tilt_deg, dt)

        # 2. Extract peak belief target
        target_pan, target_tilt, peak_prob = self.get_peak_location()

        # 3. Steering vector
        diff_pan = target_pan - current_pan_deg
        diff_tilt = target_tilt - current_tilt_deg
        dist = math.hypot(diff_pan, diff_tilt)

        # 4. Record history (subsample if long)
        if len(self._trajectory_history) == 0 or math.hypot(
            current_pan_deg - self._trajectory_history[-1][0],
            current_tilt_deg - self._trajectory_history[-1][1],
        ) >= 0.1:
            self._trajectory_history.append((current_pan_deg, current_tilt_deg))

        # Close proximity to current peak: accelerate discounting or allow smooth transition
        if dist < 0.05:
            return (0.0, 0.0)

        speed = min(self.scan_speed_deg_s, max(0.5, dist * 2.0))
        rate_pan = speed * (diff_pan / dist)
        rate_tilt = speed * (diff_tilt / dist)

        return (rate_pan, rate_tilt)

    def is_complete(self) -> bool:
        """Returns True if the search strategy has timed out or finished scanning."""
        return self._completed

    def get_trajectory_history(self) -> List[Tuple[float, float]]:
        """Returns recorded trajectory waypoints."""
        return list(self._trajectory_history)

    def get_belief_grid(self) -> np.ndarray:
        """Returns a copy of the 2D angular belief probability array."""
        return np.copy(self.belief_grid)
<<<<<<< HEAD
=======

>>>>>>> 92e2bd53912221253438c9725805b613c2bd2b21
