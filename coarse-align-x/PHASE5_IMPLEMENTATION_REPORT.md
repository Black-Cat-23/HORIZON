# HORIZON Phase 5 — Implementation & Verification Report
**SIH26169: AI-Based Virtual Camera Tracking System for Coarse Alignment of Mobile FSOC Terminals**

---

## 1. System Architecture
Phase 5 implements the target state estimation and association subsystem, completing the pipeline:

$$\text{WORLD} \longrightarrow \text{CAMERA} \longrightarrow \text{DISTURBANCE} \longrightarrow \text{PERCEPTION (Phase 4)} \longrightarrow \mathbf{\text{TRACKING / STATE ESTIMATION (Phase 5)}}$$

### Module Organization
```
horizon/
├── tracking/
│   ├── __init__.py
│   ├── association/
│   │   ├── __init__.py
│   │   ├── track.py            # Track lifecycle manager, hit/miss counters
│   │   ├── gate.py             # Mahalanobis chi-squared gating & validation
│   │   └── association.py      # Multi-candidate gating and cost-based assignment
│   ├── estimation/
│   │   ├── __init__.py
│   │   ├── state.py            # State vector, EstimatorStatus enum, StateEstimate
│   │   ├── kalman.py           # TargetKalmanFilter (predict, update, Joseph form)
│   │   ├── model.py            # Transition F, Observation H, Process Q, Measurement R
│   │   ├── covariance.py       # Validation, symmetry enforcement, ellipse extraction
│   │   └── innovation.py       # Residual y, Innovation covariance S, Mahalanobis distance
│   ├── quality/
│   │   ├── __init__.py
│   │   └── track_quality.py    # Quantitative track health dataclass
│   └── diagnostics/
│       ├── __init__.py
│       ├── evaluation.py       # Isolated ground-truth evaluation (RMSE, NEES)
│       └── visualization.py    # Multi-layer visual rendering (ellipse, reticles)
├── simulator/
│   ├── tracking/               # Re-export alias module
│   ├── perception/detector.py  # Passes timestamp & candidates in DetectionResult
│   └── visualization/debug_view.py # Phase 5 UI telemetry & tracking feed overlay
├── tests/
│   ├── reference_kalman.py     # Independent textbook numerical reference filter
│   ├── test_tracking.py        # 25 unit and scenario verification tests
│   ├── test_tracking_leakage.py# AST static analysis verifying zero ground truth leakage
│   └── test_tracking_integration.py # End-to-end integration tests across trajectories
├── benchmarks/
│   └── profile_phase5.py       # Sub-millisecond micro-benchmarking suite
└── ESTIMATION_MODEL.md         # Formal mathematical specification
```

---

## 2. Estimator State & Kinematic Model
- **State Vector:** $\mathbf{x} = [p_x, p_y, v_x, v_y]^T \in \mathbb{R}^4$ (Focal plane pixel position in $[0, 640] \times [0, 480]$ px and pixel velocity in px/s).
- **State Transition Matrix:**
  $$\mathbf{F}(\Delta t) = \begin{bmatrix} 1 & 0 & \Delta t & 0 \\ 0 & 1 & 0 & \Delta t \\ 0 & 0 & 1 & 0 \\ 0 & 0 & 0 & 1 \end{bmatrix}$$
- **Process Noise Matrix:** Continuous White Noise Acceleration (CWNA) formulation with acceleration disturbance $\sigma_a = 50.0\text{ px/s}^2$ (`PROJECT ENGINEERING PARAMETER`).
- **Observation Matrix:**
  $$\mathbf{H} = \begin{bmatrix} 1 & 0 & 0 & 0 \\ 0 & 1 & 0 & 0 \end{bmatrix}$$
- **Adaptive Measurement Noise Matrix:** $\mathbf{R}_k = \operatorname{diag}(\sigma_{r,k}^2, \sigma_{r,k}^2)$ where $\sigma_{r,k} = \operatorname{clip}\left(\frac{\sigma_{base}}{\max(c_k, 0.05)}, 0.05, 5.0\right)$ adapts dynamically to Phase 4 perception confidence.

---

