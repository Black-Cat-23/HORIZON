# HORIZON Phase 1 — Existing-Foundation Upgrade Audit

**Project:** HORIZON (SIH26169)  
**Phase:** 1 (Upgrade — no new phase created)  
**Role:** Design Systems Analyst / Mathematical Verification Engineer  
**Date:** 2026-09-08  
**Baseline Regression:** 380/380 tests pass before any modification  

---

## 1. Scope

This audit covers all Phase 1 mathematical foundation files before upgrade modifications
are applied. The goal is to document what exists, what is correct, what is missing,
and what (if anything) constitutes a verified mathematical defect.

Operational behavior will NOT be changed unless a verified defect is found.

---

## 2. Files Audited

| File | Role |
|------|------|
| `simulator/camera/intrinsics.py` | Pinhole projection model |
| `simulator/camera/camera.py` | Virtual camera + boresight |
| `simulator/camera/gimbal.py` | Pan/tilt actuator |
| `simulator/world/state.py` | Ground-truth target state |
| `simulator/world/world.py` | World renderer |
| `simulator/world/beacon.py` | Beacon rasterization |
| `simulator/core/config.py` | Configuration schema |
| `simulator/core/simulation.py` | Core orchestration engine |
| `simulator/core/seed_manager.py` | Deterministic RNG hierarchy |
| `simulator/core/clock.py` | Fixed-timestep clock |
| `tests/test_camera_intrinsics.py` | Formal V&V: projection |
| `tests/test_camera_gimbal.py` | Formal V&V: gimbal |
| `tests/test_camera_viewport.py` | Formal V&V: viewport |
| `tests/test_camera_rate.py` | Formal V&V: observation rate |
| `tests/test_seed.py` | SeedManager determinism |
| `tests/test_simulation.py` | Engine integration |

---

## 3. Coordinate Systems Audit

### 3.1 World Coordinate System

- **Origin:** Top-left corner of the 2000×2000 simulation canvas, at pixel `(0, 0)`.
- **+X axis:** Points right (increasing column index).
- **+Y axis:** Points downward (increasing row index).
- **Units:** World pixels. `1 world pixel = 1 meter` at simulation scale (undocumented but implied by the 2000×2000 "meters" world description).
- **Handedness:** Left-handed (Z would point into the screen).
- **Evidence:** `TargetState` docstring: "Coordinate origin: top-left (0, 0). +X: right. +Y: down."

### 3.2 Camera / Boresight Reference Frame

- **Origin:** World position of camera boresight, computed as:
  ```python
  bx = world_center_x + fx * tan(pan_rad)
  by = world_center_y + fy * tan(tilt_rad)
  ```
- **+X:** Corresponds to +pan (rightward in image).
- **+Y:** Corresponds to +tilt (downward in image).
- **Units:** World pixels. Critically, the mapping uses `fx` and `fy` (image focal lengths in pixels) to translate between angular displacement and world-pixel displacement. This is valid **only if world scale = image scale**, i.e., 1 world pixel = 1 image pixel at zero FOV distortion. This is a hidden assumption that is correct for this simulation but is not documented.
- **Handedness:** Left-handed.

### 3.3 Image Coordinate System

- **Origin:** Top-left of 640×480 sensor, at pixel `(0, 0)`.
- **+u axis:** Points right (increasing column).
- **+v axis:** Points downward (increasing row).
- **Units:** Image pixels.
- **Principal point (cx, cy):** Exactly `(W/2, H/2) = (320.0, 240.0)`.
- **Handedness:** Left-handed.

### 3.4 Angular Coordinate System

- **Origin:** Camera boresight direction (`theta_x = 0, theta_y = 0`).
- **+theta_x:** Positive pan angle — target moves rightward in image (+u).
- **+theta_y:** Positive tilt angle — target moves downward in image (+v).
- **Units:** Radians (internally). Degrees used in gimbal state and configuration.
- **Handedness:** Left-handed (consistent with image and world).

### 3.5 Consistency Assessment

| Invariant | Status |
|-----------|--------|
| World +X → Image +u → Angular +theta_x: all rightward | ✅ Consistent |
| World +Y → Image +v → Angular +theta_y: all downward | ✅ Consistent |
| Boresight (0 pan, 0 tilt) → image principal point (cx, cy) | ✅ Verified |
| Positive pan → increasing u (rightward in image) | ✅ Verified (monotonicity test) |
| Positive tilt → increasing v (downward in image) | ✅ Verified (monotonicity test) |
| World-pixel to image-pixel scale: 1:1 at boresight | ✅ Correct (implicit) — needs documentation |

