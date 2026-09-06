"""
HORIZON Benchmark CLI Entry Point
=================================
Executes scientific benchmark experiments, fair baseline comparisons, and Monte Carlo runs.

Usage:
    python -m benchmark.run --algorithm ours --scenario severe --seed 42 --trials 10
    python -m benchmark.run --compare --algorithms b0 b1 b2 ours --trials 10 --parallel
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import List, Dict, Any

import numpy as np

from benchmark.metrics import compute_bootstrap_ci, compute_binomial_ci
from benchmark.profiles import ALGORITHMS, SCENARIO_PRESETS
from benchmark.robustness import RobustnessEnvelopeEngine
from benchmark.runner import BatchRunner, TrialResult
from benchmark.statistics import cohens_d, paired_bootstrap_test

logger = logging.getLogger("benchmark.run")


def print_comparison_table(summary_data: Dict[str, Any]) -> None:
    """Print formatted markdown comparison table to console."""
    headers = [
        "Algorithm",
        "Success Rate",
        "Lock Retention",
        "Mean Error (px)",
        "RMSE Error (px)",
        "P95 Error (px)",
        "Mean Latency (ms)",
    ]
    rows = []
    for alg, m in summary_data.items():
        succ = f"{m.get('success_rate', 0.0)*100.0:.1f}%"
        lock = f"{m.get('lock_retention_rate', 0.0)*100.0:.1f}%"
        mean_err = f"{m.get('mean_tracking_error', 0.0):.2f}"
        rmse_err = f"{m.get('RMSE_tracking_error', 0.0):.2f}"
        p95_err = f"{m.get('P95_tracking_error', 0.0):.2f}"
        lat = f"{m.get('processing_time_ms', 0.0):.2f}"
        rows.append([alg, succ, lock, mean_err, rmse_err, p95_err, lat])

    col_widths = [max(len(headers[i]), max(len(row[i]) for row in rows)) for i in range(len(headers))]
    
    header_str = " | ".join(h.ljust(col_widths[i]) for i, h in enumerate(headers))
    sep_str = "-|-".join("-" * col_widths[i] for i in range(len(headers)))

    print("\n" + "=" * 80)
    print("PHASE 9 BASELINE BATTLEFIELD BENCHMARK SUMMARY TABLE")
    print("=" * 80)
    print(header_str)
    print(sep_str)
    for row in rows:
        print(" | ".join(val.ljust(col_widths[i]) for i, val in enumerate(row)))
    print("=" * 80 + "\n")


def execute_fair_comparison(
    algorithms: List[str],
    scenario_id: str,
    master_seed: int,
    trials_count: int,
    duration: float,
    parallel: bool,
    output_dir: str,
) -> Dict[str, Any]:
    """Run fair comparison across multiple algorithms using IDENTICAL trial seeds."""
    runner = BatchRunner(output_dir=output_dir)
    results_by_alg: Dict[str, List[TrialResult]] = {}

    for alg in algorithms:
        logger.info("Executing algorithm profile: %s", alg)
        trials = runner.run_batch(
            algorithm=alg,
            scenario_id=scenario_id,
            master_seed=master_seed,
            trials_count=trials_count,
            duration=duration,
            parallel=parallel,
        )
        results_by_alg[alg] = trials

    # Aggregate metrics
    summary: Dict[str, Any] = {}
    distribution: Dict[str, Any] = {}

    for alg, trials in results_by_alg.items():
        successes = sum(1 for t in trials if t.success)
        total = len(trials)
        succ_rate, _, _ = compute_binomial_ci(successes, total)

        errors = [t.metrics.get("mean_tracking_error", 0.0) for t in trials]
        locks = [t.metrics.get("lock_retention_rate", 0.0) for t in trials]
        proc_times = [t.metrics.get("processing_time", 0.0) for t in trials]

        mean_err, err_lo, err_hi = compute_bootstrap_ci(errors, stat_fn="mean")
        rmse_err = float(np.sqrt(np.mean(np.asarray(errors)**2))) if errors else 0.0
        p95_err = float(np.percentile(errors, 95)) if errors else 0.0
        mean_lock = float(np.mean(locks)) if locks else 0.0
        mean_proc = float(np.mean(proc_times)) if proc_times else 0.0

        summary[alg] = {
            "success_rate": succ_rate,
            "success_count": successes,
            "total_trials": total,
            "mean_tracking_error": mean_err,
            "mean_tracking_error_ci95": [err_lo, err_hi],
            "RMSE_tracking_error": rmse_err,
            "P95_tracking_error": p95_err,
            "lock_retention_rate": mean_lock,
            "processing_time_ms": mean_proc,
        }

        distribution[alg] = {
            "tracking_errors": errors,
            "lock_retentions": locks,
            "processing_times": proc_times,
        }

    print_comparison_table(summary)

    # Export machine-readable artifacts
    out_path = Path(output_dir)
    comp_dir = out_path / "comparisons"
    comp_dir.mkdir(parents=True, exist_ok=True)

    with open(comp_dir / "comparison.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    with open(comp_dir / "distribution.json", "w", encoding="utf-8") as f:
        json.dump(distribution, f, indent=2)

    with open(comp_dir / "experiment_summary.json", "w", encoding="utf-8") as f:
        json.dump({
            "scenario": scenario_id,
            "master_seed": master_seed,
            "trials_count": trials_count,
            "summary": summary,
        }, f, indent=2)

    logger.info("Exported benchmark summaries to %s", comp_dir)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="HORIZON Phase 9 Benchmark Engine")
    parser.add_argument("--algorithm", type=str, default="ours", choices=["b0", "b1", "b2", "ours", "all"])
    parser.add_argument("--algorithms", nargs="+", default=["b0", "b1", "b2", "ours"], help="List of algorithms for --compare")
    parser.add_argument("--scenario", type=str, default="nominal", choices=list(SCENARIO_PRESETS.keys()))
    parser.add_argument("--seed", type=int, default=42, help="Master random seed")
    parser.add_argument("--trials", type=int, default=10, help="Number of Monte Carlo trials")
    parser.add_argument("--duration", type=float, default=10.0, help="Simulation duration per trial (seconds)")
    parser.add_argument("--compare", action="store_true", help="Run fair baseline comparison across algorithms")
    parser.add_argument("--parallel", action="store_true", help="Enable multi-process trial execution")
    parser.add_argument("--output-dir", type=str, default="results", help="Directory for storing results")

    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    if args.compare or args.algorithm == "all":
        algs = [a.upper() for a in args.algorithms]
        execute_fair_comparison(
            algorithms=algs,
            scenario_id=args.scenario,
            master_seed=args.seed,
            trials_count=args.trials,
            duration=args.duration,
            parallel=args.parallel,
            output_dir=args.output_dir,
        )
    else:
        alg = args.algorithm.upper()
        runner = BatchRunner(output_dir=args.output_dir)
        trials = runner.run_batch(
            algorithm=alg,
            scenario_id=args.scenario,
            master_seed=args.seed,
            trials_count=args.trials,
            duration=args.duration,
            parallel=args.parallel,
        )
        logger.info("Completed %d trials for algorithm %s.", len(trials), alg)


if __name__ == "__main__":
    main()
