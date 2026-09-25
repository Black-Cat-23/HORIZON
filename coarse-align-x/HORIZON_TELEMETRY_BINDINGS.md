# HORIZON Telemetry Bindings Specification

## 1. Telemetry Architecture Overview

All UI readouts across all 5 screens are strictly bound to genuine backend telemetry fields emitted by the `SimulationEngine` (`simulator/core/engine.py`) and `PATStateMachine` (`pat/pat_fsm.py`). No fake values, random noise generators, or mock counters exist in the presentation layer.

---

## 2. Screen-by-Screen Telemetry Bindings

### Screen 1: Live Screen
| Visual Element / Widget | UI Metric Label | Backend Source Object | Backend Field Name | Units |
| :--- | :--- | :--- | :--- | :--- |
| `GlobalHeader` | PAT State Badge | `PATStateMachine` | `state.name` | Enum (`SEARCH`, `ACQUIRE`, `TRACK`, `DEGRADED`, `REACQUIRE`) |
| `GlobalHeader` | Elapsed Time | `SimulationState` | `current_time` | `s` |
| `HeroSensorView` | Sensor Video Frame | `CameraSensor` | `render_frame()` | BGR Image Array (`480x640`) |
| `HeroSensorView` | Bounding Box Overlay | `YOLOv8Detector` | `detection.bbox_xywh` | `px` |
| `WorldOverviewPanel` | Target Coordinates | `TrajectoryGenerator` | `target_position_xyz` | `m` |
| `WorldOverviewPanel` | Gimbal Orientation | `GimbalModel` | `gimbal_az_el_deg` | `deg` |
| `PATStateProgressionWidget` | Active FSM Node | `PATStateMachine` | `current_state` | State Node |
| `TelemetryPanel` | Tracking Error RMS | `TelemetryData` | `tracking_error_rms_urad` | `µrad` |
| `TelemetryPanel` | Azimuth Angle | `GimbalModel` | `azimuth_rad` | `rad` |
| `TelemetryPanel` | Elevation Angle | `GimbalModel` | `elevation_rad` | `rad` |
| `TelemetryPanel` | Covariance Norm | `EKFEstimator` | `P_covariance_norm` | `rad²` |
| `TelemetryPanel` | Detection Confidence | `YOLOv8Detector` | `confidence_score` | `%` |
| `EventTimelineWidget` | FSM Transition Events | `PATStateMachine` | `event_log` | ISO Timestamp + String Event |

---

### Screen 2: Mission Screen
| Visual Element / Widget | UI Metric Label | Backend Source Object | Backend Field Name | Units |
| :--- | :--- | :--- | :--- | :--- |
| `ScenarioGalleryWidget` | Scenario Difficulty | `ScenarioDefinition` | `difficulty` | Category Label |
| `ScenarioConfigFormWidget` | Sim Frequency | `AppConfig.simulation` | `frequency_hz` | `Hz` |
| `ScenarioConfigFormWidget` | Sim Duration | `AppConfig.simulation` | `duration_seconds` | `s` |
| `ScenarioConfigFormWidget` | Disturbance Noise | `AppConfig.disturbance` | `sensor_noise_sigma` | `px` |
| `ResolvedConfigSummaryWidget` | Total Step Count | `AppConfig` | `total_steps()` | Steps |
| `ExperimentPreviewWidget` | World Path Preview | `ScenarioDefinition` | `generate_preview_path()` | `(x, y)` World Meter Coordinates |

---

### Screen 3: Track Screen
| Visual Element / Widget | UI Metric Label | Backend Source Object | Backend Field Name | Units |
| :--- | :--- | :--- | :--- | :--- |
| `TrackGeometryView` | True vs Estimated Path | `SimulationEngine` | `true_pos`, `est_pos` | `m` |
| `TimeSeriesAnalyticsWidget` | Error Time Series | `TelemetryHistory` | `error_history_urad` | `µrad` vs `s` |
| `CovarianceDiagnosticPanel` | EKF Covariance Matrix | `EKFEstimator` | `P_matrix` (2x2 / 4x4) | `rad²` |
| `StateEstimatePanel` | Position Estimate | `EKFEstimator` | `state_vector_x` | `rad` |
| `StateEstimatePanel` | Velocity Estimate | `EKFEstimator` | `state_vector_v` | `rad/s` |
| `HybridPerceptionBreakdownPanel` | Optical Detection | `YOLOv8Detector` | `bbox_center_xy` | `px` |
| `HybridPerceptionBreakdownPanel` | Centroid Offset | `CentroidTracker` | `centroid_offset_xy` | `px` |

---

### Screen 4: Stress Screen
| Visual Element / Widget | UI Metric Label | Backend Source Object | Backend Field Name | Units |
| :--- | :--- | :--- | :--- | :--- |
| `DisturbanceControlsWidget` | Optical Attenuation | `DisturbanceEngine` | `attenuation_factor` | `%` |
| `DisturbanceControlsWidget` | Angular Jitter | `DisturbanceEngine` | `jitter_amplitude_rad` | `µrad` |
| `DisturbanceControlsWidget` | Photon Shot Noise | `DisturbanceEngine` | `noise_sigma_px` | `px` |
| `HeroSensorView` | Real-time Sensor Disturbed Stream | `CameraSensor` | `get_disturbed_frame()` | BGR Image Array |
| `SystemResponsePanelWidget` | Reacquisition Latency | `PATStateMachine` | `reacq_duration_ms` | `ms` |
| `SystemResponsePanelWidget` | Tracking Error Spike | `TelemetryData` | `peak_error_urad` | `µrad` |

---

### Screen 5: Benchmark Screen
| Visual Element / Widget | UI Metric Label | Backend Source Object | Backend Field Name | Units |
| :--- | :--- | :--- | :--- | :--- |
| `BaselineComparisonTableWidget` | RMS Error (B0, B1, B2, Ours) | `Phase10BenchmarkResult` | `mean_rms_error_urad` | `µrad` |
| `BaselineComparisonTableWidget` | Lock Retain Time | `Phase10BenchmarkResult` | `lock_percentage` | `%` |
| `SameSeedInspectorWidget` | Seed Comparison Error | `Phase10BenchmarkResult` | `seed_run_error` | `µrad` |
| `DistributionVisualsWidget` | Error Distribution CDF | `Phase10BenchmarkResult` | `error_quantiles` | `µrad` |
| `RobustnessHeatmapWidget` | Grid Cell SNR vs RMS | `Phase10BenchmarkResult` | `grid_performance_matrix` | `µrad` |
| `FailureIntelligenceWidget` | Failure Mode Count | `Phase10BenchmarkResult` | `failure_classification_counts` | Count |
| `AblationComparisonWidget` | Full vs No-AEKF vs No-YOLO | `Phase10BenchmarkResult` | `ablation_rms_error` | `µrad` |
