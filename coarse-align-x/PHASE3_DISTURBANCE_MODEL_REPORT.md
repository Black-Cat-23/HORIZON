# PHASE 3 DISTURBANCE MODEL REPORT
**HORIZON Adversarial Sensor & Environment Test Laboratory**

---

## Executive Summary

The **Phase 3 Disturbance Engine** has been upgraded from a basic noise injection wrapper into an adversarial, independently controlled sensor and environment test laboratory. All existing official SIH26169 Problem Statement (PS) disturbances are strictly preserved while introducing 14 advanced optical, atmospheric, temporal, distractor, and correlation capabilities.

> [!CRITICAL]
> **Ground Truth Invariant**:
> All disturbance modules operate strictly on sensor image frames or apparent optical centroids. The ground-truth target kinematics (`TargetState` position $x, y$, velocity $v_x, v_y$, and acceleration $a_x, a_y$) remain **100% untouched and uncorrupted**.

---

## Parameter Classification Taxonomy

Every disturbance parameter in the HORIZON simulation system is explicitly classified under one of four mathematical/engineering tiers:

1. **`OFFICIAL PS`**: Parameters strictly specified or bounded by the official SIH26169 problem statement.
2. **`PROJECT DEFAULT`**: Engineering baseline values selected for realistic baseline execution.
3. **`MODEL ASSUMPTION`**: Analytical turbulence / physical sensor transfer models.
4. **`EXPERIMENTAL`**: Adversarial stress test scenarios for failure analysis.

| Parameter | Class | Value / Bound | Rationale & Description |
| :--- | :---: | :--- | :--- |
| **Gaussian Noise $\sigma$** | `OFFICIAL PS` | $0.0 \le \sigma \le 20.0\text{ px}$ | Sensor thermal read noise standard deviation. |
| **Camera Jitter $dx, dy$** | `OFFICIAL PS` | $\le \pm 20.0\text{ px/frame}$ | Zero-mean high-frequency optical image displacement. |
| **Platform Motion Velocity** | `OFFICIAL PS` | $\le \pm 20.0\text{ px/frame}$ | Continuous low-frequency platform sway velocity limits. |
| **Salt & Pepper Probability** | `OFFICIAL PS` | $0.10$ ($10\%$) | Impulse hot/dead pixel noise probability reference. |
| **Atmospheric Conditions** | `OFFICIAL PS` | `clear`, `haze`, `fog`, `rain`, `low_light` | Specified atmospheric optical degradation states. |
| **Atmospheric Severity** | `PROJECT DEFAULT` | $0.0 \le s \le 1.0$ | Continuous severity scaling factor for contrast and brightness. |
| **Poisson Peak Photons** | `PROJECT DEFAULT` | $50.0\text{ photons}$ | Shot noise scaling for digital pixel ADU conversion. |
| **Intensity Fluctuation Depth** | `MODEL ASSUMPTION` | $0.0 \le d \le 1.0$ | Temporal scintillation & slow envelope fading modulation depth. |
| **Beam Wander Std Dev** | `MODEL ASSUMPTION` | $\sigma_{\text{bw}} = 2.0\text{ px}$ | Low-frequency Ornstein-Uhlenbeck (OU) centroid drift. |
| **Beam Wander Correlation Time** | `MODEL ASSUMPTION` | $\tau = 0.5\text{ s}$ | OU process memory time constant. |
| **Temporary Occlusion Window** | `EXPERIMENTAL` | $t_{\text{start}}, \Delta t, s$ | Partial/complete target obscuration window. |
| **False Optical Distractors** | `EXPERIMENTAL` | Count, type, motion | Physically plausible bright distractors (`small_spot`, `large_blob`, etc.). |
| **Cross-Channel Correlation** | `MODEL ASSUMPTION` | $\rho \in [0, 1]$ | Cholesky-coupled random noise (e.g. platform motion + jitter). |
| **Injection Scheduler** | `EXPERIMENTAL` | `immediate`, `ramped`, `pulsed` | Dynamic disturbance gain $g(t)$ transition profiles. |

---

## Detailed Capabilities & Architectural Verification

