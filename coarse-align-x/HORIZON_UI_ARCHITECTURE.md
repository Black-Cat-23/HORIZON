# HORIZON UI Architecture Specification

## 1. Overview & System Scope
HORIZON is a mission-critical AI Virtual Camera Pointing, Acquisition, and Tracking (PAT) Operational & Diagnostic Console for Free-Space Optical Communication (FSOC) Mobile Terminals. The Phase 11 UI Architecture implements a 5-mode instrument bank architecture built on PySide6 (Qt 6.x), driven deterministically by the underlying C++/Python simulation backend, optical detectors, Kalman filter state estimators, and PAT closed-loop mode manager.

```
                                  +---------------------------------------+
                                  |           Global Header               |
                                  | (Title, State Pill, Mode, Clock, Exp) |
                                  +---------------------------------------+
                                                     |
                                  +---------------------------------------+
                                  |        ModeSelectorBank Switcher      |
                                  |  [Mission | Live | Track | Stress | Bch] |
                                  +---------------------------------------+
                                                     |
                                   +-------------------------------------+
                                   |          QStackedWidget             |
                                   +-------------------------------------+
                                     /       |       |        \        \
                                    /        |       |         \        \
                                Mode 0    Mode 1   Mode 2    Mode 3    Mode 4
                               Mission    Live     Track     Stress   Benchmark
```

---

## 2. Component Taxonomy & Layout Hierarchy

### Application Shell Structure (`simulator/ui/shell/app_shell.py`)
- **`GlobalHeader`** (`simulator/ui/shell/header.py`):
  - Persistent operational toolbar across all screens.
  - Displays project identity `"HORIZON"`, state tag pill, active operational mode, simulation clock ($t_{sim}$), and experiment ID.
- **`ModeSelectorBank`** (`simulator/ui/shell/bank_switcher.py`):
  - 5-mode tab switcher (`Mission Control`, `Live Tracking`, `Track Diagnostics`, `Stress Testing`, `Benchmark Workstation`).
  - Emits mode index signals with 320ms cross-fade vertical settle animation (`OutCubic`).
- **`QStackedWidget`**:
  - Encapsulates the 5 primary workstation screen views.

### Screen Component Breakdown
1. **Mission Screen View (`simulator/ui/mission/mission_screen.py`)**:
   - `ScenarioGalleryWidget`: 13 scenario tiles with mathematical path preview generator.
   - `ScenarioConfigFormWidget`: Parameter configuration form with explicit error banner validation.
   - `ResolvedConfigSummaryWidget`: Plain-text parameters summary (body typography in text-primary).
   - `ExperimentPreviewWidget`: Static mathematical preview map canvas.
2. **Live Screen View (`simulator/ui/live/live_screen.py`)**:
   - `MissionStatusStrip`: Real-time simulation control toolbar (`LAUNCH`, `RESET`, speed multipliers).
   - `HeroSensorView`: Reusable 640×480 optical feed viewport with detection/estimation reticles and optional ideal reference canvas.
   - `WorldOverviewPanel`: 2000×2000 macro trajectory map canvas showing gimbal FOV footprint and target path history.
   - `PATStateProgressionWidget`: Vertical 5-state PAT stepper (`SEARCH` $\rightarrow$ `ACQUIRE` $\rightarrow$ `TRACK` $\rightarrow$ `DEGRADED` $\rightarrow$ `REACQUIRE`).
   - `TelemetryPanel`: Monospace domain readouts for tracking error, gimbal angles, signal power, SNR, FPS.
   - `EventTimelineWidget`: Dynamic real-time event log list with timestamps.
