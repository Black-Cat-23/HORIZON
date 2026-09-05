# HORIZON — DISTURBANCE, SENSOR NOISE & PLATFORM MOTION MODEL
**Problem Statement SIH26169:** AI-Based Virtual Camera Tracking System for Coarse Alignment of Mobile FSOC Terminals  
**Phase:** 3 — Disturbance, Sensor Noise & Platform Motion Engine  
**Document Version:** 1.0  
**Status:** Verified & Formally Tested  

---

## 1. Purpose of the Disturbance Engine

In Free Space Optical Communications (FSOC), coarse beam alignment must occur across real atmospheric free-space links between mobile, vibrating platforms (such as aircraft, naval vessels, UAVs, and satellites). Optical sensors operating in these operational theaters do not experience clean mathematical pinhole projections. Instead, they are subject to:

1. **Platform Mechanical Dynamics:** Continuous base vibrations, structural flexing, and attitude drift caused by mobile vehicle motion.
2. **Optical Jitter:** Rapid line-of-sight angular micro-jitters introduced by mechanical vibration, gimbal motor cogging, and aerodynamic turbulence.
3. **Atmospheric Extinction & Airlight:** Signal attenuation, contrast loss, and ambient background scattering from clear air, haze, fog, rain, and nocturnal low-light conditions.
4. **Sensor & Photonic Noise:** Quantum photon arrival fluctuations (Poisson shot noise), analog-to-digital read noise (Gaussian thermal noise), and detector element transmission drops / bit errors (Salt & Pepper impulse noise).

The Phase 3 Disturbance Engine introduces these realistic degradations to ensure that downstream perception (Phase 4) and tracking control (Phase 5+) are tested against challenging, non-ideal observations rather than sterile simulations.

---

## 2. Fundamental Distinction: Ground Truth vs. Sensor Observation

A non-negotiable architectural invariant governs HORIZON:

$$\mathbf{S}_{\text{ground\_truth}} = \left[ x_{\text{world}}, y_{\text{world}}, v_x, v_y, a_x, a_y, \theta_{\text{pan}}, \theta_{\text{tilt}}, u_{\text{ideal}}, v_{\text{ideal}} \right]^T$$

**The disturbance engine NEVER modifies ground truth.**

- $\mathbf{S}_{\text{ground\_truth}}$ represents the exact physical target kinematics and gimbal joint coordinates.
- $\mathbf{I}_{\text{disturbed}}$ represents what the optical sensor detects after platform motion, atmospheric degradation, optical jitter, and detector noise.
- Ground truth provides the absolute reference for calculating tracking error $\mathbf{e}(t) = \hat{\mathbf{x}}(t) - \mathbf{x}_{\text{true}}(t)$ in later verification gates.

```
       [ WORLD / TARGET KINEMATICS ]
                     ↓
        [ GIMBAL PHYSICAL DYNAMICS ]
                     ↓
    [ PINHOLE OPTICAL PROJECTION: u, v ] ────────────→ RECORDED TO GROUND TRUTH
                     ↓
         [ CLEAN 640×480 FRAME ]  ──────────────────→ PRESERVED AS CLEAN COPY
                     ↓
            DISTURBANCE PIPELINE
          1. Platform Motion Stage
          2. Atmospheric Degradation Stage
          3. Sensor Noise Injection Stage
          4. Camera Jitter Stage
                     ↓
       [ DISTURBED 640×480 FRAME ]  ─────────────────→ INPUT TO PHASE 4 PERCEPTION
```

---

## 3. Mathematical Disturbance Models

### 3.1. Platform Motion Model
- **Classification:** Continuous physical displacement of the observation aperture relative to the base reference frame.
- **Official SIH Limit:** Maximum per-frame displacement $\le \pm 20.0$ pixels/frame.
- **Mandatory Model (Linear):**
  $$\Delta x = \text{clamp}\left(v_x \Delta t, -20.0, 20.0\right), \quad \Delta y = \text{clamp}\left(v_y \Delta t, -20.0, 20.0\right)$$
  $$x_{\text{plat}}(t + \Delta t) = x_{\text{plat}}(t) + \Delta x, \quad y_{\text{plat}}(t + \Delta t) = y_{\text{plat}}(t) + \Delta y$$
  When cumulative offset $|x_{\text{plat}}| \ge x_{\text{bound}}$, velocity reverses ($v_x \leftarrow -v_x$) to preserve continuity without teleportation.
- **Optional Models:**
  - *Circular:* $x(t) = R \cos(\omega t), y(t) = R \sin(\omega t)$
  - *Figure-8:* $x(t) = A_x \sin(\omega t), y(t) = A_y \sin(2\omega t)$
  - *Spiral:* $x(t) = r(t) \cos(\omega t), y(t) = r(t) \sin(\omega t)$
  - *Random:* Ornstein-Uhlenbeck continuous velocity integration:
    $$\dot{v}_x = -\theta v_x + \sigma_w w_x(t)$$

