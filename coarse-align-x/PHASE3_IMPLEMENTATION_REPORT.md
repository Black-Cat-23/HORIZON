# PHASE 3 — DISTURBANCE, SENSOR NOISE & PLATFORM MOTION IMPLEMENTATION REPORT

**Project:** HORIZON (SIH26169)  
**Role:** Simulation & Disturbance Systems Engineer  
**Phase:** 3 — Disturbance, Sensor Noise & Platform Motion Engine  
**Status:** ALL PHASE 3 REQUIREMENTS COMPLETED & VERIFIED  
**Date:** 2026-09-04  

---

## 1. Implementation Summary

Phase 3 introduces a dedicated, modular, and mathematically verified Disturbance Engine for HORIZON. The engine transforms clean, uncorrupted optical camera frames ($640 \times 480$, uint8) into disturbed sensor observations simulating real mobile platform vibrations, high-frequency optical jitter, atmospheric degradations (Clear, Haze, Fog, Rain, Low Light), and quantum/analog sensor noise (Salt & Pepper, Gaussian, Poisson).

### Critical System Invariants Enforced:
1. **Ground Truth Integrity:**
   - Disturbances **NEVER** modify ground-truth target kinematics ($x, y, v_x, v_y, a_x, a_y$) or camera gimbal states ($\theta_{\text{pan}}, \theta_{\text{tilt}}$).
   - Disturbances only modify the sensor frame observation and observation telemetry.
2. **Clean vs. Disturbed Frame Separation:**
   - Both `clean_frame` and `disturbed_frame` are stored and accessible on `VirtualCamera` and `SimulationEngine`.
3. **Official SIH Limit Enforcement:**
   - Gaussian noise: $\sigma \le 20.0$ pixels (strictly validated; values $> 20$ rejected).
   - Camera jitter: zero-mean image-plane displacement $\le \pm 20.0$ pixels/frame.
   - Platform motion: continuous stateful translation $\le \pm 20.0$ pixels/frame.
   - Salt & Pepper: configurable probability (default $0.10 \approx 10\%$).
   - Atmosphere: 5 conditions (CLEAR, HAZE, FOG, RAIN, LOW_LIGHT).
4. **Deterministic Randomness:**
   - Isolated NumPy child generators (`salt_pepper`, `gaussian`, `poisson`, `jitter`, `platform`) derived from `SeedManager`. Zero access to global `np.random`.
5. **No Scope Creep:**
   - Zero AI, zero YOLO, zero Kalman/EKF, zero PID/PAT controllers.

---

## 2. Architecture Changes

### Sensor Pipeline Progression
```
WORLD (2000×2000 uint8)
  ↓
TARGET (Subpixel beacon)
  ↓
VIRTUAL CAMERA (Intrinsics, 4°×3° FOV, 30 Hz)
  ↓
640×480 CLEAN SENSOR FRAME (`clean_frame`) ────→ Preserved as ground-truth image
  ↓
DISTURBANCE PIPELINE (`DisturbancePipeline`)
  ├─ 1. Platform Motion Stage (Continuous stateful offset, max ±20 px/frame)
  ├─ 2. Atmospheric Degradation (Contrast & brightness reduction)
  ├─ 3. Sensor Noise Injection:
  │    ├─ Salt & Pepper (default p=0.10)
  │    ├─ Additive Gaussian (N(0, σ²), max σ=20 px)
  │    └─ Poisson Shot Noise (Photon counting statistics)
  └─ 4. Camera Jitter (Zero-mean image translation, max ±20 px/frame)
  ↓
640×480 DISTURBED SENSOR FRAME (`disturbed_frame`)
  ↓
LATER: PHASE 4 PERCEPTION (Beacon Centroid Detection)
```

---

## 3. Files Added

