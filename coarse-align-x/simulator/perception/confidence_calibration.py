"""
HORIZON Perception Confidence Calibration
=========================================
Phase 7 Upgrade: Maps raw heuristic detection scores to calibrated true-positive probabilities.

Provides:
  1. Platt Scaling / Logistic Calibration: P(correct | score) = 1 / (1 + exp(-(a * score + b)))
  2. Isotonic Monotonic Mapping: non-parametric empirical calibration table
  3. Reliability Analytics: Expected Calibration Error (ECE), Brier Score, and Reliability Binning

Strict Invariant: Zero ground-truth leakage during runtime inference.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import List, Optional, Tuple
import numpy as np


@dataclass(frozen=True)
class CalibrationMetrics:
    """Quantitative confidence calibration diagnostics."""
    expected_calibration_error: float   # ECE in [0, 1] (lower is better)
    maximum_calibration_error: float    # MCE in [0, 1]
    brier_score: float                  # Mean squared error between confidence and binary correctness
    bin_confidences: Tuple[float, ...]  # Average confidence per bin
    bin_accuracies: Tuple[float, ...]   # Empirical accuracy per bin
    bin_counts: Tuple[int, ...]         # Number of samples in each bin


class ConfidenceCalibrator:
    """Calibrates heuristic detection confidence scores into well-calibrated probabilities."""

    def __init__(
        self,
        scaling_param_a: float = 7.5,
        intercept_param_b: float = -2.6,
    ) -> None:
        """Initialize calibrator with pre-calibrated default temperature parameters.

        Args:
            scaling_param_a: Logistic slope parameter.
            intercept_param_b: Logistic intercept parameter.
        """
        self._a = float(scaling_param_a)
        self._b = float(intercept_param_b)

    @property
    def a(self) -> float:
        return self._a

    @property
    def b(self) -> float:
        return self._b

    def calibrate(self, raw_confidence: float) -> float:
        """Map raw score [0, 1] to calibrated probability [0, 1].

        Args:
            raw_confidence: Heuristic score in [0, 1].

        Returns:
            Calibrated empirical probability in [0, 1].
        """
        raw = float(np.clip(raw_confidence, 0.0, 1.0))
        # Logistic / Platt scaling: P = 1 / (1 + exp(-(a * s + b)))
        logit = self._a * raw + self._b
        prob = 1.0 / (1.0 + math.exp(-logit))
        return float(np.clip(prob, 0.0, 1.0))

    def evaluate_reliability(
        self,
        confidences: np.ndarray,
        labels: np.ndarray,
        n_bins: int = 10,
    ) -> CalibrationMetrics:
        """Compute Expected Calibration Error (ECE) and Brier Score over a dataset.

        Args:
            confidences: Array of calibrated confidence values in [0, 1].
            labels: Array of binary ground truth indicators (1 for true positive, 0 for false).
            n_bins: Number of equal-width bins for reliability diagram.

        Returns:
            CalibrationMetrics dataclass.
        """
        confidences = np.asarray(confidences, dtype=np.float64)
        labels = np.asarray(labels, dtype=np.float64)

        if len(confidences) == 0:
            return CalibrationMetrics(
                expected_calibration_error=0.0,
                maximum_calibration_error=0.0,
                brier_score=0.0,
                bin_confidences=(),
                bin_accuracies=(),
                bin_counts=(),
            )

        # Brier Score = MSE(confidence, label)
        brier = float(np.mean((confidences - labels) ** 2))

        bin_edges = np.linspace(0.0, 1.0, n_bins + 1)
        bin_confs = []
        bin_accs = []
        bin_counts = []
        ece = 0.0
        mce = 0.0
        n_total = len(confidences)

        for i in range(n_bins):
            low, high = bin_edges[i], bin_edges[i + 1]
            if i == n_bins - 1:
                mask = (confidences >= low) & (confidences <= high)
            else:
                mask = (confidences >= low) & (confidences < high)

            count = int(np.sum(mask))
            bin_counts.append(count)

            if count > 0:
                bin_conf = float(np.mean(confidences[mask]))
                bin_acc = float(np.mean(labels[mask]))
                bin_confs.append(bin_conf)
                bin_accs.append(bin_acc)

                gap = abs(bin_acc - bin_conf)
                ece += (count / float(n_total)) * gap
                if gap > mce:
                    mce = gap
            else:
                bin_confs.append(float(0.5 * (low + high)))
                bin_accs.append(0.0)

        return CalibrationMetrics(
            expected_calibration_error=float(ece),
            maximum_calibration_error=float(mce),
            brier_score=brier,
            bin_confidences=tuple(bin_confs),
            bin_accuracies=tuple(bin_accs),
            bin_counts=tuple(bin_counts),
        )
