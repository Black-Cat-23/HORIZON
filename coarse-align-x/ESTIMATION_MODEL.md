# HORIZON Phase 5 — Mathematical Specification & Estimation Model
**SIH26169: AI-Based Virtual Camera Tracking System for Coarse Alignment of Mobile FSOC Terminals**

---

## 1. Executive Summary & Purpose
This document provides the formal mathematical formulation, coordinate system definitions, discrete-time state-space models, covariance propagation rules, statistical gating thresholds, and association algorithms for the **HORIZON Phase 5 Target Association and State Estimation Engine**.

The objective of Phase 5 is to ingest raw, noisy, intermittent frame-by-frame beacon centroid detections from the Phase 4 Perception stage and estimate a continuous, filtered, optimal kinematic target state vector $\mathbf{x} = [p_x, p_y, v_x, v_y]^T$ and error covariance matrix $\mathbf{P}$.

---

## 2. Coordinate System & State Definition

### Coordinate Convention
- **Coordinate Space:** Sensor Focal Plane Image Coordinates [pixels]
- **Origin $(0, 0)$:** Top-left corner of the $640 \times 480$ optical sensor.
- **Horizontal Axis $(u)$:** $[0.0, 640.0]$ pixels, positive pointing right.
- **Vertical Axis $(v)$:** $[0.0, 480.0]$ pixels, positive pointing down.
- **Classification:** `PROJECT ENGINEERING PARAMETER` (matches Phase 4 subpixel centroid space; an angular line-of-sight estimator $[\theta_x, \theta_y]^T$ can be coupled directly via camera intrinsics in subsequent phases).

### State Vector Representation
$$\mathbf{x}_k = \begin{bmatrix} p_{x,k} \\ p_{y,k} \\ v_{x,k} \\ v_{y,k} \end{bmatrix} \in \mathbb{R}^4$$

| State Variable | Description | Dimension / Units | Parameter Classification |
| :--- | :--- | :--- | :--- |
| $p_{x,k}$ | Target horizontal focal plane position | Pixels $[\text{px}]$ | `IMPLEMENTATION DETAIL` |
| $p_{y,k}$ | Target vertical focal plane position | Pixels $[\text{px}]$ | `IMPLEMENTATION DETAIL` |
| $v_{x,k}$ | Target horizontal velocity | Pixels/second $[\text{px/s}]$ | `IMPLEMENTATION DETAIL` |
| $v_{y,k}$ | Target vertical velocity | Pixels/second $[\text{px/s}]$ | `IMPLEMENTATION DETAIL` |

---

## 3. Kinematic Motion Model

### Constant-Velocity (CV) State Transition
The target kinematics between measurement epochs $t_{k-1}$ and $t_k$ ($\Delta t = t_k - t_{k-1}$) are modeled as a discrete-time Gauss-Markov constant-velocity process:

$$\mathbf{x}_k = \mathbf{F}(\Delta t) \mathbf{x}_{k-1} + \mathbf{w}_{k-1}, \quad \mathbf{w}_k \sim \mathcal{N}(\mathbf{0}, \mathbf{Q}(\Delta t))$$

### State Transition Matrix $\mathbf{F}(\Delta t)$
$$\mathbf{F}(\Delta t) = \begin{bmatrix} 1 & 0 & \Delta t & 0 \\ 0 & 1 & 0 & \Delta t \\ 0 & 0 & 1 & 0 \\ 0 & 0 & 0 & 1 \end{bmatrix}$$

- **Time Step Validation:** $\Delta t > 0$. If $\Delta t \le 0$ (stale/duplicate frame), prediction is bypassed and a system alert is logged.
- **Classification:** `PROJECT ENGINEERING PARAMETER`.

---

## 4. Process Noise Covariance $\mathbf{Q}(\Delta t)$

