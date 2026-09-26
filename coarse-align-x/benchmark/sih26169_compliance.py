"""
HORIZON ISRO SIH26169 Standard Compliance Benchmarking Suite
============================================================
Evaluates tracking metrics against ISRO SIH26169 Problem Statement targets:
  1. Acquisition Latency: t_acq <= 0.50 s
  2. Re-acquisition Latency: t_reacq <= 0.20 s
  3. Pointing Error RMS: RMSE_pos <= 0.50 px
  4. Pointing Jitter RMS: sigma_jitter <= 0.10 px
  5. Lock Retention Rate: LRR >= 98.0%
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict


@dataclass(frozen=True)
class SIH26169ComplianceReport:
    """ISRO SIH26169 Benchmark Compliance Audit Report."""
    is_fully_compliant: bool
    acquisition_latency_s: float
    acquisition_compliant: bool
    reacquisition_latency_s: float
    reacquisition_compliant: bool
    pointing_rmse_px: float
    pointing_rmse_compliant: bool
    pointing_jitter_px: float
    jitter_compliant: bool
    lock_retention_rate_pct: float
    lock_retention_compliant: bool


class SIH26169ComplianceEvaluator:
    """Evaluates trial performance metrics against ISRO SIH26169 PS targets."""

    @staticmethod
    def evaluate_trial_metrics(metrics: Dict[str, Any]) -> SIH26169ComplianceReport:
        """Audit trial metrics dictionary against ISRO SIH26169 compliance bounds.

        Args:
            metrics: Dictionary of trial metrics returned by MetricEngine.evaluate_telemetry.

        Returns:
            SIH26169ComplianceReport container.
        """
        acq_t = float(metrics.get("acquisition_time") or 0.0)
        reacq_t = float(metrics.get("reacquisition_time") or 0.0)
        pos_rmse = float(metrics.get("RMSE_tracking_error", 0.0))

        # Estimate pointing jitter RMS from P95 - Median spread
        p95_err = float(metrics.get("P95_tracking_error", 0.0))
        med_err = float(metrics.get("median_tracking_error", 0.0))
        jitter_rms = float(max(0.0, (p95_err - med_err) / 1.645))

        lrr_pct = float(metrics.get("lock_retention_rate", 0.0)) * 100.0

        acq_ok = (acq_t <= 0.50)
        reacq_ok = (reacq_t <= 0.20)
        rmse_ok = (pos_rmse <= 0.50)
        jitter_ok = (jitter_rms <= 0.10)
        lrr_ok = (lrr_pct >= 98.0)

        overall_ok = (acq_ok and reacq_ok and rmse_ok and jitter_ok and lrr_ok)

        return SIH26169ComplianceReport(
            is_fully_compliant=overall_ok,
            acquisition_latency_s=acq_t,
            acquisition_compliant=acq_ok,
            reacquisition_latency_s=reacq_t,
            reacquisition_compliant=reacq_ok,
            pointing_rmse_px=pos_rmse,
            pointing_rmse_compliant=rmse_ok,
            pointing_jitter_px=jitter_rms,
            jitter_compliant=jitter_ok,
            lock_retention_rate_pct=lrr_pct,
            lock_retention_compliant=lrr_ok,
        )
