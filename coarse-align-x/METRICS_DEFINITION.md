# HORIZON Phase 9 — Metrics Definition

## Overview
This document formally defines every metric calculated by the HORIZON `MetricEngine`, including mathematical formulas, telemetry sources, measurement units, and boundary conditions.

---

## 1. Timing & Processing Metrics

### 1.1 Processing Time
- **Formula**: $T_{\text{proc}} = t_{\text{end}} - t_{\text{start}}$ per frame (ms).
- **Units**: milliseconds (ms).
- **Source**: High-resolution performance counter in `run_single_trial`.
- **Aggregation**: Mean and 95th Percentile ($P_{95}$).

### 1.2 Frames Per Second (FPS)
- **Formula**: $\text{FPS} = \frac{1000}{T_{\text{proc\_ms}}}$.
- **Units**: Hz / frames per second.
- **Aggregation**: Average and Minimum.

---

## 2. Acquisition & Reacquisition Metrics

### 2.1 Acquisition Time
- **Formula**: $T_{\text{acq}} = t_{\text{first\_TRACK}} - t_{\text{experiment\_start}}$.
- **Units**: seconds (s).
- **Source**: PAT state machine mode transition telemetry.
- **Boundary Behavior**: `None` if `TRACK` state is never achieved.

### 2.2 Reacquisition Time
- **Formula**: $T_{\text{reacq}} = t_{\text{restored\_TRACK}} - t_{\text{loss\_start}}$.
- **Units**: seconds (s).
- **Source**: Transition from `LOST`/`REACQUIRE` back to `TRACK`.
- **Aggregation**: Median and $P_{95}$.

---

## 3. Tracking Error Metrics

### 3.1 Pixel Tracking Error
- **Formula**: 
  $$e_k = \sqrt{(\hat{x}_k - x^*_k)^2 + (\hat{y}_k - y^*_k)^2}$$
  where $(\hat{x}_k, \hat{y}_k)$ is the estimated position and $(x^*_k, y^*_k)$ is ground truth.
- **Units**: pixels (px).
- **Aggregation**: Mean, Median ($P_{50}$), RMSE, $P_{95}$, $P_{99}$, Maximum.

### 3.2 Angular Tracking Error
- **Formula**: 
  $$e_{\text{angular}} = e_k \times \frac{\text{FOV}_{\text{rad}}}{\text{sensor\_width\_px}}$$
- **Units**: radians / microradians ($\mu\text{rad}$).

---

## 4. Lock Retention Rate
- **Formula**: 
  $$\text{LockRetention} = \frac{T_{\text{TRACK}}}{T_{\text{eligible}}}$$
  where $T_{\text{eligible}} = T_{\text{total}} - T_{\text{acq}}$.
- **Units**: Dimensionless ratio $[0.0, 1.0]$ or percentage ($\%$).
- **Confidence Interval**: Wilson Score 95% Binomial Interval.