3. **Track Screen View (`simulator/ui/track/track_screen.py`)**:
   - `TrackGeometryView`: 640×480 observation feed with multi-layer diagnostic reticles (measured, estimated, predicted, covariance uncertainty ellipse, error vector ray, and optional offline evaluation ground-truth marker).
   - `TimeSeriesAnalyticsWidget`: 6 time-series graphs (tracking error, track quality, innovation, pan error, tilt error, detector confidence).
   - `CovarianceDiagnosticPanel`: $\sigma$-level selector bank ($1\sigma, 2\sigma, 3\sigma$) and covariance matrix readouts ($P_{xx}, P_{yy}$, semi-axes).
   - `StateEstimatePanel`: Live state vector readouts ($X, Y, V_x, V_y$, Innovation $S$, Uncertainty $P$) with single-line context labels.
   - `HybridPerceptionBreakdownPanel`: Classical, neural, agreement, and final hybrid confidence breakdown.
4. **Stress Screen View (`simulator/ui/stress/stress_screen.py`)**:
   - `DisturbanceControlsWidget`: Preset profiles (`NOMINAL`, `DIFFICULT`, `SEVERE`, `RECOVERY`, `ADVERSARIAL`, `CUSTOM`), disturbance parameter sliders/spinboxes, and `"Run stress test"` action.
   - `HeroSensorView`: **REUSED** directly from Phase 11.2 (`simulator/ui/live/hero_sensor_view.py`) for visual parity and trustworthiness.
   - `SystemResponsePanelWidget`: Active disturbance telemetry and real backend system response readouts.
5. **Benchmark Screen View (`simulator/ui/benchmark/benchmark_screen.py`)**:
   - `BaselineComparisonTableWidget`: B0, B1, B2, Ours comparison table with monospace tabular figures and full distribution metrics.
   - `SameSeedInspectorWidget`: Side-by-side trial inspection under identical random seed.
   - `DistributionVisualsWidget`: Custom PySide6 painter canvas for CDF curves and Box plots across metrics.
   - `RobustnessHeatmapWidget`: 2D parameter grid with explicit `MEASURED` (solid cyan border) vs `INTERPOLATED` (dashed amber border) cell distinction.
   - `FailureIntelligenceWidget`: 8 failure taxonomy categories with interactive event timeline drill-down.
   - `AblationComparisonWidget`: Architecture ablation study with unified scale (0–320 px error).
   - `ReportLinksWidget`: Real direct links opening local validation reports and JSON data files.

---

## 3. Data Flow Architecture

```
                                +---------------------------+
                                |  SimulationEngine         |
                                |  (Core Deterministic Clock|
                                |   & Kinematics)           |
                                +---------------------------+
                                              |
                        +---------------------+---------------------+
                        |                                           |
           +--------------------------+               +--------------------------+
           | HybridBeaconDetector     |               | DisturbancePipeline      |
           | (Classical + Neural Yolo)|               | (Noise, Jitter, Motion)  |
           +--------------------------+               +--------------------------+
                        |                                           |
           +--------------------------+                             |
           | Track & Kalman Estimator |                             |
           | (StateEstimate, P, S)    |                             |
           +--------------------------+                             |
                        |                                           |
           +--------------------------+                             |
           | PATModeManager & Ctrl    |                             |
           | (SEARCH->ACQUIRE->TRACK) |                             |
           +--------------------------+                             |
                        |                                           |
                        +---------------------+---------------------+
                                              |
                                              v
                               +-----------------------------+
                               |     PySide6 UI Layer        |
                               | (No local interpolation!    |
                               |  Strict backend readouts)   |
                               +-----------------------------+
```

### Data Flow Principles
1. **Single Source of Truth**: All frames, telemetry figures, state transitions, and evaluation metrics originate exclusively from real backend engine objects (`SimulationEngine`, `HybridBeaconDetector`, `Track`, `PATModeManager`).
2. **Zero Local Interpolation**: UI widgets never animate, interpolate, or fake telemetry or disturbance responses locally. Every displayed change is driven by an actual reprocessed frame or simulation step.
3. **Strict Ground-Truth Firewall**: Ground-truth coordinates ($x, y$) are completely isolated from operational estimation, detection, and control algorithms. Ground-truth overlay markers appear ONLY on diagnostic canvases when an explicit offline evaluation toggle is enabled.
