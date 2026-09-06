# HORIZON Phase 10 — Statistical Methods Reference

## Overview
This document specifies the mathematical and statistical formulations implemented in `analysis/statistics/` for Phase 10 validation.

---

## 1. Proportions & Binary Metrics
- **Metric**: Success rate, lock retention rate.
- **Formulation**: Wilson Score 95% Confidence Interval:
  $$\text{Centre} = \frac{p + \frac{z^2}{2n}}{1 + \frac{z^2}{n}}, \quad \text{Spread} = \frac{z}{1 + \frac{z^2}{n}} \sqrt{\frac{p(1-p)}{n} + \frac{z^2}{4n^2}}$$
  where $z = 1.96$ for a 95% confidence level.

---

## 2. Continuous Metric Confidence Intervals
- **Method**: Non-parametric Deterministic Bootstrap.
- **Parameters**: 1,000 resamples, deterministic seed ($S=42$).
- **Percentile Method**: 2.5th and 97.5th percentiles of the empirical resampled mean distribution.

---

## 3. Seed-Matched Paired Comparisons
- **Method**: Paired Bootstrap Difference Test & Wilcoxon Signed-Rank Test.
- **Difference Formulation**: $\Delta_i = x_{\text{OURS}, i} - x_{B1, i}$ for identical trial seed $i$.
- **Hypothesis**: $H_0: \Delta = 0$ vs. $H_1: \Delta < 0$ (reduction in tracking error).

---

## 4. Standardized Effect Sizes
- **Cohen's $d$**:
  $$d = \frac{\bar{x}_1 - \bar{x}_2}{s_{\text{pooled}}}, \quad s_{\text{pooled}} = \sqrt{\frac{(n_1-1)s_1^2 + (n_2-1)s_2^2}{n_1 + n_2 - 2}}$$
  - $|d| < 0.2$: Negligible
  - $0.2 \leq |d| < 0.5$: Small
  - $0.5 \leq |d| < 0.8$: Medium
  - $|d| \geq 0.8$: Large
- **Cliff's $\delta$**: Non-parametric dominance metric evaluating sample orderings without normality assumptions.

---

## 5. Multiple Comparison Correction
- **Procedure**: Benjamini-Hochberg False Discovery Rate (FDR) control at $\alpha = 0.05$.
- **Formulation**: Adjusted P-values $P_{(i)}^{\text{adj}} = \min_{j \geq i} \left( \min \left( 1, P_{(j)} \frac{m}{j} \right) \right)$ for $m$ hypothesis tests.