### 1. Temporal Intensity Fluctuation
Implemented in [`simulator/disturbances/intensity_fluctuation.py`](file:///d:/Hackathon/SIH2.0/HORIZON/coarse-align-x/simulator/disturbances/intensity_fluctuation.py).
- **Modes**:
  - `slow`: Low-frequency sinusoidal envelope ($f \approx 0.1\text{ Hz}$) representing atmospheric beam wander out-of-aperture loss.
  - `fast`: High-frequency log-normal optical scintillation ($f \approx 10 - 50\text{ Hz}$).
  - `mixed`: Superposition of slow atmospheric fading envelope and fast scintillation.

### 2. Temporary Occlusion
Implemented in [`simulator/disturbances/occlusion.py`](file:///d:/Hackathon/SIH2.0/HORIZON/coarse-align-x/simulator/disturbances/occlusion.py).
- Supports `complete` (100% attenuation to ambient background) and `partial` (spatial trapezoidal mask) during active window $[t_{\text{start}}, t_{\text{start}} + \Delta t]$.

### 3. Motion Blur Engine
Integrated with [`simulator/camera/motion_blur.py`](file:///d:/Hackathon/SIH2.0/HORIZON/coarse-align-x/simulator/camera/motion_blur.py).
- Physical 1D directional convolution kernel length derived strictly from target velocity vector $\|v\|$ and integration time $\text{exposure\_ms}$.

### 4. False Optical Targets (Distractors)
Implemented in [`simulator/disturbances/distractor.py`](file:///d:/Hackathon/SIH2.0/HORIZON/coarse-align-x/simulator/disturbances/distractor.py).
- Renders 5 distinct false target geometries: `small_spot`, `large_blob`, `multiple_spots`, `reflection_like` streaks, and `noise_cluster`.

### 5. Cross-Channel Disturbance Correlation
Implemented in [`simulator/disturbances/correlation.py`](file:///d:/Hackathon/SIH2.0/HORIZON/coarse-align-x/simulator/disturbances/correlation.py).
- Uses Cholesky factorization to couple platform motion surges with camera jitter variance ($\rho_{\text{pj}}$) and atmospheric severity with intensity depth ($\rho_{\text{ai}}$). Uncorrelated by default.

### 6. Continuous Atmospheric Severity
Exposed in [`simulator/disturbances/config.py`](file:///d:/Hackathon/SIH2.0/HORIZON/coarse-align-x/simulator/disturbances/config.py).
- Parameter $s \in [0.0, 1.0]$ scales contrast reduction and brightness attenuation smoothly without step functions.

### 7. Turbulence-Oriented Optical Effects (Beam Wander vs. Scintillation)
- **Decoupled Architecture**: Beam wander is modeled as an spatial centroid drift in [`beam_wander.py`](file:///d:/Hackathon/SIH2.0/HORIZON/coarse-align-x/simulator/camera/beam_wander.py), while scintillation is modeled as intensity variance in [`intensity_fluctuation.py`](file:///d:/Hackathon/SIH2.0/HORIZON/coarse-align-x/simulator/disturbances/intensity_fluctuation.py).
- Kept strictly distinct in compliance with recent FSOC literature.

### 8. Disturbance Instrumentation & Telemetry
Every frame produces [`DisturbanceTelemetry`](file:///d:/Hackathon/SIH2.0/HORIZON/coarse-align-x/simulator/disturbances/pipeline.py#L37-L60) containing:
- Configured vs. actual realized values ($dx, dy, \sigma$, contrast, transmission, distractor count).

### 9. Dynamic Injection Scheduler
Implemented in [`simulator/disturbances/injection_scheduler.py`](file:///d:/Hackathon/SIH2.0/HORIZON/coarse-align-x/simulator/disturbances/injection_scheduler.py).
- Profiles: `immediate`, `ramped` (smooth transition), `pulsed` (periodic bursts), and `scheduled`.

### 10. Adversarial Scenarios
Available in [`simulator/disturbances/presets.py`](file:///d:/Hackathon/SIH2.0/HORIZON/coarse-align-x/simulator/disturbances/presets.py):
- `DISTRACTOR_BURST`, `OCCLUSION_EVENT`, `BRIGHTNESS_FADE`, `JITTER_BURST`, `PLATFORM_SWING`, `COMBINED_TURBULENCE`.

### 11. Counterfactual Compatibility & Ablation Analysis
- Supported via `ablate_module: Optional[str]` parameter in [`DisturbancePipeline.apply()`](file:///d:/Hackathon/SIH2.0/HORIZON/coarse-align-x/simulator/disturbances/pipeline.py#L93).
- Enables exact seed replay where one disturbance module is removed while maintaining identical RNG streams for all other modules.

---

## Verification & Regression Status

- **Phase 3 Extension Unit Tests**: `pytest tests/test_phase3_disturbance_upgrade.py` -> **7/7 PASSED**
- **Full Workspace Regression**: `pytest` -> **568/568 PASSED** (100% pass rate).
