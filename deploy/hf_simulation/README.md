---
title: HORIZON FSOC Tracking Simulation Console
emoji: 🛰️
colorFrom: blue
colorTo: cyan
sdk: docker
app_port: 7860
pinned: false
---

# PROJECT HORIZON: Autonomous Coarse Tracking Simulation Suite
### Smart India Hackathon 2026 — Problem Statement SIH26169

This Hugging Face Space runs the complete **HORIZON Python PySide6 (Qt 6) 5-Screen Simulation Suite** in a headless Linux virtual desktop container (Xvfb + x11vnc + noVNC).

* **Architecture**: Fourier-GMM Sub-Pixel Centroiding + 6-DoF Decoupled IMM-AEKF + Active Disturbance Rejection Control (ADRC).
* **Modes**:
  1. Mission Setup
  2. Live Flight Simulation
  3. Tracking Console (State Vector & Covariance)
  4. Stress Lab (Interactive Disturbance Injection)
  5. Benchmark Lab (Monte Carlo Validation)
