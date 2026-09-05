"""
Automated Engineering Validation Report Generator
=================================================
Generates reproducible, publication-grade markdown technical validation reports from raw trial datasets.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from analysis.aggregation import DistributionAggregator
from analysis.failures import FailureAnalyzer
from analysis.hypothesis import HypothesisTestingEngine
from analysis.validation import audit_trials_directory


class EngineeringReportGenerator:
    """Generates automated engineering reports from Phase 9 trial benchmark data."""

    def __init__(self, trials_dir: str | Path = "results/trials") -> None:
        self.trials_dir = Path(trials_dir)

    def generate_report(self, output_path: str | Path = "AUTOMATED_ENGINEERING_REPORT.md") -> str:
        """Generate markdown validation report and save to output_path."""
        audit_res = audit_trials_directory(self.trials_dir)
        valid_trials = audit_res.get("valid_trials", [])

        # Group trials by algorithm
        trials_by_alg: Dict[str, List[Dict[str, Any]]] = {}
        for t in valid_trials:
            alg = t.get("algorithm", "UNKNOWN").upper()
            trials_by_alg.setdefault(alg, []).append(t)

        aggregates_by_alg: Dict[str, Dict[str, Any]] = {}
        failures_by_alg: Dict[str, Dict[str, Any]] = {}
        errors_by_alg: Dict[str, List[float]] = {}

        for alg, t_list in trials_by_alg.items():
            aggregates_by_alg[alg] = DistributionAggregator.aggregate(t_list)
            failures_by_alg[alg] = FailureAnalyzer.analyze_trial_group(t_list)
            errors_by_alg[alg] = [t["metrics"].get("mean_tracking_error", 0.0) for t in t_list if "metrics" in t]

        # Hypothesis matrix
        hypo_res = HypothesisTestingEngine.evaluate_battlefield_matrix(errors_by_alg) if len(errors_by_alg) > 1 else {"pairwise_comparisons": []}

        # Build Markdown Document
        doc = []
        doc.append("# HORIZON COARSE-ALIGN-X — Automated Engineering Validation Report\n")
        doc.append("## Executive Summary & System Performance Matrix")
        doc.append(
            f"This scientific validation report presents the empirical benchmark evaluation across "
            f"**{audit_res['valid_count']} validated trials** (Audit Integrity: {audit_res['valid_count']}/{audit_res['total_files']} files passed).\n"
        )

        # Baseline Battlefield Comparison Table
        doc.append("### Baseline Battlefield Comparison Matrix")
        doc.append("| Algorithm | Success Rate (95% CI) | Lock Retention | Mean Error (px) | RMSE Error (px) | P95 Error (px) | Mean Latency (ms) |")
        doc.append("|---|---|---|---|---|---|---|")

        for alg in ["B0", "B1", "B2", "OURS"]:
            if alg in aggregates_by_alg:
                agg = aggregates_by_alg[alg]
                succ = f"{agg['success_rate']*100.0:.1f}% [{agg['success_rate_ci95'][0]*100.0:.1f}% - {agg['success_rate_ci95'][1]*100.0:.1f}%]"
                lock = f"{agg['lock_retention_rate']['mean']*100.0:.1f}%"
                mean_err = f"{agg['tracking_error']['mean']:.2f}"
                rmse_err = f"{agg['tracking_error']['rmse']:.2f}"
                p95_err = f"{agg['tracking_error']['p95']:.2f}"
                lat = f"{agg['latency_ms']['mean']:.2f} ms"
                doc.append(f"| **{alg}** | {succ} | {lock} | {mean_err} | {rmse_err} | {p95_err} | {lat} |")

        doc.append("\n---\n")

        # Statistical Hypothesis Superiority Table
        doc.append("### Pairwise Statistical Superiority & Effect Sizes")
        if hypo_res["pairwise_comparisons"]:
            doc.append("| Pairwise Comparison | Mean Diff (px) | P-Value (BH-FDR) | Cohen's d | Effect Size | Statistically Significant? |")
            doc.append("|---|---|---|---|---|---|")
            for comp in hypo_res["pairwise_comparisons"]:
                pair = comp["pair"]
                diff = f"{comp['delta_mean']:+.2f}"
                p_str = f"{comp.get('adjusted_p_value', 1.0):.4f}"
                d_str = f"{comp['cohens_d']:.2f}"
                eff = comp["effect_size_label"]
                sig = "YES" if comp.get("is_statistically_significant", False) else "NO"
                doc.append(f"| {pair} | {diff} | {p_str} | {d_str} | {eff} | **{sig}** |")
        else:
            doc.append("_Single algorithm evaluated; multi-baseline comparison requires at least 2 profile sets._\n")

        doc.append("\n---\n")

        # Failure Taxonomy Matrix
        doc.append("### Failure Mode Taxonomy Breakdown")
        doc.append("| Algorithm | Total Trials | Successes | Excessive Error | Track Loss | Rate Clamped Saturation | Overrun |")
        doc.append("|---|---|---|---|---|---|---|")
        for alg, fail_data in failures_by_alg.items():
            tot = fail_data["total_trials"]
            succ_cnt = fail_data["failure_counts"].get("SUCCESS", 0)
            exc_cnt = fail_data["failure_counts"].get("EXCESSIVE_ERROR", 0)
            loss_cnt = fail_data["failure_counts"].get("TRACK_LOSS", 0)
            sat_cnt = fail_data["failure_counts"].get("CONTROLLER_SATURATION", 0)
            overrun_cnt = fail_data["failure_counts"].get("PROCESSING_OVERRUN", 0)
            doc.append(f"| **{alg}** | {tot} | {succ_cnt} | {exc_cnt} | {loss_cnt} | {sat_cnt} | {overrun_cnt} |")

        doc.append("\n---\n")
        doc.append("## Reproducibility Statement")
        doc.append("All metrics, confidence intervals, and P-values in this document were generated automatically without human intervention or manual threshold editing.")

        report_content = "\n".join(doc)
        out_p = Path(output_path)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        with open(out_p, "w", encoding="utf-8") as f:
            f.write(report_content)

        return report_content
