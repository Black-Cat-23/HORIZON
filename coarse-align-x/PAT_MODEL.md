# Phase 6 — PAT (Pointing, Acquisition, Tracking) Model Specification

## 1. System Overview
The Pointing, Acquisition, and Tracking (PAT) system provides finite state machine (FSM) control for mobile Free-Space Optical Communication (FSOC) coarse alignment terminals. The system operates strictly on sensor observations and state estimation outputs ($\hat{\mathbf{x}}$), completely decoupled from ground-truth simulation variables.

---

## 2. State Machine Specification
```
                 [ Candidate Detected ]
   +-------------------------------------------------+
   |                                                 |
   v                                                 |
+--------+   (N Valid Frames)   +---------+   (Loss/Qual)  +----------+
| SEARCH | -------------------> | ACQUIRE | -------------> |  TRACK   |
+--------+                      +---------+                +----------+
   ^                                 |                          |
   |                                 | (Invalid)                | (2 Misses)
   |                                 v                          v
   |                            +--------+                 +----------+
   | (Timeout)                  | SEARCH |                 | DEGRADED |
   |                            +--------+                 +----------+
   |                                                            |
   +------------------------------------------------------------+
                           (5 Misses / Lost)
                                   |
                                   v
                             +-----------+
                             | REACQUIRE |
                             +-----------+
```

### Modes & Transitions
1. **SEARCH**: No validated beacon lock. Camera executes pre-planned **Raster** or **Spiral** scanning patterns.
2. **ACQUIRE**: Candidate detection observed. Validates $N=3$ consecutive frames with acceptable confidence ($c \ge 0.35$) and innovation ($d^2 \le 16.0$).
3. **TRACK**: Locked tracking state. Dual-axis PID controller commands camera gimbal using estimated target pointing error ($e_{\text{pan}}, e_{\text{tilt}}$).
4. **DEGRADED**: Reduced detector quality or 2 consecutive missed frames. Controller gains are scaled by $50\%$ to prevent chasing noise while relying on Kalman predictions.
5. **REACQUIRE**: Persistent loss ($5$ missed frames). Initiates a localized Archimedean spiral search centered around predicted state $\hat{\mathbf{x}}_{k|k-1}$ and last known target position.

---

## 3. Dedicated Track Quality Metric ($Q_{\text{track}}$)
Unlike simple perception confidence, $Q_{\text{track}} \in [0.0, 1.0]$ combines four independent metrics:
$$Q_{\text{track}} = 0.35 \cdot c + 0.25 \cdot \max\left(0, 1 - \frac{d^2}{16.0}\right) + 0.20 \cdot \exp\left(-\frac{\text{trace}(\mathbf{P}_{\text{pos}})}{1000.0}\right) + 0.20 \cdot \frac{1}{1 + \text{misses}}$$

| Parameter | Type | Value | Unit | Description |
|---|---|---|---|---|
| `acquire_required_frames` | Engineering Parameter | `3` | frames | Confirmation lock threshold |
| `degraded_miss_frames` | Engineering Parameter | `2` | frames | Degradation trigger threshold |
| `reacquire_trigger_frames` | Engineering Parameter | `5` | frames | Reacquisition trigger threshold |
| `maximum_prediction_frames` | Engineering Parameter | `30` | frames | Max coasting prediction frames |
| `reacquire_timeout_s` | Engineering Parameter | `8.0` | s | Max reacquisition search duration |
