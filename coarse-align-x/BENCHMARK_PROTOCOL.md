# HORIZON Phase 9 — Benchmark Protocol

## Overview
This document specifies the scientific benchmark protocol for HORIZON Phase 9. It defines algorithm profiles, immutable manifests, seed generation policies, fairness rules, failure taxonomy, and statistical methods.

---

## 1. Algorithm Profiles
- **B0 (Naive Baseline)**: Open-loop baseline with zero active camera feedback (static gaze at sensor center).
- **B1 (Classical Baseline)**: Classical intensity-threshold perception (`ClassicalBeaconDetector`) + Constant-Velocity Kalman Filter + Closed-Loop PAT Camera Controller.
- **B2 (Neural Baseline)**: YOLOv8n FP32 ONNX neural perception (`NeuralBeaconDetector`) + Constant-Velocity Kalman Filter + Closed-Loop PAT Camera Controller.
- **OURS (Hybrid System)**: Hybrid perception engine (`HybridBeaconDetector` with YOLOv8 proposal + optical CoG Gaussian subpixel refinement + covariance fusion) + Constant-Velocity Kalman Filter + Closed-Loop PAT Camera Controller.

---

## 2. Seed Policy & Determinism
- Master random seed $S_{\text{master}}$ decomposes into unique trial seeds using SHA-256:
  $$\text{Seed}_{\text{trial}} = \text{SHA256}(S_{\text{master}} \,||\, \text{scenario\_id} \,||\, \text{trial\_index}) \pmod{2^{31}-1}$$
- Clock time is strictly forbidden as a random seed source.
- All algorithms ($B_0, B_1, B_2, \text{OURS}$) in a comparative benchmark MUST evaluate identical trial seeds.

---

## 3. Fairness Rules
- Identical initial target position and velocity.
- Identical virtual camera intrinsics ($640 \times 480$, $\text{FOV}_x = 4^\circ$, $\text{FOV}_y = 3^\circ$, $30\text{ Hz}$).
- Identical disturbance pipeline seeds (Gaussian noise, Salt & Pepper, Camera Jitter, Atmospheric haze).
- Zero ground-truth leakage into detector or estimator logic. Ground truth is used strictly post-hoc for metric calculation.

---

## 4. Failure Taxonomy
1. `NO_ACQUISITION`: Target failed to achieve `TRACK` mode during simulation.
2. `TRACK_LOSS`: Target lost and unrecovered before simulation termination.
3. `REACQUISITION_TIMEOUT`: Reacquisition phase exceeded timeout.
4. `EXCESSIVE_ERROR`: Mean tracking error exceeded maximum error envelope ($>50\text{ px}$).
5. `CONTROLLER_SATURATION`: Gimbal rate limits saturated for $>20\%$ of frames.
6. `PROCESSING_OVERRUN`: Frame processing latency exceeded frame interval ($>50\text{ ms}$).
7. `INVALID_OUTPUT`: Detector returned non-finite centroid coordinates.
8. `RUNTIME_ERROR`: Simulation exception thrown during execution.

---

## 5. Statistical Methods
- **Proportions**: Wilson Score 95% Confidence Interval.
- **Continuous Metrics**: Non-parametric Bootstrap (1,000 resamples).
- **Paired Comparisons**: Wilcoxon signed-rank test and paired bootstrap test.
- **Effect Size**: Cohen's $d$ and Cliff's $\delta$.
- **Multiple Comparisons**: Benjamini-Hochberg False Discovery Rate (FDR) procedure ($\alpha = 0.05$).
