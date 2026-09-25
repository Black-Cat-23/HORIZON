# HORIZON Screen Specification

This document details the functional purpose, layout structure, content elements, and design principles for each of the 5 operational screens in HORIZON.

---

## 1. Mission Control Screen (Mode 0)

### Purpose
Mission Control is where an operational experiment or scenario is defined before execution. It provides a visual scenario gallery, interactive configuration form, plain-text resolved summary, and static trajectory preview.

### Layout Structure
- **Top / Main Grid**: Split 2-column layout.
  - **Left Column**: `ScenarioGalleryWidget` (13 scenario tiles).
  - **Right Column (Top)**: `ScenarioConfigFormWidget` (Parameter inputs & error banner).
  - **Right Column (Bottom Left)**: `ResolvedConfigSummaryWidget` (Plain-language parameter summary in body font).
  - **Right Column (Bottom Right)**: `ExperimentPreviewWidget` (Static preview map canvas).

### Content & Interaction Rules
- **Sentence-Case Action**: Button labeled `"Launch scenario"`.
- **Text-Primary Body Typography**: Resolved summary text uses body font (`General Sans`), avoiding monospace font for static text blocks.
- **Validation Error Banner**: Displays an inline red alert banner if any parameter is invalid ($t \le 0$, $FPS \le 0$, etc.).

---

## 2. Live Tracking Screen (Mode 1)

### Purpose
The high-stakes main view watched for live tracking demonstrations. Instantly communicates target detection, tracking state, gimbal alignment, and operational telemetry.

### Layout Structure
- **Top**: `MissionStatusStrip` (Simulation controls, speed multipliers, status indicators).
- **Center Main (55–65% Visual Area)**: `HeroSensorView` (640×480 live optical sensor feed & perception overlays).
- **Left Lower**: `WorldOverviewPanel` (2000×2000 macro trajectory canvas, FOV footprint, target path).
- **Right Column**:
  - `PATStateProgressionWidget` (Vertical 5-state PAT stepper).
  - `TelemetryPanel` (Monospace domain readouts).
- **Bottom**: `EventTimelineWidget` (Real event log with timestamps).

### Content & Interaction Rules
- **Plain Sentence-Case Header**: `"Live sensor"`.
- **Search State Discipline**: When in `SEARCH` mode, zero fake target reticles are drawn. Draws clean center crosshair (320, 240) and displays active search pattern telemetry (`Pattern`, `Pan Rate`, `Tilt Rate`, `Elapsed`).
- **Ideal Reference Toggle**: Checkbox labeled `"Ideal sensor reference"` toggles secondary clean optical feed side-by-side.

---

## 3. Track Diagnostics Workstation (Mode 2)

### Purpose
Precision analysis workstation for deep inspection of target state estimation, Kalman filter innovations, and covariance uncertainty.

### Layout Structure
- **Main Viewport (Top Left)**: `TrackGeometryView` (640×480 crop observation with multi-layer diagnostic reticles).
- **Right Column**:
  - `StateEstimatePanel` (State vector $X, Y, V_x, V_y$, Innovation $S$, Uncertainty $P$).
  - `CovarianceDiagnosticPanel` ($1\sigma, 2\sigma, 3\sigma$ selector bank & covariance matrix figures).
  - `HybridPerceptionBreakdownPanel` (Classical, Neural, Agreement, Final confidence).
- **Bottom**: `TimeSeriesAnalyticsWidget` (6 time-series graphs: tracking error, track quality, innovation, pan error, tilt error, detector confidence).

### Content & Interaction Rules
- **Multi-Layer Reticles**: Measured centroid (Red), Estimated centroid (Cyan), Predicted centroid (Amber), Uncertainty ellipse (Scaled by selected $\sigma$), Error vector ray.
- **Offline Evaluation Firewall**: Ground-truth marker appears ONLY when `"Ground-truth evaluation reference [OFFLINE EVAL ONLY]"` toggle is active.

---

## 4. Controlled Disturbance Experiment Room (Mode 3)

### Purpose
Controlled experiment room where judges or engineers deliberately inject optical and kinematic disturbances to observe system response causality.

### Layout Structure
- **Left Column (Width ~300px)**: `DisturbanceControlsWidget` (Preset profiles & sliders/spinboxes).
- **Center Main**: `HeroSensorView` (**REUSED** directly from Phase 11.2 for 100% visual parity!).
- **Right Column (Width ~300px)**: `SystemResponsePanelWidget` (Active disturbance telemetry & system response readouts).

### Content & Interaction Rules
- **Real Backend Controls**: Gaussian sigma, Salt & pepper, Poisson peak photons, Camera jitter, Platform motion, Atmosphere condition.
- **Custom Profile Auto-Switching**: Changing any control manually switches preset combo box to `"CUSTOM"`.
- **Sentence-Case Action**: Button labeled `"Run stress test"`.
- **Enforced Causality**: Zero UI-side interpolation or faking.

---

## 5. Scientific Benchmarking Workstation (Mode 4)

### Purpose
Scientific results room providing distribution-level benchmarking against baselines B0, B1, and B2 using real Phase 10 validation outputs.

### Layout Structure
- **Section 1**: `BaselineComparisonTableWidget` (B0, B1, B2, Ours comparison table with tabular monospace figures).
- **Section 2**: `SameSeedInspectorWidget` (Signature HORIZON side-by-side trial inspector).
- **Section 3**: `DistributionVisualsWidget` (Custom canvas CDF curves and Box plots).
- **Section 4**: `RobustnessHeatmapWidget` (2D parameter grids with explicit `MEASURED` vs `INTERPOLATED` tags).
- **Section 5**: `FailureIntelligenceWidget` (8 failure taxonomy categories with interactive event timeline drill-down).
- **Section 6**: `AblationComparisonWidget` (Architecture ablation study with unified 0–320px scale).
- **Section 7**: `ReportLinksWidget` (Real direct links to saved HTML/Markdown reports and JSON data files).

### Content & Interaction Rules
- **Full Distribution Reporting**: Reports median, P95, P99, RMSE, lock retention, and latency across four columns.
- **Visual Matrix Differentiation**: Solid Cyan border for `MEASURED` cells; Dashed Amber border for `INTERPOLATED` cells.