---

## 4. Unit Conversions Audit

| Conversion | Location | Method | Correctness |
|------------|----------|--------|-------------|
| Degrees → Radians | `intrinsics.py`, `camera.py` | `math.radians()` | ✅ |
| Radians → Degrees | `simulation.py` (recording) | `math.degrees()` | ✅ |
| Angular offset → pixel | `intrinsics.project()` | `u = cx + fx*tan(theta)` | ✅ |
| Pixel → angular offset | `intrinsics.unproject()` | `theta = atan((u-cx)/fx)` | ✅ |
| FOV → focal length | `intrinsics.__init__` | `fx = (W/2) / tan(FOV/2)` | ✅ |
| Boresight world pos | `camera.get_boresight_world_pos()` | `bx = cx_world + fx*tan(pan)` | ✅ (implicit scale) |
| Camera angle → pointing error | `camera.compute_target_angles()` | `theta = atan(dx / fx)` | ✅ |

---

## 5. Mathematical Verification Results (Pre-Upgrade)

### 5.1 Camera Intrinsics

- **fx** = 320.0 / tan(2°) = **9163.604603 px**  
- **fy** = 240.0 / tan(1.5°) = **9165.232338 px**  
- **cx** = 320.0, **cy** = 240.0  
- Round-trip error (angle → pixel → angle): < 1e-15 radians  
- FOV consistency: `2 * atan(W/2 / fx) = FOV_x` verified to < 1e-12 relative error  

### 5.2 Projection Model

Formula used:
```
u = cx + fx * tan(theta_x)
v = cy + fy * tan(theta_y)
```
This is the **ideal pinhole tangent projection** (also called "tan-theta" lens model), which is exact for an ideal pinhole camera. It differs from the paraxial approximation (`u ≈ cx + fx * theta`) in the nonlinear tangent term. The implementation uses `tan()` throughout — this is correct and more accurate than the paraxial model.

### 5.3 Gimbal Physics

- Rate limit: ±5.0 deg/s enforced by hard clamp.
- Acceleration limit: ±50.0 deg/s² enforced by delta-rate clamp per step.
- Angular position integrated with Euler method: `pan += rate * dt`.
- No singularity exists (2D pan/tilt, not 3D Euler angles — no gimbal lock).

### 5.4 Deterministic Initialization

- `SeedManager` uses `np.random.SeedSequence` with hierarchical child spawning.
- Named children (`"initial_placement"`, `"random_trajectory"`, etc.) are deterministic per seed.
- **Gap:** Camera initial pointing is always (0°, 0°) — not seeded. Documented below as missing feature.

---

## 6. Missing Features (Non-Defects)

The following are missing features, not mathematical defects. Operational behavior is preserved by not modifying them without explicit design.

| Item | Status | Upgrade Action |
|------|--------|----------------|
| Authoritative coordinate-system contract | Missing | Add `coordinate_contract.py` |
| `CameraCalibration` with explicit fx/fy/cx/cy override | Missing | Extend `intrinsics.py` |
| Lens distortion model | Missing | Add `distortion.py` (disabled by default) |
| Pixel uncertainty → angular uncertainty propagation | Missing | Add to `intrinsics.py` |
| Calibration sensitivity experiment | Missing | Add `test_calibration_sensitivity.py` |
| Camera initial pointing offset via seed | Missing | Add to `config.py` + `simulation.py` |
| Mathematical invariant assertions | Missing | Add `validate_invariants()` + tests |
| Independent reference NumPy tests | Partial (existing tests partially self-referential) | Add `test_independent_reference.py` |
| `PHASE1_CALIBRATION_REPORT.md` | Missing | Create |

---

## 7. Verified Defects Found

**None.** The existing implementation is mathematically correct.

The only clarification needed is documentation of the implicit assumption that world pixel scale = image pixel scale (1:1 correspondence at boresight). This is correct for this simulation architecture and must not be changed.

---

## 8. Baseline Test Summary

```
Platform: Windows 11, Python 3.13.9, pytest 9.1.1
Tests collected: 380
Tests passed:    380
Tests failed:    0
Execution time:  53.29s
```

All modifications in this upgrade must preserve this baseline.

---

## 9. Upgrade Contract

1. Do not change the operational behavior of any existing scenario.
2. Do not modify `CameraIntrinsics.__init__()` signature in a breaking way.
3. Do not enable lens distortion by default — only when `enabled=True` explicitly.
4. Do not leak ground truth into the perception pipeline.
5. All new features must be covered by automated tests.
6. All 380 existing tests must continue to pass after upgrade.
