# HORIZON — Source & Evidence Register

## Purpose
This document is the provenance guardrail for all HORIZON development. Agents must distinguish:
1. official SIH requirements;
2. published/open-source technical references;
3. our engineering choices;
4. provisional simulation assumptions.

No agent may present category 3 or 4 as an official SIH requirement or experimentally validated physical fact.

## A. Official SIH26169 source of truth

Use the official SIH PS as the authoritative source for what SIH26169 actually requires:
- Title: Development of an AI-Based Virtual Camera Tracking System for Coarse Alignment of Mobile Free Space Optical Communication (FSOC) Terminals.
- Software solution, not a hardware-build requirement.
- Configurable virtual environment.
- Moving target/beacon(s).
- Movable virtual camera.
- Automatic detection/identification of designated beacon.
- Continuous tracking and camera repositioning.
- Disturbance simulation including atmospheric turbulence, platform vibration, camera motion and sensor noise.
- Real-time performance statistics including simulation duration, FPS, acquisition time, average/max tracking error, lock-retention rate and processing time.
- Standalone executable, source, technical report, user manual and generated performance report.

Official source:
https://www.sih.gov.in/sih2026PS

Do not invent official numerical acceptance thresholds where the current accessible PS does not publish them.

## B. Open-source / published references relevant to implementation

### B1. UT-ISSL FSO PAT Simulator
https://github.com/ut-issl/free-space-optical-communication-pat-simulator

Use as a reference for modular PAT simulation concepts, including optics, actuators, sensors, disturbance and control modelling. The repository is MIT-licensed according to its repository metadata.

Important: the repository documents a known stability issue in its default scenario. Do not blindly copy parameters or claim its default configuration is physically validated.

### B2. IRNAS KORUZA v2 tracking
https://github.com/IRNAS/koruza-v2-tracking

Use primarily as a reference for optical-link alignment architecture and spiral acquisition. The repository includes a Spiral Scan Align implementation. Its software is GPLv3: do not paste GPL code into proprietary/project code without reviewing licensing implications. Prefer independent reimplementation of algorithms from the literature.

### B3. IIT laser-spot tracker
https://github.com/ADVRHumanoids/nn_laser_spot_tracking

Use as a reference/baseline source for classical and neural laser-spot detection. Repository license is BSD-3-Clause according to the repository metadata.

### B4. Laser-spot dataset
https://zenodo.org/records/15230870

Use as a perception-development reference/dataset subject to the dataset's own terms. Do not describe it as an FSOC space-beacon dataset. It is a laser-spot dataset from a different application domain and therefore requires domain adaptation / synthetic augmentation.

### B5. Published FSO tracking literature
A 2025 Scientific Reports paper reports a computer-vision FSO tracking architecture combining a lightweight CNN, Kalman filtering and closed-loop control. Use as an architectural prior, not as a source of guaranteed performance for HORIZON.

https://www.nature.com/articles/s41598-025-17695-7

### B6. Published FSO acquisition literature
Published work discusses raster/spiral and other acquisition strategies and acquisition-time trade-offs. Use these papers to justify baselines and experiment design; do not copy their numerical results into HORIZON.

### B7. Visual servoing reference
https://github.com/lagadic/visp

Use as a conceptual reference for visual tracking/servoing. Do not introduce this package into HORIZON unless its role and Unity compatibility are explicitly justified and verified.

## C. HORIZON engineering choices (NOT official SIH requirements)

The following are our proposed implementation choices unless subsequently changed by evidence:
- Unity 6 LTS + URP for the runtime simulator.
- C# for runtime control/estimation/simulation.
- Python for research/training/offline analysis.
- ONNX runtime inside Unity for neural inference if/when validated.
- Baselines: simple baseline, classical spiral/raster + detector + KF + PID, neural detector + KF + PID.
- Candidate differentiator: adaptive acquisition + confidence-aware perception + multi-model estimation + adaptive control + reacquisition.
- Seeded Monte Carlo evaluation.

These are strategic design decisions, not claims that SIH mandates these exact technologies.

## D. Rules for evidence

Every nontrivial technical constant must be tagged in code/documentation as one of:
- SOURCE_BACKED
- DERIVED
- PROVISIONAL
- MEASURED_HORIZON

No agent may silently turn PROVISIONAL into SOURCE_BACKED.

Every benchmark result shown in a UI/report must be generated from stored experiment output. No hard-coded showcase metrics.
