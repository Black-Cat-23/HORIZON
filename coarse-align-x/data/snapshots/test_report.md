# HORIZON COARSE-ALIGN-X — Automated Engineering Validation Report

## Executive Summary & System Performance Matrix
This scientific validation report presents the empirical benchmark evaluation across **40 validated trials** (Audit Integrity: 40/40 files passed).

### Baseline Battlefield Comparison Matrix
| Algorithm | Success Rate (95% CI) | Lock Retention | Mean Error (px) | RMSE Error (px) | P95 Error (px) | Mean Latency (ms) |
|---|---|---|---|---|---|---|
| **B0** | 0.0% [0.0% - 27.8%] | 0.0% | 300.00 | 300.00 | 300.00 | 10.03 ms |
| **B1** | 0.0% [0.0% - 27.8%] | 54.0% | 78.95 | 79.20 | 85.53 | 8.59 ms |
| **B2** | 0.0% [0.0% - 27.8%] | 51.4% | 86.71 | 87.08 | 94.83 | 39.20 ms |
| **OURS** | 0.0% [0.0% - 27.8%] | 51.4% | 86.77 | 87.14 | 94.96 | 41.90 ms |

---

### Pairwise Statistical Superiority & Effect Sizes
| Pairwise Comparison | Mean Diff (px) | P-Value (BH-FDR) | Cohen's d | Effect Size | Statistically Significant? |
|---|---|---|---|---|---|
| B0 vs B1 | +221.05 | 0.0000 | 46.62 | Large | **YES** |
| B0 vs B2 | +213.29 | 0.0000 | 35.67 | Large | **YES** |
| B0 vs OURS | +213.23 | 0.0000 | 35.64 | Large | **YES** |
| B1 vs B2 | -7.76 | 0.0000 | -1.02 | Large | **YES** |
| B1 vs OURS | -7.83 | 0.0000 | -1.03 | Large | **YES** |
| B2 vs OURS | -0.06 | 0.0000 | -0.01 | Negligible | **YES** |

---

### Failure Mode Taxonomy Breakdown
| Algorithm | Total Trials | Successes | Excessive Error | Track Loss | Rate Clamped Saturation | Overrun |
|---|---|---|---|---|---|---|
| **B0** | 10 | 0 | 0 | 0 | 0 | 0 |
| **B1** | 10 | 0 | 10 | 0 | 0 | 0 |
| **B2** | 10 | 0 | 10 | 0 | 0 | 0 |
| **OURS** | 10 | 0 | 10 | 0 | 0 | 0 |

---

## Reproducibility Statement
All metrics, confidence intervals, and P-values in this document were generated automatically without human intervention or manual threshold editing.