# HORIZON PHASE 8 ASSOCIATION QUANTITATIVE AUDIT RECORD
**Evidence-Driven Association, Disagreement Matrix, False-Lock Defense, and Ablation**

---

## 1. False-Lock Prevention & Distractor Defense
| Distractor Modality | Trials | Beacon Lock Rate (%) | False Lock Rate (%) | Subpixel Error (px) | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **BRIGHT_DISTRACTOR** | 25 | 100.0% | **0.0%** | 0.698 px | **PASS** |
| **MULTI_DISTRACTORS** | 25 | 100.0% | **0.0%** | 0.703 px | **PASS** |
| **MOVING_DISTRACTOR** | 25 | 100.0% | **0.0%** | 3.323 px | **PASS** |
| **NOISE_BURST** | 25 | 100.0% | **0.0%** | 0.718 px | **PASS** |
| **REFLECTION_SLAB** | 25 | 100.0% | **0.0%** | 0.687 px | **PASS** |

---

## 2. Detector Disagreement Analysis Matrix
- **Total Disagreement Trials**: `42`
- **Correct Selection Rate**: **`100.0%`**
- **Correct Rejection Rate**: **`0.0%`**
- **False Lock Rate**: **`0.0%`**

### Counterexamples Taxonomy
- **Classical Correct / Neural Wrong**: `42`
- **Neural Correct / Classical Wrong**: `0`
- **Both Detectors Correct**: `20`
- **Both Detectors Wrong**: `18`
- **Fusion Improves Accuracy**: **`42`**
- **Fusion Harms Accuracy**: **`0`**

---

## 3. Architecture Component Ablation
| Architectural Mode | Overall Accuracy (%) | False Alarm Rate (%) | Mean Centroid Error (px) |
| :--- | :--- | :--- | :--- |
| **CLASSICAL_ONLY** | **100.0%** | 0.0% | 0.6915 px |
| **NEURAL_ONLY** | **24.0%** | 0.0% | 0.0000 px |
| **EVIDENCE_GATED_HYBRID** | **100.0%** | 0.0% | 0.6892 px |

---