### Formulation: Continuous White Noise Acceleration (CWNA)
We assume target acceleration is driven by zero-mean, continuous white noise $a(t)$ with power spectral density $q_c = \sigma_a^2$:

$$\mathbf{Q}(\Delta t) = \int_0^{\Delta t} \mathbf{F}(\tau) \mathbf{G} q_c \mathbf{G}^T \mathbf{F}(\tau)^T d\tau, \quad \mathbf{G} = \begin{bmatrix} 0 & 0 \\ 0 & 0 \\ 1 & 0 \\ 0 & 1 \end{bmatrix}$$

Evaluating the integral yields the analytical block diagonal covariance:
$$\mathbf{Q}(\Delta t) = \sigma_a^2 \begin{bmatrix} \frac{\Delta t^3}{3} & 0 & \frac{\Delta t^2}{2} & 0 \\ 0 & \frac{\Delta t^3}{3} & 0 & \frac{\Delta t^2}{2} \\ \frac{\Delta t^2}{2} & 0 & \Delta t & 0 \\ 0 & \frac{\Delta t^2}{2} & 0 & \Delta t \end{bmatrix}$$

- **Acceleration Noise Intensity $\sigma_a$:** Nominal value: $50.0\text{ px/s}^2$.
- **Classification:** `PROJECT ENGINEERING PARAMETER`.
- **Physical Rationale:** Models target turns, maneuvers, optical jitter, and wind-buffeting without forcing artificial trajectory lock.

---

## 5. Observation Model & Measurement Matrix $\mathbf{H}$

Phase 4 Optical Beacon Perception yields 2D focal plane centroid positions:
$$\mathbf{z}_k = \begin{bmatrix} z_{x,k} \\ z_{y,k} \end{bmatrix} = \mathbf{H} \mathbf{x}_k + \mathbf{v}_k, \quad \mathbf{v}_k \sim \mathcal{N}(\mathbf{0}, \mathbf{R}_k)$$

### Observation Matrix $\mathbf{H}$
$$\mathbf{H} = \begin{bmatrix} 1 & 0 & 0 & 0 \\ 0 & 1 & 0 & 0 \end{bmatrix} \in \mathbb{R}^{2 \times 4}$$

- **Strict Invariant:** The measurement $\mathbf{z}_k$ receives ONLY measured centroid coordinates and detector metadata. Ground truth target states are never accessed.

---

## 6. Adaptive Measurement Noise $\mathbf{R}_k(\text{confidence})$

Perception quality varies based on SNR, atmospheric haze, and optical flare. Rather than a constant measurement noise matrix, $\mathbf{R}_k$ dynamically adapts to detector confidence $c_k \in [0.0, 1.0]$:

$$\sigma_{r,k} = \operatorname{clip}\left(\frac{\sigma_{base}}{\max(c_k, 0.05)}, \sigma_{min}, \sigma_{max}\right)$$
$$\mathbf{R}_k = \begin{bmatrix} \sigma_{r,k}^2 & 0 \\ 0 & \sigma_{r,k}^2 \end{bmatrix}$$

- **$\sigma_{base}$:** $0.5\text{ px}$ (nominal subpixel centroid noise at $c=1.0$).
- **$\sigma_{min}$:** $0.05\text{ px}$ (lower noise floor).
- **$\sigma_{max}$:** $5.0\text{ px}$ (upper uncertainty clamp for faint detections).
- **Classification:** `PROJECT ENGINEERING PARAMETER`.

---

## 7. Kalman Filter Equations

### A. Prediction Step
$$\hat{\mathbf{x}}_{k|k-1} = \mathbf{F}(\Delta t) \hat{\mathbf{x}}_{k-1|k-1}$$
$$\mathbf{P}_{k|k-1} = \mathbf{F}(\Delta t) \mathbf{P}_{k-1|k-1} \mathbf{F}(\Delta t)^T + \mathbf{Q}(\Delta t)$$
- Symmetry Enforcement: $\mathbf{P}_{k|k-1} \leftarrow \frac{1}{2}\left(\mathbf{P}_{k|k-1} + \mathbf{P}_{k|k-1}^T\right)$.

