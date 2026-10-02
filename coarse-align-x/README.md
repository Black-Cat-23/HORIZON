<div align="center">

# 🛰️ HORIZON (coarse-align-x)
### AI-Based Virtual Camera Tracking System for Coarse Alignment of Mobile FSOC Terminals

**Smart India Hackathon 2026 — Problem Statement ID: SIH26169**  
*Autonomous Guidance, Navigation & Optical Tracking Directorate (ISRO)*

[![Windows Executable](https://img.shields.io/badge/Windows%20Executable-v1.0.0%20Standalone-0078D6?style=for-the-badge&logo=windows&logoColor=white)](https://github.com/bhanu-1108/HORIZON/releases/tag/v1.0.0)
[![ISRO Benchmark Verified](https://img.shields.io/badge/ISRO%20Benchmark-0.69px%20RMSE%20%7C%204.35ms-success?style=for-the-badge)](https://github.com/bhanu-1108/HORIZON/releases/tag/v1.0.0)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%20%7C%203.11%20%7C%203.12-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg?style=for-the-badge)](../LICENSE)

[**Download Executable (.exe)**](https://github.com/bhanu-1108/HORIZON/releases/download/v1.0.0/HORIZON_ISRO_Desktop_Suite_v1.0.zip) • [**System Architecture**](#-system-architecture--algorithmic-foundations) • [**ISRO Benchmark Results**](#-isro-sih26169-compliance--benchmark-verification) • [**Operator Manual**](#-operator-manual--workstation-guide) • [**Developer Guide**](#-developer-guide--running-from-source)

</div>

---

## 📋 Executive Summary & Mission Context

Free-Space Optical Communications (FSOC) represent the next frontier in inter-satellite, UAV-to-ground, and deep-space telemetry, offering data throughput orders of magnitude higher than conventional RF bands. However, optical communication beams exhibit extremely narrow divergence angles ($\mu\text{rad}$ scale).

Before sub-microradian **Fine Pointing Stages (FPS)** (such as Fast Steering Mirrors - FSM) can achieve optical lock, an autonomous **Coarse Alignment System** must:
1. Rapidly acquire an optical beacon within an uncertain wide Field-of-View (FOV) ($2000 \times 2000$ pixels).
2. Track high-velocity, maneuverable trajectories with sub-pixel precision.
3. Reject optical atmospheric turbulence, scintillation, solar blinding, micro-vibrations, and temporary line-of-sight occlusions.

**HORIZON** is an aerospace-grade, deterministic digital-twin simulation and tracking suite developed specifically for ISRO's SIH26169 problem statement. It couples a **Hybrid Perception Pipeline** with an **Interacting Multiple Model Extended Kalman Filter (IMM-EKF)** and a **Nonlinear Active Disturbance Rejection Controller (ADRC)** to deliver sub-pixel tracking and sub-$5\text{ ms}$ compute latency.

---

## 🏆 ISRO SIH26169 Compliance & Benchmark Verification

The tracking performance was verified across extended operational profiles and stressed against ISRO requirements:

| Performance Metric | Official ISRO Specification | HORIZON Benchmark Measured | Operational Margin | Result |
| :--- | :---: | :---: | :---: | :---: |
| **Tracking Accuracy (RMSE)** | $\le 2.50\text{ px}$ | **$0.69\text{ px}$** | **$3.6\times$ tighter** | <kbd>PASS</kbd> |
| **95th Percentile Error ($P_{95}$)** | $\le 5.00\text{ px}$ | **$0.97\text{ px}$** | **$5.1\times$ tighter** | <kbd>PASS</kbd> |
| **Peak 99th Error ($P_{99}$)** | $\le 8.00\text{ px}$ | **$1.02\text{ px}$** | **$7.8\times$ tighter** | <kbd>PASS</kbd> |
| **Processing Latency ($P_{95}$)** | $\le 20.00\text{ ms}$ | **$4.35\text{ ms}$** | **$4.6\times$ faster** | <kbd>PASS</kbd> |
| **Acquisition Success Rate** | $\ge 95.0\%$ | **$100.0\%$** | **$100\%$ acquisition** | <kbd>PASS</kbd> |
| **Continuous Lock Retention** | $\ge 98.0\%$ | **$100.0\%$** | **Zero lock drops** | <kbd>PASS</kbd> |
| **False Positive Alarm Rate** | $\le 2.0\%$ | **$0.0\%$** | **Zero false detections**| <kbd>PASS</kbd> |
| **Re-acquisition Speed** | $\le 150\text{ ms}$ | **$< 16.7\text{ ms}$ (1 frame)**| **Instantaneous** | <kbd>PASS</kbd> |

*All data verified via `results/comparisons/comparison.json` and exportable as high-precision ISRO PDF Engineering Reports.*

---

## 📦 How to Download & Run the Standalone Executable (.exe)

**No Python, PyTorch, C++ compilers, or GPU drivers are required.** The standalone package bundles the entire PySide6 GUI runtime, computational backends, optical dataset samples, and neural weights.

### Step 1: Download the Release Bundle
Download the standalone ZIP package from either official repository:
- **Direct Download Link**: [**HORIZON_ISRO_Desktop_Suite_v1.0.zip (1.06 GB)**](https://github.com/bhanu-1108/HORIZON/releases/download/v1.0.0/HORIZON_ISRO_Desktop_Suite_v1.0.zip)
- **GitHub Release Page**: [https://github.com/bhanu-1108/HORIZON/releases/tag/v1.0.0](https://github.com/bhanu-1108/HORIZON/releases/tag/v1.0.0)
- *(Upstream Release)*: [https://github.com/Black-Cat-23/HORIZON/releases](https://github.com/Black-Cat-23/HORIZON/releases)

### Step 2: Extract the Package
Right-click `HORIZON_ISRO_Desktop_Suite_v1.0.zip` and select **Extract All...** to any folder on your computer.

### Step 3: Launch with One Click
Inside the extracted `HORIZON` folder:
- **Double-click `Launch_HORIZON.bat`** (or `HORIZON.exe`).
- The application will initialize in high-DPI desktop mode and launch the mission control workstation immediately.

---

## 🧠 System Architecture & Algorithmic Foundations

```
                           +------------------------------------------+
                           |  Optical Sensor Stream (2000x2000 uint8) |
                           +--------------------+---------------------+
                                                |
                     +--------------------------v---------------------------+
                     |             HYBRID PERCEPTION SUBSYSTEM              |
                     |  - Adaptive Thresholding & Morphology               |
                     |  - Sub-Pixel Weighted Center-of-Gravity (CoG)        |
                     |  - Dual-Channel Deep Beacon Verification CNN         |
                     +--------------------------+---------------------------+
                                                |  Measurement z_k = [x, y]^T
                     +--------------------------v---------------------------+
                     |          IMM-ADAPTIVE STATE ESTIMATOR                |
                     |  Mode 1: Constant Velocity (CV) Kinematic Model     |
                     |  Mode 2: Singer Stochastic Acceleration Jump Model  |
                     |  - Markov Probability Hypothesis Fusion              |
                     +--------------------------+---------------------------+
                                                |  Estimated State x_hat_k
                     +--------------------------v---------------------------+
                     |    ACTIVE DISTURBANCE REJECTION CONTROLLER (ADRC)    |
                     |  - Extended State Observer (ESO)                     |
                     |  - Real-time Total Disturbance Estimation (f_total)  |
                     |  - Nonlinear Feedback Virtual Gimbal Actuation       |
                     +--------------------------+---------------------------+
                                                |  Control Command u_k
                           +--------------------v---------------------+
                           | Virtual Gimbal & Mirror Steering Plant   |
                           +------------------------------------------+
```

### 1. Hybrid Perception Engine
- **Sub-Pixel Area Overlap Rasterization**: Converts continuous optical beacon state coordinates into realistic Poisson/Gaussian PSF profiles.
- **Weighted Center-of-Gravity (CoG)**: Computes intensity-weighted centroid:
  $$\bar{x} = \frac{\sum_{i,j} I(i, j) \cdot x_{i,j}}{\sum_{i,j} I(i, j)}, \quad \bar{y} = \frac{\sum_{i,j} I(i, j) \cdot y_{i,j}}{\sum_{i,j} I(i, j)}$$
- **False-Target Discriminator**: Filters space debris, stray reflections, and cosmic-ray artifacts via aspect-ratio and radiometric flux bounds.

### 2. Interacting Multiple Model Extended Kalman Filter (IMM-EKF)
Space terminals switch between steady tracking and sudden evasive or atmospheric maneuvers. HORIZON executes parallel Kalman filters weighted dynamically by likelihood:
- **Model $M_1$ (Calm Drift)**: Constant Velocity (CV) with white noise acceleration.
- **Model $M_2$ (High-G Maneuver)**: Singer acceleration model capturing correlated wind shear and platform vibrations.
- **Transition Probability Matrix $\Pi$**:
  $$\Pi = \begin{bmatrix} 0.95 & 0.05 \\ 0.10 & 0.90 \end{bmatrix}$$
  Ensures zero-overshoot recovery during rapid trajectory direction reversals.

### 3. Active Disturbance Rejection Control (ADRC)
Rather than relying on exact physical inertia models of the terminal gimbal, HORIZON employs an **Extended State Observer (ESO)** to treat unmodeled kinematics, aerodynamic buffet, and mirror friction as an augmented state:
$$\dot{x}_1 = x_2, \quad \dot{x}_2 = x_3 + b_0 u, \quad \dot{x}_3 = \dot{f}_{\text{total}}$$
The controller compensates for disturbances in real-time before pointing errors propagate to the optical line-of-sight.

---

## 🖥️ Operator Manual & Workstation Guide

The GUI is structured into 5 dedicated aerospace engineering workstations:

### 1. Mission Setup Workstation
- **Trajectory Generators**:
  - `Straight Line`: Dynamic boundary bounce or clamp with continuous velocity vectors.
  - `Circular`: Variable radius and angular orbital velocity.
  - `Figure-8`: Lemniscate of Gerono with dual-axis inflection points.
  - `Continuous Random`: Multi-order Gauss-Markov random walk simulating satellite attitude drift.
- **Beacon Customizer**: Select shapes (Square/Box, Gaussian Point, Circle), dimensions ($5\text{--}20\text{ px}$), and emission power.
- **Disturbance Suite**: Atmospheric turbulence index ($C_n^2$), random walk micro-vibrations, cloud occlusion intervals, and sensor dark noise.

### 2. Live Simulation & Tracking Viewport
- **Resolution**: $2000 \times 2000$ virtual focal plane array rendered at 60 FPS.
- **Interactive HUD Overlays**:
  - 🟢 **Green Crosshair**: Estimated beacon state from IMM-EKF.
  - 🟡 **Yellow Bounding Box**: Region-of-Interest (ROI) tracker window.
  - 🔴 **Red Target**: True physical position of optical beacon.
  - **State Pill**: Real-time finite-state indicator (`ACQUISITION` $\rightarrow$ `LOCKED_TRACKING` $\rightarrow$ `RE_ACQUISITION`).

### 3. Tracking Diagnostics Console
- Real-time Matplotlib & PyQtGraph diagnostic monitors:
  - Error magnitude history ($\Delta x, \Delta y, \|\mathbf{e}\|$).
  - Power Spectral Density (PSD) analysis of tracking errors.
  - IMM Model Hypothesis Probabilities (Model 1 vs Model 2 likelihoods).
  - Virtual Gimbal control efforts ($u_x, u_y$).

### 4. Stress & Adversarial Lab
- Test edge cases interactively while tracking is live:
  - **Flash Flare**: Simulate direct solar intrusion into camera aperture.
  - **Total Occlusion**: Inject dense cloud banks and evaluate re-acquisition times.
  - **Dynamic Wind Gusts**: Sudden step disturbance inputs to test ADRC rejection.

### 5. ISRO Benchmark Lab
- Automated Monte Carlo trials ($N=10$ to $N=500$ runs).
- Comparative analysis against baseline models:
  - **HORIZON Champion** (IMM-Adaptive EKF + ESO ADRC)
  - **Baseline 1** (Classical Single-Model Kalman Filter)
  - **Baseline 2** (Classical PID Controller)
- **One-Click ISRO PDF Report Exporter**: Compiles tables, distributions, and LaTeX-rendered metric compliance into a formal submission PDF.

---

## 💻 Developer Guide — Running from Source

For developers or evaluators wanting to inspect and modify the raw Python source:

### Prerequisites
- Python 3.10, 3.11, or 3.12 (64-bit recommended)
- Git

### 1. Clone the Repository
```bash
git clone https://github.com/bhanu-1108/HORIZON.git
cd HORIZON/coarse-align-x
```

### 2. Set Up Virtual Environment
```powershell
# Create virtual environment
python -m venv venv

# Activate on Windows
.\venv\Scripts\Activate.ps1

# Activate on Linux/macOS
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Launch Desktop Application
```bash
python main.py --gui
```

### 5. Headless Mode (Automated Batch Verification)
Run batch simulations without GUI for CI/CD or benchmark pipelines:
```bash
python main.py --duration 30.0 --trajectory figure8 --preset NOMINAL
```
