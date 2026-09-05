# HORIZON: AI-Based Virtual Camera Tracking System for Coarse Alignment of Mobile FSOC Terminals

**Smart India Hackathon 2026 — Problem Statement SIH26169**  
*Phase 1: Simulation Foundation*

---

## 1. Project Purpose
Free Space Optical Communication (FSOC) requires ultra-precise beam pointing between moving terminals (e.g., UAV-to-ground, satellite-to-optical ground station). Before fine pointing (< milliradian) can lock, a **Coarse Alignment** phase must acquire and track an optical beacon within an uncertainty field of view.

**HORIZON** is an autonomous engineering simulation platform built to design, validate, and benchmark AI/vision-based virtual camera coarse tracking algorithms for mobile FSOC terminals under physical dynamics and optical disturbances.

---

## 2. SIH26169 Relationship & Compliance
This codebase is developed to meet the official requirements of SIH Problem Statement **SIH26169**:
- **Environment**: Configurable monochrome virtual world (2000×2000 pixels).
- **Target**: Single optical beacon (5–20 px, default 10×10 px) with continuous subpixel coordinates.
- **Kinematics**: Real-time position, velocity, and acceleration state models.
- **Mandatory Trajectories**: Straight Line (with bounce/clamp), Circular, Figure-of-8, and Continuous Random Motion.
- **Determinism**: Fully decoupled simulation clock with reproducible random seeds.

---

## 3. Phase 1 Scope
Phase 1 establishes the mathematical and software **Simulation Foundation**:
- Deterministic fixed-timestep clock ($dt = 1/60$ s) decoupled from rendering or wall-clock timing.
- SeedManager using modern NumPy `SeedSequence` for reproducible child RNG streams.
- Analytical and continuous stochastic trajectory kinematics.
- Subpixel area-overlap rasterization of optical beacon into real 2000×2000 `uint8` monochrome frames.
- Per-frame ground-truth telemetry logging (CSV and JSON).
- Lightweight PySide6 development debug viewer.
- Full automated test suite (94 passing tests).

---

## 4. Architecture

```
horizon/
│
├── configs/
│   └── default.yaml          # Validated baseline YAML parameters
│
├── simulator/
│   ├── core/
│   │   ├── clock.py          # FixedTimestepClock (pure deterministic dt)
│   │   ├── config.py         # Strongly-typed dataclasses & validation
│   │   ├── recorder.py       # GroundTruthRecorder (CSV / JSON)
│   │   ├── seed_manager.py   # SeedManager with SeedSequence child streams
│   │   └── simulation.py     # SimulationEngine (pure mathematical orchestration)
│   │
│   ├── world/
│   │   ├── beacon.py         # Beacon model & subpixel box rasterization
│   │   ├── state.py          # TargetState ground truth dataclass
│   │   └── world.py          # WorldRenderer (2000×2000 monochrome uint8)
│   │
│   ├── trajectories/
│   │   ├── base.py           # Abstract Trajectory interface
│   │   ├── straight.py       # StraightLineTrajectory (analytical bounce/clamp)
│   │   ├── circular.py       # CircularTrajectory (analytical derivatives)
│   │   ├── figure8.py        # FigureEightTrajectory (Lissajous 1:2 ratio)
│   │   ├── random_motion.py  # RandomMotionTrajectory (Ornstein-Uhlenbeck)
│   │   ├── spiral.py         # SpiralTrajectory (optional interface)
│   │   └── sinusoidal.py     # SinusoidalTrajectory (optional interface)
│   │
│   └── visualization/
│       └── debug_view.py     # PySide6 development debug viewer
│
├── tests/                    # 94 comprehensive automated tests
│   ├── test_beacon.py
│   ├── test_circular.py
│   ├── test_clock.py
│   ├── test_config.py
│   ├── test_figure8.py
│   ├── test_random_motion.py
│   ├── test_reproducibility.py
│   ├── test_seed.py
│   ├── test_simulation.py
│   ├── test_straight.py
│   ├── test_target_state.py
│   └── test_world.py
│
├── data/ground_truth/        # Exported telemetry files
├── logs/                     # Diagnostics logs
├── main.py                   # Headless & GUI entry point
├── requirements.txt          # Pinned dependency specifications
└── README.md
```

### Strict Separation of Concerns:
- **Trajectory** $\rightarrow$ Kinematic target motion only.
- **Target/Beacon** $\rightarrow$ Optical representation and rasterization.
- **WorldRenderer** $\rightarrow$ Frame generation (no camera viewport extraction).
- **Clock** $\rightarrow$ Discrete simulation steps (independent of wall time).
- **SimulationEngine** $\rightarrow$ Headless state orchestrator.
- **GroundTruthRecorder** $\rightarrow$ Persistence (CSV/JSON).
- **DebugView** $\rightarrow$ Read-only observer.

---

## 5. Installation

```bash
# Navigate to the project directory
cd horizon

# Create and activate virtual environment (optional)
python -m venv venv
venv\Scripts\activate   # Windows

# Install dependencies
pip install -r requirements.txt
```

---

## 6. Dependencies
- `numpy >= 1.26`
- `opencv-python >= 4.9`
- `PySide6 >= 6.6`
- `PyYAML >= 6.0`
- `pytest >= 8.0`

---

## 7. Running the Simulator