| File Path | Description |
| :--- | :--- |
| `simulator/disturbances/__init__.py` | Package initialization and public API export. |
| `simulator/disturbances/config.py` | Typed dataclasses (`DisturbanceConfig`, etc.) and SIH parameter validators. |
| `simulator/disturbances/noise.py` | Vectorized Salt & Pepper, Gaussian ($\sigma \le 20$), and Poisson shot noise engines. |
| `simulator/disturbances/atmosphere.py` | Mathematical atmospheric contrast/brightness degradation (5 conditions). |
| `simulator/disturbances/jitter.py` | Image-plane optical line-of-sight camera jitter engine ($\le \pm 20$ px). |
| `simulator/disturbances/platform.py` | Stateful continuous platform motion engine ($\le \pm 20$ px/frame, Linear & optional models). |
| `simulator/disturbances/pipeline.py` | Central `DisturbancePipeline` orchestrator and telemetry collector. |
| `simulator/disturbances/presets.py` | Predefined presets (NOMINAL, DIFFICULT, SEVERE, RECOVERY, ADVERSARIAL, CUSTOM). |
| `benchmarks/profile_phase3.py` | Empirical execution time profiler (Mean, Median, P95, Max). |
| `tests/test_disturbances_noise.py` | Unit tests for Salt & Pepper, Gaussian, and Poisson noise. |
| `tests/test_disturbances_jitter.py` | Unit tests for camera jitter bounds, distributions, and determinism. |
| `tests/test_disturbances_platform.py`| Unit tests for platform continuity, bounds, linear and optional models. |
| `tests/test_disturbances_atmosphere.py`| Unit tests for 5 atmospheric conditions and parameter monotonicity. |
| `tests/test_disturbances_pipeline.py`| Integration tests for pipeline composition and ground truth invariance. |
| `tests/test_disturbances_determinism.py`| Determinism and seed divergence verification tests. |
| `DISTURBANCE_MODEL.md` | Formal mathematical specification and parameter taxonomy document. |
| `PHASE3_IMPLEMENTATION_REPORT.md` | This formal implementation and verification report. |

---

## 4. Files Modified

| File Path | Changes |
| :--- | :--- |
| `simulator/camera/camera.py` | Added `last_clean_observation`, `last_disturbed_observation`, and `set_disturbed_observation()`. |
| `simulator/core/config.py` | Added `DisturbanceConfig` to `AppConfig`, YAML parsing, and strict disturbance validation. |
| `simulator/core/recorder.py` | Extended `GroundTruthRecord` and `record_frame()` with all 19 Phase 3 telemetry fields. |
| `simulator/core/simulation.py` | Initialized `DisturbancePipeline`, applied disturbances on capture, exposed `get_clean_frame()` and `get_disturbed_frame()`. |
| `simulator/visualization/debug_view.py` | Upgraded to triple viewports: Macro World, Clean Sensor Feed (Left), Disturbed Sensor Feed (Right), live disturbance telemetry, and PNG snapshot export. |
| `main.py` | Added `--preset` CLI argument to select disturbance presets in headless or GUI mode. |

---

## 5. Disturbance Equations & Models

### 5.1. Gaussian Noise (Additive)
$$I_{\text{gauss}}(u, v) = \text{round}\left(\text{clip}\left(I(u, v) + \eta, 0.0, 255.0\right)\right), \quad \eta \sim \mathcal{N}\left(0, \sigma^2\right)$$
Enforced constraint: $0.0 \le \sigma \le 20.0$ pixels.

### 5.2. Salt & Pepper Noise (Impulse)
For pixel $(u, v)$ with uniform draw $\xi \sim U(0, 1)$:
$$I_{\text{sp}}(u, v) = \begin{cases} 255 & \text{if } \xi < \frac{p}{2} \\ 0 & \text{if } \frac{p}{2} \le \xi < p \\ I(u, v) & \text{otherwise} \end{cases}$$
Configurable probability $p \in [0.0, 1.0]$, default $p = 0.10$.

### 5.3. Poisson Shot Noise
$$\lambda(u, v) = I(u, v) \times \frac{\Phi_{\text{peak}}}{255.0}, \quad k \sim \text{Poisson}(\lambda(u, v)), \quad I_{\text{poisson}}(u, v) = \text{round}\left(\text{clip}\left(k \times \frac{255.0}{\Phi_{\text{peak}}}, 0.0, 255.0\right)\right)$$

### 5.4. Atmospheric Degradation
$$I_{\text{atmos}}(u, v) = \text{round}\left(255.0 \times \text{clip}\left(c \cdot \frac{I(u, v)}{255.0} + b, 0.0, 1.0\right)\right)$$
CLEAR: $c=1.0, b=0.0$; HAZE: $c=0.65, b=+0.12$; FOG: $c=0.35, b=+0.25$; RAIN: $c=0.70, b=-0.05$; LOW_LIGHT: $c=0.85, b=-0.40$.

### 5.5. Camera Jitter & Platform Motion
- **Jitter:** $\delta x, \delta y \in [-j_{\max}, +j_{\max}]$, with $j_{\max} \le 20.0$ px.
- **Platform:** Continuous stateful integration: $\Delta x = \text{clamp}(v_x \Delta t, -20.0, 20.0)$ px/frame.

---

## 6. Configuration & Taxonomy

All parameters are categorized per engineering standards:
- **OFFICIAL SIH:** Gaussian max $\sigma = 20.0$ px, Jitter max $\pm 20.0$ px/frame, Platform max $\pm 20.0$ px/frame, S&P reference $\approx 10\%$, Conditions: CLEAR, HAZE, FOG, RAIN, LOW_LIGHT.
- **PROJECT DEFAULT:** Atmospheric $c$ and $b$ factors, Poisson $\Phi_{\text{peak}} = 50.0$, platform boundary limit $100.0$ px.
- **USER CONFIGURABLE:** All fields exposed via `DisturbanceConfig` and YAML / CLI.

