"""
HORIZON Ground-Truth Leakage Invariant Guard
=============================================
Strict runtime structural inspector and call stack guard ensuring zero ground-truth variables
(`true_x`, `true_y`, `true_vx`, `true_vy`) leak into online perception, data association,
or Kalman estimator step functions.

Strict Invariant: Ground truth is used STRICTLY for post-hoc metric evaluation.
"""

from __future__ import annotations

import inspect
import logging
from typing import Any, Callable, Dict, List

logger = logging.getLogger(__name__)

FORBIDDEN_GROUND_TRUTH_KEYS = {"true_x", "true_y", "true_vx", "true_vy", "gt_x", "gt_y", "gt_vx", "gt_vy"}


class GroundTruthInvariantGuard:
    """Runtime inspector guarding online modules against ground-truth data leakage."""

    @staticmethod
    def verify_no_ground_truth_in_kwargs(kwargs: Dict[str, Any], caller_name: str = "online_step") -> bool:
        """Inspect kwarg parameter dictionary for forbidden ground-truth keys.

        Args:
            kwargs: Dictionary of arguments passed to function.
            caller_name: Name of caller function for logging.

        Raises:
            ValueError if any ground-truth key is passed into an online processing call.

        Returns:
            True if clean.
        """
        leaked_keys = FORBIDDEN_GROUND_TRUTH_KEYS.intersection(kwargs.keys())
        if leaked_keys:
            msg = f"[CRITICAL LEAKAGE DETECTED] Ground-truth parameter(s) {leaked_keys} passed to online module function '{caller_name}'"
            logger.critical(msg)
            raise ValueError(msg)
        return True

    @staticmethod
    def audit_online_call_stack() -> bool:
        """Inspect current python call stack frames to verify no ground-truth object is accessed."""
        stack = inspect.stack()
        for frame_info in stack:
            mod_name = frame_info.frame.f_globals.get("__name__", "")
            if "tracking.estimation" in mod_name or "simulator.perception" in mod_name or "tracking.association" in mod_name:
                locs = frame_info.frame.f_locals
                leaked = FORBIDDEN_GROUND_TRUTH_KEYS.intersection(locs.keys())
                if leaked:
                    msg = f"[CRITICAL LEAKAGE DETECTED] Ground-truth variable(s) {leaked} found in local frame of '{mod_name}'"
                    logger.critical(msg)
                    raise ValueError(msg)
        return True
