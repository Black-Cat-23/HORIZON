# PHASE 2 — FORMAL VERIFICATION & VALIDATION REPORT

**Project:** HORIZON (SIH26169)  
**Role:** Verification & Validation Engineer  
**Status:** ALL TESTS PASSED — ZERO REGRESSIONS  
**Date:** 2026-09-04  

---

## 1. Environment
- **Python Version:** 3.13.9 (64-bit AMD64)
- **Operating System:** Windows 11 Pro (10.0.26200-SP0)
- **NumPy Version:** 2.2.5
- **OpenCV Version:** 4.10.0
- **PySide6 Version:** 6.11.2
- **pytest Version:** 9.1.1
- **Repository Commit:** `30262f1` (branch `bhanu`)

---

## 2. Test Suite Summary

| Category | Total Tests | Passed | Failed | Skipped | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Phase 1 Regression** | 94 | 94 | 0 | 0 | **PASS** |
| **Camera Intrinsics & Projection** | 13 | 13 | 0 | 0 | **PASS** |
| **Gimbal & Rate Limiter** | 11 | 11 | 0 | 0 | **PASS** |
| **Viewport & Subpixel** | 5 | 5 | 0 | 0 | **PASS** |
| **Clock, Observation Rate & Export** | 4 | 4 | 0 | 0 | **PASS** |
| **Phase 2 Edge Cases** | 3 | 3 | 0 | 0 | **PASS** |
| **TOTAL** | **130** | **130** | **0** | **0** | **PASS** |

Execution time: **2.00 seconds**.

---

## 3. Phase 1 Regression Results
- **Result:** **PASS** (94/94 tests passed)
- Zero regressions detected across WorldRenderer, Beacon model, deterministic clock, SeedManager, and all 4 mandatory trajectories (Straight, Circular, Figure-8, Random).

---

## 4. Camera Mathematical Verification
- **Configuration:** $W = 640$, $H = 480$, $\text{FOV}_x = 4.0^\circ$, $\text{FOV}_y = 3.0^\circ$.
- **Principal Point:**
  - Expected: $c_x = 320.0$, $c_y = 240.0$
  - Actual: $c_x = 320.0$, $c_y = 240.0$
  - Absolute Error: $0.0$, Relative Error: $0.0$ $\rightarrow$ **PASS**
- **Focal Lengths:**
  - Expected $f_x = \frac{320}{\tan(2^\circ)} = 9163.604603$ px
  - Actual $f_x = 9163.604603$ px (Absolute Error: $< 10^{-12}$, Rel: $< 10^{-15}$) $\rightarrow$ **PASS**
  - Expected $f_y = \frac{240}{\tan(1.5^\circ)} = 9165.232338$ px
  - Actual $f_y = 9165.232338$ px (Absolute Error: $< 10^{-12}$, Rel: $< 10^{-15}$) $\rightarrow$ **PASS**

---

## 5. Projection & Inverse Projection Verification
- **Boresight Check:** $\theta_x = 0, \theta_y = 0 \implies u = 320.0, v = 240.0$ $\rightarrow$ **PASS**
- **Symmetry Check:** $u(+\theta) - c_x = -(u(-\theta) - c_x)$ verified to machine epsilon $\rightarrow$ **PASS**
- **Monotonicity Check:** Verified that $\frac{\partial u}{\partial \theta_x} > 0$ and $\frac{\partial v}{\partial \theta_y} > 0$ across all valid angles $\rightarrow$ **PASS**
- **Round-Trip Error:**
  - Test set: $\theta \in [-1.99^\circ, +1.99^\circ] \times [-1.49^\circ, +1.49^\circ]$
  - Max Error: $< 10^{-15}$ radians
  - RMS Error: $< 10^{-15}$ radians (Tolerance $10^{-12}$) $\rightarrow$ **PASS**

---

## 6. FOV Boundary Verification
Tested 7 discrete geometric boundary conditions:
1. Target exactly at optical axis: **PASS** (Visible)
2. Target slightly inside FOV ($2^\circ - \epsilon, 1.5^\circ - \epsilon$): **PASS** (Visible)
3. Target exactly on horizontal boundary ($2^\circ, 0$): **PASS** (Visible)
4. Target slightly outside horizontal boundary ($2^\circ + \epsilon, 0$): **PASS** (Outside)
5. Target exactly on vertical boundary ($0, 1.5^\circ$): **PASS** (Visible)
6. Target slightly outside vertical boundary ($0, 1.5^\circ + \epsilon$): **PASS** (Outside)
7. Target outside both axes ($2^\circ + \epsilon, 1.5^\circ + \epsilon$): **PASS** (Outside)

---