### Headless Execution (CLI):
```bash
# Run default configuration (10 seconds, straight line, seed 42)
python main.py

# Run Figure-8 trajectory for 5 seconds and export CSV/JSON
python main.py --trajectory figure8 --duration 5.0 --export-csv data/ground_truth/fig8.csv --export-json data/ground_truth/fig8.json

# Run Circular trajectory with custom seed
python main.py --trajectory circular --seed 12345 --duration 10.0

# Run Random motion trajectory
python main.py --trajectory random --seed 999 --duration 15.0
```

---

## 8. Running the Debug Viewer

To launch the development inspection GUI:
```bash
python main.py --gui
```
Controls available in viewer:
- **Start / Pause / Reset**: Interactive playback control.
- **Trajectory Selection**: Switch between `straight`, `circular`, `figure8`, `random`, `spiral`, and `sinusoidal`.
- **Seed Input**: Modify seed dynamically and observe deterministic response.
- **Duration**: Configure simulation run length.
- **Export**: One-click dump to CSV and JSON.

---

## 9. Configuration (`configs/default.yaml`)
All simulation parameters are declared and strictly validated on load:
```yaml
world:
  width: 2000
  height: 2000
  background_level: 0

camera:
  width: 640
  height: 480
  fov_horizontal_deg: 4.0
  fov_vertical_deg: 3.0
  update_rate_hz: 30

target:
  count: 1
  size_px: 10
  intensity: 255
  initial_position:
    x: null # null = seed-derived
    y: null

simulation:
  frequency_hz: 60
  seed: 42
  duration_seconds: 10.0
```

---

## 10. Mathematical Trajectory Formulations

### 1. Straight Line (with Reflection)
$$x(t) = \text{reflect}_{1\text{D}}(x_0, v_x, t, [x_{\min}, x_{\max}])$$
$$y(t) = \text{reflect}_{1\text{D}}(y_0, v_y, t, [y_{\min}, y_{\max}])$$
Speed $|v|$ is strictly conserved upon specular reflection.

### 2. Circular Trajectory
$$\theta(t) = \omega t + \phi$$
$$x(t) = c_x + R \cos(\theta), \quad y(t) = c_y + R \sin(\theta)$$
$$\dot{x}(t) = -R\omega \sin(\theta), \quad \dot{y}(t) = R\omega \cos(\theta)$$
$$\ddot{x}(t) = -R\omega^2 \cos(\theta), \quad \ddot{y}(t) = -R\omega^2 \sin(\theta)$$

### 3. Figure-of-8 (Lissajous 1:2)
$$x(t) = c_x + A \sin(\omega t + \phi), \quad y(t) = c_y + B \sin(2\omega t + \phi)$$
$$\dot{x}(t) = A\omega \cos(\omega t + \phi), \quad \dot{y}(t) = 2B\omega \cos(2\omega t + \phi)$$
$$\ddot{x}(t) = -A\omega^2 \sin(\omega t + \phi), \quad \ddot{y}(t) = -4B\omega^2 \sin(2\omega t + \phi)$$

### 4. Random Motion (Bounded Ornstein-Uhlenbeck)
Acceleration evolves via continuous mean-reverting stochastic process:
$$a(t + \Delta t) = a(t)(1 - \theta \Delta t) + \sigma \sqrt{\Delta t} \eta, \quad \eta \sim \mathcal{N}(0, 1)$$
Clamped such that $\|a\| \leq a_{\max}$ and integrated velocity $\|v\| \leq v_{\max}$. Soft bounce boundary reflection guarantees continuous paths without teleportation.

---

## 11. Ground-Truth Telemetry Schema
Every simulation timestep produces an immutable record with:
- `experiment_id`: Unique run identifier
- `seed`: Random seed used
- `frame`: 0-indexed frame count
- `timestamp`: Simulation time in seconds
- `target_id`: Target index (1)
- `target_x, target_y`: Subpixel coordinates in world frame
- `target_vx, target_vy`: Instantaneous velocities (px/s)
- `target_ax, target_ay`: Instantaneous accelerations (px/s²)
- `target_visible`: Boolean optical flag
- `trajectory_type`: Name of active trajectory
- `world_width, world_height`: World dimensions (2000×2000)
- `target_size_px`: Target edge length

---

## 12. Running Automated Tests

Run the full pytest suite:
```bash
python -m pytest tests/ -v
```

All **94 tests** validate:
- Parameter validation and error handling
- Clock determinism and absence of floating-point drift
- Seed reproducibility and child stream isolation
- Analytical and numerical consistency of all derivatives
- Kinematic boundedness and anti-teleportation constraints
- Area conservation in subpixel rasterization
- 100% bit-exact frame and telemetry reproduction across repeated runs

---

## 13. What is Intentionally NOT Implemented in Phase 1
Per Phase 1 design boundaries, the following components are reserved for future phases:
- Virtual Camera Viewport extraction (Phase 2)
- Atmospheric disturbances, noise, and jitter models (Phase 3)
- Beacon computer vision and AI detectors (Phase 4)
- Kalman Filter / EKF state estimators (Phase 5)
- Pointing, Acquisition, and Tracking (PAT) state machine (Phase 6)
- Closed-loop camera gimbal controller (Phase 7)
- Automated benchmarking and Monte Carlo experiment framework (Phase 8)
- Standalone production UI (Phase 9)

---

## 14. Phase 1 Status
**PHASE 1 READY FOR HUMAN REVIEW**