### B. Innovation & Residual Covariance
$$\mathbf{y}_k = \mathbf{z}_k - \mathbf{H} \hat{\mathbf{x}}_{k|k-1} \in \mathbb{R}^{2 \times 1}$$
$$\mathbf{S}_k = \mathbf{H} \mathbf{P}_{k|k-1} \mathbf{H}^T + \mathbf{R}_k \in \mathbb{R}^{2 \times 2}$$

### C. Kalman Gain
$$\mathbf{K}_k = \mathbf{P}_{k|k-1} \mathbf{H}^T \mathbf{S}_k^{-1}$$
- Numerical Implementation: Solved via linear system solve (`np.linalg.solve(S.T, H @ P).T`) rather than explicit matrix inversion to avoid roundoff error.

### D. State Update
$$\hat{\mathbf{x}}_{k|k} = \hat{\mathbf{x}}_{k|k-1} + \mathbf{K}_k \mathbf{y}_k$$

### E. Covariance Update: Stabilized Joseph Form
Standard textbook covariance update $\mathbf{P} = (\mathbf{I} - \mathbf{K}\mathbf{H})\mathbf{P}_{pred}$ is prone to loss of positive definiteness under finite floating-point precision. We strictly use the **Joseph stabilized formulation**:

$$\mathbf{P}_{k|k} = (\mathbf{I} - \mathbf{K}_k \mathbf{H}) \mathbf{P}_{k|k-1} (\mathbf{I} - \mathbf{K}_k \mathbf{H})^T + \mathbf{K}_k \mathbf{R}_k \mathbf{K}_k^T$$
- Mathematically guaranteed to remain positive semi-definite for any gain $\mathbf{K}_k$.
- Enforce exact symmetry: $\mathbf{P}_{k|k} \leftarrow \frac{1}{2}\left(\mathbf{P}_{k|k} + \mathbf{P}_{k|k}^T\right)$.

---

## 8. Statistical Mahalanobis Gating & Outlier Rejection

Under linear Gaussian assumptions, the squared Mahalanobis distance of the innovation residual:
$$d_k^2 = \mathbf{y}_k^T \mathbf{S}_k^{-1} \mathbf{y}_k$$
follows a central Chi-squared distribution with $n_z = 2$ degrees of freedom:
$$d_k^2 \sim \chi^2(2)$$

### Gating Decision Rule
$$\text{If } d_k^2 \le \gamma_{gate}: \quad \text{ACCEPT MEASUREMENT} \to \text{Execute Kalman update}$$
$$\text{If } d_k^2 > \gamma_{gate}: \quad \text{REJECT AS OUTLIER} \to \text{Coast on prediction, status = REJECTED\_MEASUREMENT}$$

| Confidence Probability $1 - \alpha$ | $\chi^2(2)$ Threshold $\gamma_{gate}$ | Classification |
| :--- | :--- | :--- |
| $90.0\%$ | $4.605$ | `PROJECT ENGINEERING PARAMETER` |
| $95.0\%$ | $5.991$ | `PROJECT ENGINEERING PARAMETER` |
| **$99.0\%$ (Nominal Default)** | **$9.210$** | **`PROJECT ENGINEERING PARAMETER`** |
| $99.9\%$ | $13.816$ | `PROJECT ENGINEERING PARAMETER` |

---

## 9. Multi-Candidate Association Logic

