# Phase 6 — PAT Mode Manager Specification

## 1. Responsibilities
The `PATModeManager` orchestrates high-level decision making for optical acquisition and tracking. It integrates detector outputs, Kalman estimates, track diagnostics, search strategies, and controller commands.

## 2. Event Log Definitions
Every state transition emits a structured `PATEvent`:

| Event Type | Triggering Condition |
|---|---|
| `SEARCH_STARTED` | System startup or search strategy reset |
| `CANDIDATE_FOUND` | First valid detection ($c \ge 0.35$) in SEARCH |
| `ACQUISITION_STARTED` | Transition into ACQUIRE mode |
| `ACQUISITION_CONFIRMED` | $N=3$ valid frames confirmed |
| `TRACK_STARTED` | Initial entry into TRACK mode |
| `TRACK_DEGRADED` | 2 consecutive misses or $Q_{\text{track}} < 0.3$ |
| `TRACK_RESTORED` | Valid detection recovered during DEGRADED |
| `TARGET_LOST` | 5 consecutive misses in DEGRADED -> REACQUIRE |
| `REACQUISITION_STARTED` | Localized spiral search initiated |
| `REACQUISITION_CONFIRMED` | Target re-detected during reacquisition |
| `SEARCH_TIMEOUT` | Reacquisition search timed out (8.0 s) -> SEARCH |