## 3. Mathematical Equations & Covariance Model
- **State Propagation:** $\hat{\mathbf{x}}_{k|k-1} = \mathbf{F}(\Delta t)\hat{\mathbf{x}}_{k-1|k-1}$
- **Covariance Propagation:** $\mathbf{P}_{k|k-1} = \mathbf{F}(\Delta t)\mathbf{P}_{k-1|k-1}\mathbf{F}(\Delta t)^T + \mathbf{Q}(\Delta t)$
- **Residual & Innovation Covariance:** $\mathbf{y}_k = \mathbf{z}_k - \mathbf{H}\hat{\mathbf{x}}_{k|k-1}$, $\mathbf{S}_k = \mathbf{H}\mathbf{P}_{k|k-1}\mathbf{H}^T + \mathbf{R}_k$
- **Kalman Gain:** $\mathbf{K}_k = \mathbf{P}_{k|k-1}\mathbf{H}^T \mathbf{S}_k^{-1}$ (solved via stable linear equation solve `np.linalg.solve(S.T, H @ P).T`)
- **State Update:** $\hat{\mathbf{x}}_{k|k} = \hat{\mathbf{x}}_{k|k-1} + \mathbf{K}_k \mathbf{y}_k$
- **Joseph Form Covariance Update:**
  $$\mathbf{P}_{k|k} = (\mathbf{I} - \mathbf{K}_k \mathbf{H}) \mathbf{P}_{k|k-1} (\mathbf{I} - \mathbf{K}_k \mathbf{H})^T + \mathbf{K}_k \mathbf{R}_k \mathbf{K}_k^T$$
  Guarantees symmetry and positive semi-definiteness under floating-point roundoff.

---

## 4. Mahalanobis Gating & Association Method
- **Statistical Metric:** $d^2 = \mathbf{y}^T \mathbf{S}^{-1} \mathbf{y} \sim \chi^2(2)$.
- **Validation Gate:** $\gamma_{gate} = 9.210$ ($99\%$ confidence limit for 2 DOF).
- **Outlier Rejection:** Detections with $d^2 > \gamma_{gate}$ are discarded. The filter coasts on prediction without state corruption.
- **Candidate Ranking:** For multiple candidates passing the gate:
  $$J_i = d_i^2 - \alpha \cdot \text{confidence}_i - \beta \cdot \text{score}_i, \quad (\alpha=2.0, \beta=1.0)$$
  Candidate with $\min J_i$ is selected. Strictly zero ground truth is accessed.

---

## 5. Missed-Measurement & Coasting Behavior
- When Phase 4 reports `detected == False`:
  - The filter advances time and predicts state forward: $\hat{\mathbf{x}}_k = \hat{\mathbf{x}}_{k|k-1}, \mathbf{P}_k = \mathbf{P}_{k|k-1}$.
  - Filter status transitions to `PREDICTING`.
  - Covariance expands naturally via $\mathbf{Q}(\Delta t)$, widening the validation gate for future reacquisition.
  - When the target reappears, the filter updates immediately without divergence.

---

## 6. Verification Test Matrix & Results
The test suite was executed across all phases with **zero regressions**:

| Test Suite | Tests | Result | Execution Time | Description |
| :--- | :--- | :--- | :--- | :--- |
| **Phase 1 Tests** | 48 | **PASSED** | ~2.5 s | Deterministic foundation, trajectories, clock, seeds |
| **Phase 2 Tests** | 46 | **PASSED** | ~3.0 s | Virtual camera, gimbal geometry, FOV projections |
| **Phase 3 Tests** | 84 | **PASSED** | ~4.5 s | Disturbance pipeline, noise engines, jitter, atmosphere |
| **Phase 4 Tests** | 94 | **PASSED** | ~4.8 s | Classical beacon detection, preprocessing, centroiding |
| **Phase 5 Tracking Tests** | 25 | **PASSED** | 0.68 s | Unit tests, Joseph form, covariance math, gating |
| **Phase 5 AST Leakage Test** | 1 | **PASSED** | 0.05 s | Static AST analysis verifying zero ground truth leakage |
| **Phase 5 Integration Tests** | 4 | **PASSED** | 8.79 s | End-to-end simulation $\to$ perception $\to$ tracking |
| **TOTAL** | **302** | **ALL PASSED (100%)** | **20.69 s** | **Zero Regressions** |

---

