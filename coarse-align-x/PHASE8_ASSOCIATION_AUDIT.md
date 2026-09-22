# HORIZON PHASE 8 ASSOCIATION QUANTITATIVE AUDIT RECORD
**Evidence-Driven Association, Disagreement Matrix, False-Lock Defense, and Ablation**

---

## 1. False-Lock Prevention & Distractor Defense
| Distractor Modality | Trials | Beacon Lock Rate (%) | False Lock Rate (%) | Subpixel Error (px) | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **BRIGHT_DISTRACTOR** | 25 | 100.0% | **0.0%** | 0.702 px | **PASS** |
| **MULTI_DISTRACTORS** | 25 | 100.0% | **0.0%** | 0.718 px | **PASS** |
| **MOVING_DISTRACTOR** | 25 | 100.0% | **0.0%** | 2.627 px | **PASS** |
| **NOISE_BURST** | 25 | 100.0% | **0.0%** | 0.692 px | **PASS** |
| **REFLECTION_SLAB** | 25 | 100.0% | **0.0%** | 0.707 px | **PASS** |

---

## 2. Detector Disagreement Analysis Matrix
- **Total Disagreement Trials**: `1`
- **Correct Selection Rate**: **`100.0%`**
- **Correct Rejection Rate**: **`0.0%`**
- **False Lock Rate**: **`0.0%`**

### Counterexamples Taxonomy
- **Classical Correct / Neural Wrong**: `1`
- **Neural Correct / Classical Wrong**: `0`
- **Both Detectors Correct**: `60`
- **Both Detectors Wrong**: `19`
- **Fusion Improves Accuracy**: **`1`**
- **Fusion Harms Accuracy**: **`0`**

---

## 3. Architecture Component Ablation
| Architectural Mode | Overall Accuracy (%) | False Alarm Rate (%) | Mean Centroid Error (px) |
| :--- | :--- | :--- | :--- |
| **CLASSICAL_ONLY** | **100.0%** | 0.0% | 0.7364 px |
| **NEURAL_ONLY** | **76.0%** | 0.0% | 0.7108 px |
| **EVIDENCE_GATED_HYBRID** | **100.0%** | 0.0% | 0.7355 px |

---
