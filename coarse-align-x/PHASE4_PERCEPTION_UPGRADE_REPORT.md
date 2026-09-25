# PHASE 4 CLASSICAL PERCEPTION UPGRADE REPORT

**Project:** HORIZON (SIH26169)
**Status:** IMPLEMENTED & VERIFIED - 94/94 Tests Pass
**Date:** 2026-09-08

## 1. Upgrade Summary

All 11 requirements from the Phase 4 Perception Upgrade prompt have been implemented:

1. Multi-Scale Beacon Handling: 5x5, 10x10, 15x15, 20x20 via dynamic area range and size_plausibility scoring across all 4 scales.

2. Adaptive Background Model: Per-candidate annular background model in estimate_local_background(). Exposes bg_mean, bg_variance, local_contrast.

3. Adaptive Threshold: T = clamp(mu_bg + max(15, 3.5*sigma_noise), 30, 250). Responds to local SNR conditions.

4. Multi-Candidate Representation: All valid candidates kept with 15+ fields: location, size, contrast, intensity, shape, score, quality, uncertainty.

5. Optical Shape Validation: 5 independent shape dimensions: circularity, compactness, symmetry, radial_consistency, size_plausibility.

6. Subpixel Refinement: Weighted CoG with moment-based uncertainty. Gaussian fit with covariance-matrix uncertainty.

7. Centroid Uncertainty: sigma_u_px, sigma_v_px from photon-noise statistics only. No ground truth.

8. Detection Quality Metrics: DetectionQuality dataclass - 15 named fields, not one opaque number.

9. False-Lock Defense: 5 independent gates + marginal edge-only candidate suppression.

10. Edge/Clipping: clipped_by_edge flag per candidate. Score penalty. Not auto-rejected.

11. Diagnostics/Profiling: Per-stage timing, full diagnostic visual artifacts.

## 2. Files Modified

- simulator/perception/preprocessing.py: Added estimate_local_background()
- simulator/perception/candidate.py: BeaconCandidate extended to 15 fields, multi-scale, shape validation, uncertainty, edge detection
- simulator/perception/centroid.py: All centroid methods return (u, v, sigma_u, sigma_v) with uncertainty propagation
- simulator/perception/detector.py: New DetectionQuality + upgraded DetectionResult + 8-stage pipeline
- simulator/perception/config.py: max_area_px = 900 for 20x20 support
- simulator/perception/sota_detector.py: Updated for new BeaconCandidate/DetectionResult API
- simulator/perception/__init__.py: Added DetectionQuality to public API

## 3. Mathematical Foundations

Adaptive Threshold: T = clamp(mu_bg + max(15, 3.5 * sigma_noise), 30, 250)
Annular Background: bg_mean, bg_variance, local_contrast from ring around candidate
Size Plausibility: min(area, s*s) / max(area, s*s) for best s in {5, 10, 15, 20}
CoG Uncertainty: sigma_u = sqrt(sum(w_i*(u_i-u_c)^2) / sum(w_i))
Gaussian Fit Uncertainty: sigma_u, sigma_v from sqrt(diag(pcov))

## 4. Verification

94/94 tests passing in tests/test_perception.py
Multi-scale: 5x5, 10x10, 15x15, 20x20 all detected at 8 grid positions
Subpixel accuracy: < 0.45 px on clean frames
Ground-truth leakage: Zero (AST audit verified)
Memory stability: 1000+ frames, no growth
Determinism: identical frames produce identical results

PHASE 4 CLASSICAL PERCEPTION UPGRADE COMPLETE
