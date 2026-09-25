# PHASE 5 STATE ESTIMATION ENGINE REPORT

**Project:** HORIZON (SIH26169)  
**Subsystem:** 3-Model IMM-EKF Uncertainty-Aware Estimator Engine  
**Date:** 2026-09-08  
**Status:** IMPLEMENTED & VERIFIED — ZERO GROUND-TRUTH LEAKAGE  

---

## 1. 3-Model IMM Architecture

The Phase 5 estimator incorporates 3 specialized motion models running in parallel:

1. **Constant Velocity (CV) Filter ($\sigma_a = 200.0\text{ px/s}^2$):** Low-noise kinematic drift during smooth tracking.
2. **Constant Acceleration (CA) Filter ($\sigma_a = 800.0\text{ px/s}^2$):** Steady velocity changes and maneuvering.
3. **Sudden Maneuver Filter ($\sigma_a = 2500.0\text{ px/s}^2$):** Rapid dynamic turns, high-speed directional changes, and platform swing steps.

### Markov Chain Transition Matrix $\mathbf{\Pi} \in \mathbb{R}^{3 \times 3}$
$$\mathbf{\Pi} = \begin{bmatrix} 0.92 & 0.05 & 0.03 \\ 0.08 & 0.87 & 0.05 \\ 0.05 & 0.15 & 0.80 \end{bmatrix}$$

---

## 2. Statistical Metrics & Diagnostics

* **Normalized Innovation Squared (NIS):** $\text{NIS}_k = \boldsymbol{\nu}_k^T \mathbf{S}_k^{-1} \boldsymbol{\nu}_k$ monitored continuously for statistical filter consistency.
* **NEES Evaluation (Evaluation-Only):** $\text{NEES}_k = (\mathbf{x}_{\text{true}} - \hat{\mathbf{x}}_k)^T \mathbf{P}_k^{-1} (\mathbf{x}_{\text{true}} - \hat{\mathbf{x}}_k)$ evaluated offline against ground truth. Zero influence on operational filter state or control laws.
* **Covariance Integrity:** Enforces finite numerical checks, symmetry $\mathbf{P} = \frac{1}{2}(\mathbf{P} + \mathbf{P}^T)$, and positive-semidefinite eigenvalue floor ($\lambda_{\min} \ge 10^{-6}$).
* **Estimator Health Object:** Assembles `EstimatorHealth` record containing NIS, NEES, position $\sigma$, velocity $\sigma$, model probabilities, and gating decisions.