---

## 7. Verification & Test Results

The full automated test suite was executed via `pytest -v`:

```
============================= 178 passed in 7.68s =============================
```

### Breakdown by Category:
- **Phase 1 & Phase 2 Regressions:** 130 / 130 tests **PASSED**
- **Phase 3 Sensor Noise (S&P, Gaussian, Poisson):** 13 / 13 tests **PASSED**
- **Phase 3 Camera Jitter:** 6 / 6 tests **PASSED**
- **Phase 3 Platform Motion:** 5 / 5 tests **PASSED**
- **Phase 3 Atmospheric Degradation:** 6 / 6 tests **PASSED**
- **Phase 3 Pipeline Composition & Ground Truth Invariance:** 16 / 16 tests **PASSED**
- **Phase 3 Seed Determinism & Divergence:** 2 / 2 tests **PASSED**
- **TOTAL:** **178 / 178 tests PASSED (100%)**

---

## 8. Empirical Performance Profiling Measurements

Micro-benchmarked on $640 \times 480$ grayscale sensor frames over 100 continuous iterations:

| Component Stage | Mean (ms) | Median (ms) | P95 (ms) | Max (ms) |
| :--- | :---: | :---: | :---: | :---: |
| **Salt & Pepper ($p=0.10$)** | 2.519 ms | 2.405 ms | 3.134 ms | 4.608 ms |
| **Gaussian Noise ($\sigma=20.0$)** | 8.798 ms | 8.487 ms | 10.613 ms | 13.066 ms |
| **Poisson Shot Noise ($\Phi=30$)** | 27.070 ms | 26.898 ms | 29.379 ms | 34.979 ms |
| **Atmospheric Degradation (Fog)** | 5.981 ms | 5.925 ms | 6.896 ms | 10.531 ms |
| **Camera Jitter (Affine $\pm 15$ px)** | 0.525 ms | 0.459 ms | 0.804 ms | 1.216 ms |
| **Platform Motion (Linear Step)** | 0.457 ms | 0.434 ms | 0.586 ms | 0.905 ms |
| **FULL PIPELINE (ADVERSARIAL: All Simultaneous)** | **38.342 ms** | **37.962 ms** | **40.567 ms** | **51.194 ms** |

*Note: Under worst-case ADVERSARIAL stress (all 5 disturbances simultaneously active at official maximum parameters), pipeline execution is $\approx 38.3$ ms ($\approx 26$ FPS), satisfying the preliminary $>20$ FPS sensor update constraint.*

---

## 9. Telemetry Export Verification

Exported CSV schema confirmed in `data/ground_truth/phase3_test_export.csv`:
All 45 columns verified, including:
`disturbance_enabled`, `salt_pepper_enabled`, `salt_pepper_probability`, `gaussian_enabled`, `gaussian_sigma`, `poisson_enabled`, `poisson_parameter`, `camera_jitter_enabled`, `camera_jitter_x`, `camera_jitter_y`, `platform_motion_enabled`, `platform_model`, `platform_offset_x`, `platform_offset_y`, `platform_velocity_x`, `platform_velocity_y`, `atmosphere_enabled`, `atmosphere_condition`, `contrast_factor`, `brightness_factor`.

---

## 10. Known Limitations

1. **Optical Scintillation Approximation:** Phase 3 models atmospheric degradation via contrast and brightness attenuation per the SIH specification. Full wave-optics split-step phase screens are deliberately omitted to avoid uncalibrated computational overhead.
2. **Fixed Sensor Resolution:** Viewport remains $640 \times 480$ per SIH intrinsics.

---

## 11. Interface Exposed to Phase 4 (Perception Engine)

Phase 4 perception algorithms will interface directly with the following clean APIs:

```python
# 1. Access latest disturbed observation frame for beacon detection:
frame_to_detect = engine.get_camera_frame()        # 480×640 uint8 numpy array

# 2. Access clean frame for clean vs. disturbed detector evaluation:
clean_frame = engine.get_clean_frame()             # 480×640 uint8 numpy array

# 3. Access current ground-truth target pixel projection for IoU / Centroid error evaluation:
_, _, u_true, v_true, in_fov = engine.camera.project_target(state.x, state.y)

# 4. Access live disturbance telemetry metadata:
telemetry = engine.last_disturbance_telemetry
```

---

PHASE 3 IMPLEMENTATION COMPLETE — WAITING FOR VERIFICATION