### 3.2. Atmospheric Degradation Model
Per SIH26169, atmospheric effects are modeled as user-defined reductions in contrast and brightness.
$$\tilde{I}(u, v) = \frac{I(u, v)}{255.0}$$
$$I_{\text{atmos}}(u, v) = \text{round}\left(255.0 \times \text{clip}\left(c \cdot \tilde{I}(u, v) + b, 0.0, 1.0\right)\right)$$
Where:
- $c \ge 0.0$ is the contrast multiplier.
- $b \in [-1.0, 1.0]$ is the brightness offset.

The 5 official conditions and their Project Default parameters:
| Condition | Contrast Factor $c$ | Brightness Offset $b$ | Designation | Description |
| :--- | :--- | :--- | :--- | :--- |
| **CLEAR** | $1.00$ | $0.00$ | OFFICIAL SIH | Perfect optical transmission (mathematical identity $\mathbf{I}' = \mathbf{I}$). |
| **HAZE** | $0.65$ | $+0.12$ | PROJECT DEFAULT | Moderate contrast reduction with diffuse airlight veil. |
| **FOG** | $0.35$ | $+0.25$ | PROJECT DEFAULT | Heavy optical extinction, dense scattering veil. |
| **RAIN** | $0.70$ | $-0.05$ | PROJECT DEFAULT | Rain drop scattering, slight darkness attenuation. |
| **LOW_LIGHT** | $0.85$ | $-0.40$ | PROJECT DEFAULT | Nocturnal / low solar irradiance conditions. Note: NO silent noise injection. |

### 3.3. Sensor Noise Models

#### 3.3.1. Salt & Pepper Noise (Impulse Noise)
- **Official Reference:** Approximately 10% corrupted pixels.
- **Model:** For each pixel with random draw $\xi \sim U(0, 1)$:
  $$I_{\text{sp}}(u, v) = \begin{cases} 255 & \text{if } \xi < \frac{p}{2} \quad (\text{Salt}) \\ 0 & \text{if } \frac{p}{2} \le \xi < p \quad (\text{Pepper}) \\ I(u, v) & \text{if } \xi \ge p \end{cases}$$
- **Default Probability:** $p = 0.10$.

#### 3.3.2. Additive Gaussian Sensor Noise
- **Official SIH Limit:** Maximum standard deviation $\sigma \le 20.0$ pixels.
- **Model:**
  $$\eta \sim \mathcal{N}\left(0, \sigma^2\right)$$
  $$I_{\text{gauss}}(u, v) = \text{round}\left(\text{clip}\left(I(u, v) + \eta, 0.0, 255.0\right)\right)$$
- Float64 calculations avoid intermediate quantization error.

#### 3.3.3. Poisson Shot Noise (Photon Counting Statistics)
- **Model:** Physical photon shot noise arriving at the sensor array:
  $$\lambda(u, v) = I(u, v) \times \frac{\Phi_{\text{peak}}}{255.0}$$
  $$k(u, v) \sim \text{Poisson}\left(\lambda(u, v)\right)$$
  $$I_{\text{poisson}}(u, v) = \text{round}\left(\text{clip}\left(k(u, v) \times \frac{255.0}{\Phi_{\text{peak}}}, 0.0, 255.0\right)\right)$$
- $\Phi_{\text{peak}}$ is the peak photon count (PROJECT DEFAULT = 50.0). Lower counts naturally yield higher relative quantum shot variance.

### 3.4. Camera Jitter Model
- **Classification:** High-frequency zero-mean optical line-of-sight shift.
- **Official SIH Limit:** Maximum displacement $\le \pm 20.0$ pixels/frame.
- **Model:** Per-frame stochastic shift $(\delta x, \delta y)$ sampled from uniform or normal distributions:
  $$\delta x \in [-j_x^{\max}, +j_x^{\max}], \quad \delta y \in [-j_y^{\max}, +j_y^{\max}]$$
  $$\mathbf{I}_{\text{jitter}}(u, v) = \mathbf{I}(u - \delta x, v - \delta y)$$
- Applied via subpixel affine translation (`cv2.warpAffine`) with zero border padding.

---

## 4. Pipeline Order of Operations

The order of operations is explicit, deterministic, and strictly sequenced:

1. **Stage 1 — Platform Motion:** Displaces the camera field of regard continuously according to vehicle kinematics.
2. **Stage 2 — Atmospheric Degradation:** Applies medium attenuation (contrast and brightness adjustment).
3. **Stage 3 — Sensor Noise Injection:**
   - Salt & Pepper (dead/hot detector elements)
   - Additive Gaussian (thermal Johnson-Nyquist / amplifier read noise)
   - Poisson (quantum photon arrival statistics)
4. **Stage 4 — Camera Jitter:** High-frequency image-plane line-of-sight shift.

---

## 5. Parameter Classification & Taxonomy

| Parameter | Official SIH | Project Default | User Configurable | Allowed Range |
| :--- | :---: | :---: | :---: | :--- |
| `gaussian.sigma` | **YES** | — | YES | $[0.0, 20.0]$ px |
| `camera_jitter.max_x_px` | **YES** | — | YES | $[0.0, 20.0]$ px |
| `camera_jitter.max_y_px` | **YES** | — | YES | $[0.0, 20.0]$ px |
| `platform_motion.max_dx_px_per_frame` | **YES** | — | YES | $[0.0, 20.0]$ px/frame |
| `platform_motion.max_dy_px_per_frame` | **YES** | — | YES | $[0.0, 20.0]$ px/frame |
| `salt_pepper.probability` | **YES** (Ref ~10%) | 0.10 | YES | $[0.0, 1.0]$ |
| `atmosphere.condition` | **YES** (5 types) | CLEAR | YES | {clear, haze, fog, rain, low_light} |
| `atmosphere.contrast_factor` | — | **YES** | YES | $\ge 0.0$ |
| `atmosphere.brightness_factor`| — | **YES** | YES | $[-1.0, 1.0]$ |
| `poisson.peak_photons` | — | **YES** (50.0) | YES | $> 0.0$ |
| `platform_motion.boundary_limit_px` | — | **YES** (100.0) | YES | $> 0.0$ px |

---

## 6. Predefined Disturbance Presets

| Preset | S&P Prob | Gauss $\sigma$ | Poisson Peak | Jitter Bounds | Platform Model | Atmosphere | Purpose |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **NOMINAL** | Disabled (0.0) | Disabled (0.0) | Disabled | Disabled (0, 0) | Disabled | CLEAR (1.0, 0.0) | Clean sensor baseline |
| **DIFFICULT** | 0.03 (3%) | 6.0 px | 80 photons | $\pm 5.0$ px | Linear (40, 20 px/s) | HAZE (0.65, +0.12) | Operational maritime haze |
| **SEVERE** | 0.08 (8%) | 15.0 px | 30 photons | $\pm 14.0$ px | Linear (80, 50 px/s) | FOG (0.35, +0.25) | Dense advection fog |
| **RECOVERY** | Disabled (0.0) | 8.0 px | 50 photons | $\pm 16.0$ px | Linear (60, 30 px/s) | LOW_LIGHT (0.85, -0.40) | Target loss & recovery testing |
| **ADVERSARIAL**| 0.10 (10%) | **20.0 px (MAX)** | 20 photons | **$\pm 20.0$ px (MAX)**| Linear (**20 px/frame MAX**)| RAIN (0.70, -0.05) | Boundary compliance stress |

---

## 7. Determinism & Random Stream Separation

All stochastic operations are strictly isolated using NumPy's `SeedSequence` mechanism via `SeedManager`. No global `np.random` calls are made.

The named child streams are:
- `seed_mgr.get_rng("salt_pepper")`
- `seed_mgr.get_rng("gaussian")`
- `seed_mgr.get_rng("poisson")`
- `seed_mgr.get_rng("jitter")`
- `seed_mgr.get_rng("platform")`

This guarantees that:
1. Seed 42 reproduces identical disturbed frames across repeated executions.
2. Modifying Gaussian parameters does not alter the random sequence generated for Salt & Pepper or Camera Jitter.

---

## 8. Known Limitations & Phase 4 Transition Interface

1. **Atmospheric Physics Simplification:** Atmospheric modeling in Phase 3 follows the explicit SIH requirement of user-defined contrast and brightness reduction. Physical phase screens (Kolmogorov/von Kármán turbulence, scintillations) are not introduced because they exceed SIH26169 specifications.
2. **Phase 4 Transition Interface:**
   - `SimulationEngine.get_clean_frame() -> np.ndarray (480, 640, uint8)`
   - `SimulationEngine.get_disturbed_frame() -> np.ndarray (480, 640, uint8)`
   - `SimulationEngine.get_camera_frame() -> np.ndarray (480, 640, uint8)` (Returns disturbed observation)
   - `SimulationEngine.last_disturbance_telemetry -> DisturbanceTelemetry`
   - Phase 4 detection algorithms will take `engine.get_camera_frame()` as input and compute beacon centroid coordinates $(\hat{u}, \hat{v})$.
