# HORIZON PHASE 10 EXISTING VALIDATION UPGRADE REPORT

## Step 1 — Data Integrity Audit Summary
- **Total Trial Files Inspected:** 43
- **Validated Trials:** 40
- **Corrupted / Invalid Files:** 3
- **Duplicate Trial Seeds:** 2
- **Incomplete Trials:** 0
- **Configuration Mismatches:** 0

## Step 2 — Full Metric Distributions (P50, P95, P99, Max)
| Algorithm | Success Rate | Lock Retention | Mean Error | Median (P50) | P95 Error | P99 Error | Max Error | Mean Latency |
|---|---|---|---|---|---|---|---|---|
| **B0** | 0.0% | 0.0% | 300.00 px | 300.00 px | 300.00 px | 300.00 px | 300.00 px | 10.03 ms |
| **B1** | 0.0% | 54.0% | 78.95 px | 79.15 px | 85.53 px | 85.56 px | 85.56 px | 8.59 ms |
| **B2** | 0.0% | 51.4% | 86.71 px | 87.43 px | 94.83 px | 94.86 px | 94.86 px | 39.20 ms |
| **OURS** | 0.0% | 51.4% | 86.77 px | 87.45 px | 94.96 px | 94.97 px | 94.97 px | 41.90 ms |

---

## Step 3 & 4 — Seed-Matched Differences & Non-Parametric Statistics
| Pairwise Comparison | Mean Delta | Test Method | P-Value (BH-FDR) | Cohen's d | Vargha-Delaney A12 | Significant? |
|---|---|---|---|---|---|---|
| B0 vs B1 | +221.05 px | Paired Wilcoxon Signed-Rank (Non-Parametric) | 0.0061 | 46.62 | 1.00 | **YES** |
| B0 vs B2 | +213.29 px | Paired Wilcoxon Signed-Rank (Non-Parametric) | 0.0061 | 35.67 | 1.00 | **YES** |
| B0 vs OURS | +213.23 px | Paired Wilcoxon Signed-Rank (Non-Parametric) | 0.0061 | 35.64 | 1.00 | **YES** |
| B1 vs B2 | -7.76 px | Paired Wilcoxon Signed-Rank (Non-Parametric) | 0.0061 | -1.02 | 0.25 | **YES** |
| B1 vs OURS | -7.83 px | Paired Wilcoxon Signed-Rank (Non-Parametric) | 0.0061 | -1.03 | 0.25 | **YES** |
| B2 vs OURS | -0.06 px | Paired Wilcoxon Signed-Rank (Non-Parametric) | 0.0218 | -0.01 | 0.45 | **YES** |

---

## Step 7 — Subsystem Telemetry Failure Forensics
| Algorithm | Total Trials | Perception | Association | Estimation | PAT | Control | Computation | Unknown |
|---|---|---|---|---|---|---|---|---|
| **B0** | 10 | 0 | 0 | 0 | 10 | 0 | 0 | 0 |
| **B1** | 10 | 0 | 0 | 5 | 5 | 0 | 0 | 0 |
| **B2** | 10 | 0 | 0 | 0 | 0 | 0 | 10 | 0 |
| **OURS** | 10 | 0 | 0 | 0 | 0 | 0 | 10 | 0 |

---

## Step 10 — Accuracy / Latency Trade-off Pareto Frontier
**Pareto Frontier Optimal Algorithms:** `B1`