## 7. Numerical Validation & Cross-Reference
- **Independent Textbook Reference:** A baseline Kalman filter using explicit matrix inversion ($\mathbf{S}^{-1}$) and standard covariance update was evaluated against the production filter over 50 noisy steps. State vectors and covariance matrices matched within $10^{-5}\text{ px}$.
- **Long-Run Numerical Stability:** 1,000 continuous tracking cycles under random accelerations confirmed:
  - Zero `NaN` or `Inf` occurrences.
  - Positive semi-definite covariance preservation ($\lambda_{min} \ge 0$).
  - Trace of covariance $\operatorname{tr}(\mathbf{P})$ remained strictly bounded.
- **Repeated Reset Stability:** 25 consecutive initialize-update-reset cycles confirmed zero residual memory leaks or state persistence.

---

## 8. Micro-Benchmarking & Performance Results
Measured over 5,000 iterations using `benchmarks/profile_phase5.py`:

| Operation | Mean Latency | Median Latency | P95 Latency | Max Latency | Equivalent Throughput |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Kalman Predict Step** | $27.0\ \mu\text{s}$ | $17.2\ \mu\text{s}$ | $53.1\ \mu\text{s}$ | $2.75\text{ ms}$ | **$37,089\text{ Hz}$** |
| **Kalman Update (Joseph)** | $95.4\ \mu\text{s}$ | $66.4\ \mu\text{s}$ | $212.0\ \mu\text{s}$ | $3.04\text{ ms}$ | **$10,488\text{ Hz}$** |
| **Mahalanobis Gate Test** | $27.1\ \mu\text{s}$ | $19.6\ \mu\text{s}$ | $38.4\ \mu\text{s}$ | $1.06\text{ ms}$ | **$36,916\text{ Hz}$** |
| **Multi-Candidate (5 cands)** | $262.0\ \mu\text{s}$ | $202.2\ \mu\text{s}$ | $567.3\ \mu\text{s}$ | $6.76\text{ ms}$ | **$3,817\text{ Hz}$** |
| **Full Track.step Cycle** | **$96.9\ \mu\text{s}$** | **$82.0\ \mu\text{s}$** | **$194.6\ \mu\text{s}$** | **$1.29\text{ ms}$** | **$10,321\text{ Hz}$** |

*Phase 5 adds less than $0.1\text{ ms}$ overhead per frame, operating at over $10,000\text{ Hz}$.*

---

## 9. Example Tracking Accuracy
Measured against true projected optical sensor ground truth:

| Trajectory / Scenario | Samples Tracked | Position RMSE | 95th Percentile Error | Assessment |
| :--- | :--- | :--- | :--- | :--- |
| **Straight Clean** | 43 | **$0.363\text{ px}$** | $0.531\text{ px}$ | Subpixel tracking precision |
| **Circular Clean** | 17 | **$0.797\text{ px}$** | $1.170\text{ px}$ | Smooth centripetal tracking |
| **Figure-8 Clean** | 11 | **$2.127\text{ px}$** | $3.364\text{ px}$ | Excellent tracking across high-curvature inflection |
| **Difficult Preset** | 120 (100% lock) | **$9.532\text{ px}$** | $17.473\text{ px}$ | Continuous lock through 5px jitter, haze & S&P noise |

---

## 10. Known Limitations
1. **Linear Velocity Assumption:** The constant-velocity model does not model target jerk or high acceleration without process noise expansion.
2. **No Closed-Loop Control:** Camera gimbal control and pointing feedback are deliberately uncoupled (belongs to Phase 6).
3. **No Mission State Machine:** SEARCH, ACQUIRE, TRACK, DEGRADED, REACQUIRE logic belongs strictly to subsequent PAT management phases.

---

## 11. Interface Prepared for Phase 6 (Closed-Loop Control)
Phase 6 can directly ingest the output dataclass:

```python
@dataclass(frozen=True)
class StateEstimate:
    estimated_x: float          # Target position u [px]
    estimated_y: float          # Target position v [px]
    estimated_vx: float         # Target velocity v_u [px/s]
    estimated_vy: float         # Target velocity v_v [px/s]
    covariance: np.ndarray      # 4x4 state covariance matrix
    innovation: Optional[np.ndarray]
    predicted_x: float          # Predicted lead position [px]
    predicted_y: float          # Predicted lead position [px]
    filter_status: EstimatorStatus # TRACKING, PREDICTING, REJECTED
    timestamp: float
    measurement_available: bool
```
Phase 6 gimbal controllers (e.g. PID or Feed-Forward tracking) can use `(estimated_x, estimated_y)` for feedback error and `(estimated_vx, estimated_vy)` for velocity feed-forward pointing commands.