When Phase 4 produces multiple candidate regions (e.g. true beacon + bright distractor + noise blob):
1. **Predict State:** $\hat{\mathbf{x}}_{k|k-1}, \mathbf{P}_{k|k-1}$.
2. **Residual & Gating:** Compute $\mathbf{y}_i, \mathbf{S}_i, d_i^2$ for every candidate $i \in \{1, \dots, N\}$.
3. **Ellipsoidal Filter:** Reject all candidates where $d_i^2 > \gamma_{gate}$.
4. **Cost Optimization:** For remaining valid gated candidates, compute composite assignment cost:
   $$J_i = d_i^2 - \alpha \cdot \text{confidence}_i - \beta \cdot \text{score}_i$$
   - $\alpha = 2.0$, $\beta = 1.0$ (`PROJECT ENGINEERING PARAMETER`).
5. **Selection:** Select candidate with $\min J_i$.
- **Strict Invariant:** Ground truth is never used for candidate selection.

---

## 10. Track Initialization, Missing Observations & Reset Policy

### Track Initialization Policy
- **First Measurement $\mathbf{z}_0$:** Initial position is set to $\mathbf{z}_0$.
- **Initial Velocity Policy:** Set strictly to $(0.0, 0.0)\text{ px/s}$.
- **Initial Covariance $\mathbf{P}_0$:**
  $$\mathbf{P}_0 = \operatorname{diag}(\sigma_{p0}^2, \sigma_{p0}^2, \sigma_{v0}^2, \sigma_{v0}^2)$$
  With $\sigma_{p0} = 5.0\text{ px}$, $\sigma_{v0} = 120.0\text{ px/s}$. High initial velocity variance allows subsequent frames to rapidly converge to true target velocity without initial bias.
- **Strict Invariant:** Ground-truth velocity is NEVER injected.

### Missing Observation Behavior (`detected == False`)
- Advance prediction: $\hat{\mathbf{x}}_k = \hat{\mathbf{x}}_{k|k-1}$, $\mathbf{P}_k = \mathbf{P}_{k|k-1}$.
- Filter status transitions to `PREDICTING`.
- Covariance expands naturally via $\mathbf{Q}(\Delta t)$.
- No NaNs or unbounded divergence; instant seamless recovery when target is redetected.

### Track Reset
- `reset()` completely wipes state vector, covariance matrix, innovation, and counters back to `UNINITIALIZED`.

---

## 11. Covariance Uncertainty Ellipse Derivation

For diagnostic visualization and tracking console displays, the $2 \times 2$ positional submatrix $\mathbf{P}_{pos} = \mathbf{P}_{k|k}[0:2, 0:2]$ is extracted and spectrally decomposed:

$$\mathbf{P}_{pos} \mathbf{v}_i = \lambda_i \mathbf{v}_i, \quad \lambda_1 \ge \lambda_2 \ge 0$$

For confidence probability $p = 0.95$ ($2\sigma$ equivalent, $\chi^2(2) = 5.991$):
$$k = \sqrt{-2 \ln(1 - p)} = \sqrt{5.991} \approx 2.4477$$
- **Semi-Major Axis:** $a = k \sqrt{\lambda_1}$
- **Semi-Minor Axis:** $b = k \sqrt{\lambda_2}$
- **Ellipse Orientation:** $\theta = \operatorname{atan2}(v_{y,1}, v_{x,1})$

---

## 12. Assumptions & Known Limitations

| Item | Classification | Description |
| :--- | :--- | :--- |
| **Focal Plane Coordinates** | `ASSUMPTION` | State is tracked in 2D sensor image pixels $[u, v]$, matching Phase 4 detector output. |
| **Constant Velocity** | `ASSUMPTION` | Baseline target motion assumes constant velocity with acceleration modeled as unmodeled white noise. High jerk maneuvers cause transient tracking lag. |
| **Single Primary Target** | `ASSUMPTION` | Associator tracks 1 active target track while rejecting $N$ distractors. Multi-target MHT/JPDA is out of scope for Phase 5. |
| **No Gimbal Feedback** | `LIMITATION` | Gimbal feedback control, PID, and PAT state machine belong strictly to Phase 6+. Phase 5 does not issue camera actuation commands. |
