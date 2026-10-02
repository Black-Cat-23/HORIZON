# HORIZON: AI-Based Virtual Camera Tracking System for Coarse Alignment of Mobile FSOC Terminals

**Smart India Hackathon 2026 — Problem Statement SIH26169 (ISRO)**

[![Windows Executable](https://img.shields.io/badge/Windows%20Executable-v1.0.0%20Standalone-0078D6?style=for-the-badge&logo=windows&logoColor=white)](https://github.com/bhanu-1108/HORIZON/releases/tag/v1.0.0)
[![ISRO Benchmark Verified](https://img.shields.io/badge/ISRO%20Benchmark-0.69px%20RMSE%20%7C%204.35ms-success?style=for-the-badge)](https://github.com/bhanu-1108/HORIZON/releases/tag/v1.0.0)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg?style=for-the-badge)](LICENSE)

---

## 🚀 Quick Start for Evaluators & Judges

### Option 1: Standalone Windows Executable (Zero Setup)
No Python, PyTorch, or CUDA installation is required.

1. **Download the Release Bundle**:  
   👉 [**Download HORIZON_ISRO_Desktop_Suite_v1.0.zip (1.06 GB)**](https://github.com/bhanu-1108/HORIZON/releases/download/v1.0.0/HORIZON_ISRO_Desktop_Suite_v1.0.zip)  
   *(Also available under the [GitHub Releases Page](https://github.com/bhanu-1108/HORIZON/releases/tag/v1.0.0))*
2. **Extract the ZIP archive**.
3. **Double-click** `Launch_HORIZON.bat` or `HORIZON.exe`.

---

### Option 2: One-Click Local Launcher (If Cloned)
If you have cloned this repository locally:
- Simply double-click **`RUN_HORIZON_EXE.bat`** in the repository root.
  *(It automatically detects the compiled standalone executable or routes to the local Python environment).*

---

### Option 3: Run from Python Source
```bash
# Navigate to the core simulation suite
cd coarse-align-x

# Install dependencies
pip install -r requirements.txt

# Launch the unified desktop GUI
python main.py --gui
```

---

## 🏆 Verified ISRO Benchmark Performance

The system was evaluated under strict ISRO SIH26169 benchmark criteria:

| Metric | Target Specification | Measured Performance | Margin / Status |
| :--- | :--- | :--- | :--- |
| **Tracking Accuracy (RMSE)** | $\le 2.50\text{ px}$ | **$0.69\text{ px}$** | **$3.6\times$ better than spec (PASS)** |
| **95th Percentile Error ($P_{95}$)** | $\le 5.00\text{ px}$ | **$0.97\text{ px}$** | **$5.1\times$ better than spec (PASS)** |
| **Processing Latency ($P_{95}$)** | $\le 20.00\text{ ms}$ | **$4.35\text{ ms}$** | **$4.6\times$ faster than spec (PASS)** |
| **Acquisition Success Rate** | $\ge 95\%$ | **$100.0\%$** | **Flawless acquisition (PASS)** |
| **Lock Retention Rate** | $\ge 98\%$ | **$100.0\%$** | **Zero lock drops (PASS)** |
| **False Positive Detections** | $\le 2.0\%$ | **$0.0\%$** | **Zero false alarms (PASS)** |

---

## 🛰️ Architecture & Workstations

The desktop application provides 5 integrated engineering workstations:

1. **Mission Setup**: Trajectory kinematics (Straight, Circular, Figure-8, Stochastic Gauss-Markov), optical parameters, physical disturbances (atmospheric turbulence, micro-vibrations, cloud occlusions).
2. **Real-Time Live Simulation**: Unified viewport displaying high-speed camera frames, dynamic bounding box, predicted beacon center, and state transitions (Acquisition $\rightarrow$ Tracking $\rightarrow$ Re-acquisition).
3. **Tracking & Controls**: IMM-Adaptive Extended Kalman Filter (IMM-EKF) state estimation combined with Active Disturbance Rejection Control (Nonlinear ADRC).
4. **Stress & Adversarial Lab**: On-the-fly injection of optical blobbing, sensor saturation, and angular wind gusts.
5. **ISRO Benchmark Workstation**: Comprehensive Monte Carlo validation and baseline comparisons against Classical Kalman, Vanilla ADRC, and ISRO pass/fail thresholding.

---

## 👥 Repository Remotes

- **Primary Submission**: [https://github.com/bhanu-1108/HORIZON](https://github.com/bhanu-1108/HORIZON)
- **Upstream Development**: [https://github.com/Black-Cat-23/HORIZON](https://github.com/Black-Cat-23/HORIZON)
