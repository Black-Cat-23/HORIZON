# HORIZON PHASE 8 ASSOCIATION QUANTITATIVE AUDIT RECORD
**Evidence-Driven Association, Disagreement Matrix, False-Lock Defense, and Ablation**

---

## 1. False-Lock Prevention & Distractor Defense
| Distractor Modality | Trials | Beacon Lock Rate (%) | False Lock Rate (%) | Subpixel Error (px) | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **BRIGHT_DISTRACTOR** | 25 | 100.0% | **0.0%** | 0.738 px | **PASS** |
| **MULTI_DISTRACTORS** | 25 | 72.0% | **28.0%** | 0.729 px | **FAIL** |
| **MOVING_DISTRACTOR** | 25 | 100.0% | **0.0%** | 2.085 px | **PASS** |
| **NOISE_BURST** | 25 | 100.0% | **0.0%** | 0.740 px | **PASS** |
| **REFLECTION_SLAB** | 25 | 100.0% | **0.0%** | 0.714 px | **PASS** |

---

## 2. Detector Disagreement Analysis Matrix
- **Total Disagreement Trials**: `0`
- **Correct Selection Rate**: **`0.0%`**
- **Correct Rejection Rate**: **`0.0%`**
- **False Lock Rate**: **`0.0%`**

### Counterexamples Taxonomy
- **Classical Correct / Neural Wrong**: `0`
- **Neural Correct / Classical Wrong**: `0`
- **Both Detectors Correct**: `60`
- **Both Detectors Wrong**: `20`
- **Fusion Improves Accuracy**: **`0`**
- **Fusion Harms Accuracy**: **`0`**

---

## 3. Architecture Component Ablation
| Architectural Mode | Overall Accuracy (%) | False Alarm Rate (%) | Mean Centroid Error (px) |
| :--- | :--- | :--- | :--- |
| **CLASSICAL_ONLY** | **100.0%** | 0.0% | 0.7252 px |
| **NEURAL_ONLY** | **82.0%** | 0.0% | 0.6890 px |
| **EVIDENCE_GATED_HYBRID** | **82.0%** | 0.0% | 0.7044 px |

---
