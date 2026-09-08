# HORIZON PHASE 7 PERCEPTION QUANTITATIVE AUDIT RECORD
**Empirical Subsystem Baseline & Robustness Assessment**

---
## 1. Multi-Scale Target Size Robustness (3×3 to 30×30 px)
| Target Scale | Detection Rate (%) | Mean Subpixel Error (px) | P95 Error (px) | Avg Latency (ms) |
| :--- | :--- | :--- | :--- | :--- |
| **3×3 px** | 100.0% | 0.059 | 0.145 | 1.63 ms |
| **5×5 px** | 100.0% | 0.026 | 0.053 | 1.33 ms |
| **8×8 px** | 100.0% | 0.017 | 0.033 | 1.26 ms |
| **10×10 px** | 100.0% | 0.027 | 0.054 | 1.35 ms |
| **15×15 px** | 100.0% | 0.019 | 0.047 | 1.21 ms |
| **20×20 px** | 100.0% | 0.019 | 0.030 | 1.31 ms |
| **25×25 px** | 100.0% | 0.019 | 0.040 | 1.23 ms |
| **30×30 px** | 100.0% | 0.009 | 0.016 | 1.43 ms |

---
## 2. Disturbance & Environmental Robustness (11 Independent Conditions)
| Disturbance Condition | Detection Rate (%) | Mean Centroid Error (px) | Mean Confidence |
| :--- | :--- | :--- | :--- |
| **CLEAN_BASELINE** | 100.0% | 0.030 | 0.964 |
| **GAUSSIAN_NOISE (sigma=20)** | 100.0% | 0.172 | 0.856 |
| **SALT_AND_PEPPER (5%)** | 100.0% | 0.050 | 0.793 |
| **POISSON_SHOT_NOISE** | 100.0% | 0.032 | 0.962 |
| **MOTION_BLUR (angle=45, len=15)** | 100.0% | 0.507 | 0.934 |
| **ATMOSPHERIC_FOG** | 100.0% | 0.035 | 0.952 |
| **ATMOSPHERIC_HAZE** | 100.0% | 0.032 | 0.962 |
| **ATMOSPHERIC_RAIN** | 92.0% | 0.081 | 0.799 |
| **LOW_LIGHT_SNR (intensity=45)** | 100.0% | 0.194 | 0.677 |
| **PARTIAL_OCCLUSION (50%)** | 52.0% | 0.209 | 0.493 |
| **ADVERSARIAL_COMPOUND** | 100.0% | 0.154 | 0.661 |

---
## 3. False-Target Defense & Distractor Rejection
| Scenario / Distractor Type | Trials | False Alarms | False Alarm Rate (%) | Rejection Rate (%) |
| :--- | :--- | :--- | :--- | :--- |
| **SINGLE_DISTRACTOR (elongated glint)** | 20 | 0 | 0.0% | **100.0%** |
| **MULTI_DISTRACTORS (4 glints)** | 20 | 0 | 0.0% | **100.0%** |
| **NOISE_CLUSTERS (isolated Gaussian blobs)** | 20 | 0 | 0.0% | **100.0%** |
| **SPECULAR_REFLECTION (flat high-intensity slab)** | 20 | 0 | 0.0% | **100.0%** |
| **BLACK_EMPTY_FRAME (no beacon)** | 20 | 0 | 0.0% | **100.0%** |

---
## 4. Confidence Calibration & Reliability
- **Expected Calibration Error (ECE)**: `0.0325`
- **Maximum Calibration Error (MCE)**: `0.0691`
- **Brier Score**: `0.0017`

---
## 5. Latency & Computational Budget Breakdown
- **Video Frame Decoding Latency**: `1.118 ms`
- **Adaptive Preprocessing & Background Est**: `0.240 ms`
- **Multi-Scale Candidate Extraction**: `0.555 ms`
- **Subpixel Centroid Refinement (CoG)**: `0.078 ms`
- **Total End-to-End Perception Latency**: **`1.138 ms`** *(Frame budget: 16.6 ms at 60 FPS, 33.3 ms at 30 FPS)*
