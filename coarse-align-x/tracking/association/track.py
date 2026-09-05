"""
HORIZON Optical Target Track Lifecycle Manager
=====================================================
Encapsulates individual target track lifecycle, state estimation,
candidate association, and history tracking.

Strict Invariant: Zero access to true target position or ground-truth state.
"""

from __future__ import annotations

import logging
from typing import List, Optional, Tuple, Union
import numpy as np

from tracking.association.association import (
    AssociationResult,
    MeasurementCandidate,
    TrackAssociator,
)
from tracking.estimation.kalman import KalmanFilterConfig, TargetKalmanFilter
from tracking.estimation.state import EstimatorStatus, StateEstimate

logger = logging.getLogger(__name__)


class Track:
    """Optical target track manager encapsulating filter and association logic."""

    def __init__(
        self,
        track_id: int = 1,
        kalman_config: Optional[KalmanFilterConfig] = None,
        associator: Optional[TrackAssociator] = None,
    ) -> None:
        self._track_id = int(track_id)
        self._filter = TargetKalmanFilter(config=kalman_config)
        self._associator = associator or TrackAssociator(
            gate_threshold=self._filter.config.gate_chi2_threshold,
            base_sigma_px=self._filter.config.base_measurement_sigma_px,
        )
        self._last_estimate: Optional[StateEstimate] = None
        self._last_association: Optional[AssociationResult] = None

    @property
    def track_id(self) -> int:
        return self._track_id

    @property
    def filter(self) -> TargetKalmanFilter:
        return self._filter

    @property
    def associator(self) -> TrackAssociator:
        return self._associator

    @property
    def status(self) -> EstimatorStatus:
        return self._filter.status

    @property
    def last_estimate(self) -> Optional[StateEstimate]:
        return self._last_estimate

    @property
    def last_association(self) -> Optional[AssociationResult]:
        return self._last_association

    def step(
        self,
        measurement: Optional[Tuple[float, float]] = None,
        confidence: float = 1.0,
        timestamp: float = 0.0,
        candidates: Optional[List[MeasurementCandidate]] = None,
        gimbal_pan_rate: float = 0.0,
        gimbal_tilt_rate: float = 0.0,
    ) -> StateEstimate:
        """Process one tracking cycle.

        Args:
            measurement: Optional (u, v) measurement coordinate.
            confidence: Measurement confidence score in [0.0, 1.0].
            timestamp: Simulation timestamp in seconds.
            candidates: Optional list of all candidate detections for multi-candidate association.
            gimbal_pan_rate: Camera pan rate in deg/s.
            gimbal_tilt_rate: Camera tilt rate in deg/s.

        Returns:
            StateEstimate output.
        """
        # Case 1: Multi-candidate association enabled
        if candidates is not None and len(candidates) > 0:
            if not self._filter.is_initialized:
                # Initialize with highest confidence candidate
                best_cand = max(candidates, key=lambda c: c.confidence)
                estimate = self._filter.initialize(
                    measurement=best_cand.centroid,
                    timestamp=timestamp,
                )
                self._last_association = AssociationResult(
                    associated=True,
                    selected_candidate=best_cand,
                    rejected_candidates=[c for c in candidates if c != best_cand],
                    all_candidates_count=len(candidates),
                )
                self._last_estimate = estimate
                return estimate

            # Predict first to obtain predicted state for gating
            assert self._filter.state_vector is not None
            dt = max(1e-4, timestamp - self._filter._last_timestamp)
            x_pred, P_pred = self._filter.predict(dt, gimbal_pan_rate, gimbal_tilt_rate)

            assoc_res = self._associator.associate(candidates, x_pred, P_pred)
            self._last_association = assoc_res

            if assoc_res.associated and assoc_res.selected_candidate is not None:
                cand = assoc_res.selected_candidate
                estimate = self._filter.update(
                    measurement=cand.centroid,
                    confidence=cand.confidence,
                    timestamp=timestamp,
                    gimbal_pan_rate=gimbal_pan_rate,
                    gimbal_tilt_rate=gimbal_tilt_rate,
                )
            else:
                # All candidates gated out: missing/coasting update
                estimate = self._filter.update_missing(timestamp=timestamp)

            self._last_estimate = estimate
            return estimate

        # Case 2: Single measurement or explicit missing observation
        if measurement is not None:
            estimate = self._filter.update(
                measurement=measurement,
                confidence=confidence,
                timestamp=timestamp,
                gimbal_pan_rate=gimbal_pan_rate,
                gimbal_tilt_rate=gimbal_tilt_rate,
            )
            self._last_association = None
        else:
            estimate = self._filter.update_missing(timestamp=timestamp)
            self._last_association = None

        self._last_estimate = estimate
        return estimate

    def reset(self) -> None:
        """Reset the track and associated filter."""
        self._filter.reset()
        self._last_estimate = None
        self._last_association = None