## 7. Camera Rate-Limit Verification
- **Test spectrum:** Commanded slew rates $\in \{0, \pm 1, \pm 5, \pm 10, \pm 100\}$ deg/s.
- **Actuator Constraint:** Actual slew rate strictly clamped to $\le 5.0^\circ$/s.
- **Maximum Observed Rate:** Exactly $5.0000^\circ$/s $\rightarrow$ **PASS**
- **Command vs Actual Separation:**
  - When commanding $15^\circ$/s: `commanded_rate == 15.0`, `actual_rate == 5.0` $\rightarrow$ **PASS**
- **Acceleration Limiting:**
  - $\left|\frac{\Delta \text{rate}}{\Delta t}\right| \le 50.0^\circ/\text{s}^2$ verified across continuous 120 steps $\rightarrow$ **PASS**

---

## 8. Viewport Verification
- **Observation Dimensions:** Exactly $(480, 640)$, dtype `uint8`, single-channel grayscale $\rightarrow$ **PASS**
- **Not A Resize:** Target pixel count preserves true $10 \times 10$ physical area ($\sim 100$ px), proving the viewport is a physical optical sub-window crop, not a destructive resize of $2000 \times 2000$ $\rightarrow$ **PASS**
- **Dynamic Viewport:** Panning camera changes observed region deterministically $\rightarrow$ **PASS**

---

## 9. Subpixel Verification
- Evaluated subpixel target coordinates ($1000.1, 1000.5, 1000.9$).
- Step delta $\Delta u = 0.400000$ px preserved exactly with zero truncation $\rightarrow$ **PASS**

---

## 10. Determinism Verification
- Experiment A (Seed 42) vs Experiment B (Seed 42): Bit-for-bit identical camera frames, telemetry, and trajectories (`np.array_equal == True`) $\rightarrow$ **PASS**
- Experiment C (Seed 43): Divergent stochastic random motion trajectory $\rightarrow$ **PASS**

---

## 11. Export Verification
- Telemetry exported to `data/ground_truth/phase2_verification_run.csv` and `.json`.
- All fields verified: `camera_pan_deg`, `camera_tilt_deg`, `camera_pan_rate_deg_s`, `camera_tilt_rate_deg_s`, `target_theta_x_deg`, `target_theta_y_deg`, `target_pixel_u`, `target_pixel_v`, `target_in_fov`.
- Readback verified against in-memory records $\rightarrow$ **PASS**

---

## 12. GUI Verification
- PySide6 Debug Viewer (`simulator/visualization/debug_view.py`):
  - Displays dual viewports: Macro 2000×2000 World + 640×480 Optical Camera Feed.
  - Shows camera FOV footprint box and optical boresight crosshairs.
  - Interactive playback controls (Start, Pause, Reset, Trajectory selector, Seed, Duration).
  - Timing is strictly observer-driven (zero impact on fixed 60 Hz simulation clock) $\rightarrow$ **PASS**

---

## 13. Performance Measurements
Benchmarked across 300 real simulation cycles:
- **World Generation Time:**
  - Mean: $0.80$ ms | Median: $0.76$ ms | P95: $0.98$ ms | Max: $2.07$ ms
- **Camera Viewport Extraction Time:**
  - Mean: $0.058$ ms | Median: $0.055$ ms | P95: $0.075$ ms | Max: $0.14$ ms
- **Projection Computation Time:**
  - Mean: $0.0031$ ms | Median: $0.0028$ ms | P95: $0.0051$ ms | Max: $0.022$ ms
- **Total Step Time:**
  - Mean: $1.72$ ms | Median: $1.66$ ms | P95: $2.09$ ms | Max: $4.52$ ms
- **Conclusion:** Step execution time of $1.72$ ms is **nearly 10× faster** than the 60 Hz real-time budget of $16.67$ ms $\rightarrow$ **PASS**

---

## 14. Edge-Case Results
- Target at $(0, 0)$: **PASS**
- Target at $(1999, 1999)$: **PASS**
- Camera pointing beyond world boundaries: **PASS** (Clean background zero-padding)
- Extreme rate commands ($\pm 1000^\circ$/s): **PASS** (Strictly clamped to $5^\circ$/s)
- Repeated start/reset cycles: **PASS**
- Invalid parameters rejected: **PASS**

---

## 15. Code-Quality Audit
- **Zero Global Mutable State:** Verified.
- **Zero Magic Numbers:** Camera dimensions, FOV, and rates are parameterized through `CameraConfig`.
- **Zero Circular Imports:** Verified clean import tree.
- **Coordinate Integrity:** Monotonic, consistent $+X$ right, $+Y$ down.

---

## 16. Documentation Audit
- Clarified distinctions between Official SIH Requirements ($2000 \times 2000$ world, $640 \times 480$ camera, 30 Hz camera update rate, $5^\circ$/s rate limit) and Engineering Assumptions in `README.md`.

---

## 17. Failures
- **None.**

---

## 18. Warnings
- None.

---

## 19. Required Fixes
- None required. All 130 tests pass.

---

## 20. Release Gate Decision

### **PHASE 2 VERIFIED — READY FOR HUMAN REVIEW**
