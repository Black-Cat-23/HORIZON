# HORIZON Phase 10 — Analysis Protocol

## Overview
This document specifies the scientific analysis protocol for HORIZON Phase 10 validation. It defines trial data auditing rules, validity state taxonomy, metric aggregation standards, robustness envelope classification, and automated reporting rules.

---

## 1. Immutable Data Principle
- Benchmark outputs saved in `results/trials/` are immutable source evidence.
- The analysis pipeline NEVER modifies, overwrites, or deletes original raw trial files.
- All derived datasets, statistics, and tables are stored separately in `analysis/aggregates/`, `analysis/statistics/`, and `analysis/reporting/`.

---

## 2. Trial Validity State Taxonomy
Every trial evaluated by `ResultValidator` is assigned one of the following explicit validity states:
- `VALID`: Complete schema, finite metrics, valid execution.
- `FAILED_RUNTIME`: Simulation runtime exception recorded.
- `INVALID_DATA`: Missing required schema fields or non-finite numbers (NaN/Inf).
- `INCOMPLETE`: Execution interrupted prior to duration completion.
- `EXCLUDED_WITH_REASON`: Explicitly audited exclusion with documented root-cause metadata.

---

## 3. Data Integrity & Anti-Cherry-Picking Rules
- No silent trial exclusion. Every trial evaluated in the benchmark suite MUST be accounted for in the distribution statistics.
- Outliers are NOT removed automatically. Numerical extremes resulting from severe disturbance conditions remain in the empirical distribution.
- All metrics, P-values, confidence intervals, and tables are generated programmatically without manual threshold editing.

---

## 4. Multi-Level Evaluation Pipeline
1. **Result Validation**: Schema integrity, NaN/Inf checks, duplicate detection.
2. **Distribution Aggregation**: Means, medians, std, min, max, $P_{50}, P_{95}, P_{99}$ percentiles.
3. **Statistical Hypothesis Testing**: Seed-matched paired bootstrap tests, Wilcoxon signed-rank tests, Cohen's $d$, Cliff's $\delta$, Benjamini-Hochberg FDR control ($\alpha=0.05$).
4. **Robustness Envelope**: 2D parameter heatmaps categorized into `STABLE`, `DEGRADED`, and `FAILURE` operational regions.
5. **Failure Mode Taxonomy**: Categorizes failures into 9 taxonomy modes with Pareto ranking.
6. **Component & Feature Ablation**: Component steps A–E evaluation and feature toggle impact analysis.
7. **Accuracy vs. Latency Trade-Off**: Non-dominated Pareto frontier calculation.
8. **Automated Report Generation**: Programmatic Markdown and HTML report generation.