<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 500 300' width='100%' height='280' style='background:#18181b; border-radius:8px; border:1px solid #27272a;'>
<text x='250.0' y='25' fill='#f4f4f5' font-family='sans-serif' font-size='14' font-weight='bold' text-anchor='middle'>Accuracy vs Latency Pareto Curve</text>
<line x1='60' y1='260' x2='440' y2='260' stroke='#52525b' stroke-width='1.5'/>
<line x1='60' y1='40' x2='60' y2='260' stroke='#52525b' stroke-width='1.5'/>
<text x='250.0' y='290' fill='#a1a1aa' font-family='sans-serif' font-size='11' text-anchor='middle'>Latency (ms)</text>
<text x='15' y='150.0' fill='#a1a1aa' font-family='sans-serif' font-size='11' text-anchor='middle' transform='rotate(-90 15 150.0)'>Accuracy</text>
<circle cx='135.8' cy='259.3' r='7' fill='#ef4444' stroke='#ffffff' stroke-width='1.5'/>
<text x='145.8' y='263.3' fill='#f4f4f5' font-family='sans-serif' font-size='12' font-weight='600'>B0 (10.0ms, 0.3)</text>
<circle cx='124.9' cy='258.5' r='7' fill='#f59e0b' stroke='#ffffff' stroke-width='1.5'/>
<text x='134.9' y='262.5' fill='#f4f4f5' font-family='sans-serif' font-size='12' font-weight='600'>B1 (8.6ms, 0.8)</text>
<circle cx='356.2' cy='258.6' r='7' fill='#3b82f6' stroke='#ffffff' stroke-width='1.5'/>
<text x='366.2' y='262.6' fill='#f4f4f5' font-family='sans-serif' font-size='12' font-weight='600'>B2 (39.2ms, 0.7)</text>
<circle cx='376.7' cy='258.6' r='7' fill='#10b981' stroke='#ffffff' stroke-width='1.5'/>
<text x='386.7' y='262.6' fill='#f4f4f5' font-family='sans-serif' font-size='12' font-weight='600'>OURS (41.9ms, 0.7)</text>
</svg>

---

## Step 12 — Claim Traceability Matrix
### Empirical Claim Traceability Matrix
| Claim ID | Value | Experiment ID | Seed | Scenario | Metric | Analysis Method |
|---|---|---|---|---|---|---|
| `B0_MEAN_ERR` | **300.00 px** | `BENCHMARK_SUITE_P9` | `AGGREGATED_ALL` | `ALL_COMBINED` | `mean_tracking_error` | `Bootstrap Mean (N=1000)` |
| `B0_P95_ERR` | **300.00 px** | `BENCHMARK_SUITE_P9` | `AGGREGATED_ALL` | `ALL_COMBINED` | `P95_tracking_error` | `Percentile P95` |
| `B0_LATENCY` | **10.03 ms** | `BENCHMARK_SUITE_P9` | `AGGREGATED_ALL` | `ALL_COMBINED` | `processing_time` | `Sample Mean` |
| `B1_MEAN_ERR` | **78.95 px** | `BENCHMARK_SUITE_P9` | `AGGREGATED_ALL` | `ALL_COMBINED` | `mean_tracking_error` | `Bootstrap Mean (N=1000)` |
| `B1_P95_ERR` | **85.53 px** | `BENCHMARK_SUITE_P9` | `AGGREGATED_ALL` | `ALL_COMBINED` | `P95_tracking_error` | `Percentile P95` |
| `B1_LATENCY` | **8.59 ms** | `BENCHMARK_SUITE_P9` | `AGGREGATED_ALL` | `ALL_COMBINED` | `processing_time` | `Sample Mean` |
| `B2_MEAN_ERR` | **86.71 px** | `BENCHMARK_SUITE_P9` | `AGGREGATED_ALL` | `ALL_COMBINED` | `mean_tracking_error` | `Bootstrap Mean (N=1000)` |
| `B2_P95_ERR` | **94.83 px** | `BENCHMARK_SUITE_P9` | `AGGREGATED_ALL` | `ALL_COMBINED` | `P95_tracking_error` | `Percentile P95` |
| `B2_LATENCY` | **39.20 ms** | `BENCHMARK_SUITE_P9` | `AGGREGATED_ALL` | `ALL_COMBINED` | `processing_time` | `Sample Mean` |
| `OURS_MEAN_ERR` | **86.77 px** | `BENCHMARK_SUITE_P9` | `AGGREGATED_ALL` | `ALL_COMBINED` | `mean_tracking_error` | `Bootstrap Mean (N=1000)` |
| `OURS_P95_ERR` | **94.96 px** | `BENCHMARK_SUITE_P9` | `AGGREGATED_ALL` | `ALL_COMBINED` | `P95_tracking_error` | `Percentile P95` |
| `OURS_LATENCY` | **41.90 ms** | `BENCHMARK_SUITE_P9` | `AGGREGATED_ALL` | `ALL_COMBINED` | `processing_time` | `Sample Mean` |

---

## Step 11 & 14 — Reproducibility Statement & Scientific Integrity Guardrails
- **Reproducibility:** All benchmark results are generated deterministically from seed-matched simulator scenarios.
- **Anti-Marketing Linter:** Automated guardrail check passed. Zero unsubstantiated adjectives (top-ranked, dominant, leading-class, state-of-the-practice) detected.