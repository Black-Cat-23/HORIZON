# COARSE-ALIGN-X — Master Project Contract

## Purpose
Build the SIH26169 solution as a software-in-the-loop experimental platform for developing, stress-testing and statistically benchmarking coarse Pointing/Acquisition/Tracking (PAT) algorithms for mobile Free-Space Optical Communication (FSOC) terminals.

This is NOT a generic "AI camera tracker" and NOT a physical FSOC hardware build.

## Source of truth
1. Official SIH26169 problem statement.
2. `COARSE-ALIGN-X_SIH26169_Documentation(1).pdf` supplied by the team.
3. `COARSE-ALIGN-X_UIUX_Experience_Documentation.pdf` supplied by the team.
4. Verified external research referenced by those documents.

Never invent a PS requirement, numerical target, scientific constant, benchmark number, or claim of novelty.

## Required product behavior
The application must support:
- configurable virtual environment
- moving target/beacon(s)
- movable virtual camera
- automatic detection and identification of the designated beacon
- continuous tracking and camera-control commands
- disturbance injection: atmospheric/turbulence-inspired effects, platform vibration, camera motion/jitter, sensor noise; plus the team's documented robustness extensions
- real-time performance statistics
- standalone executable
- source code
- technical report
- user manual
- automatically generated performance report

## Product identity
Name: COARSE-ALIGN-X
Descriptor: Adaptive PAT Validation Platform

Core thesis:
A validation laboratory, not merely a tracker. The system must make measurements reproducible, compare algorithms under identical randomized conditions, expose failure cases, and show evidence rather than marketing claims.

## Core architecture
Scenario Engine -> Virtual Camera -> Beacon Perception -> Target Association -> State Estimation -> Confidence-aware Mode Manager -> Control Engine -> Virtual Camera feedback loop.

Parallel services:
- Disturbance Lab
- Experiment Engine
- Benchmark Lab

## Algorithm families
Baseline B0:
- simple acquisition/search
- classical beacon detection
- proportional/basic control

Baseline B1:
- spiral/raster acquisition
- classical detector
- Kalman filter
- PID

Baseline B2:
- neural detector
- Kalman filter
- PID

Candidate Ours:
- adaptive acquisition using a belief/search map
- hybrid classical + learned perception
- uncertainty-aware state estimation, potentially IMM-EKF after validation
- confidence-aware mode switching
- adaptive control
- explicit target-loss and reacquisition strategy

These are candidate engineering choices, not pre-proven facts. Every claimed benefit must be measured.

## Measurement philosophy
Do not optimize a single scripted demo.
Use reproducible seeded randomized trials.
At minimum track the PS-required metrics and the team's extended robustness metrics.
Never publish illustrative values as measured results.

## Engineering truth rules
- Camera geometry must be mathematically explicit.
- Angular error must come from the camera model, not only pixel distance.
- Filter matrices/covariances/gains must be validated.
- Actuator limits and latency must be explicit parameters.
- Disturbance models must be documented as simplified simulation models unless experimentally validated.
- Baselines must run on the same scenarios as the proposed method.
- Every benchmark result must be traceable to a run ID and random seed.

## Implementation order
1. Freeze mathematical specification.
2. Build Python research reference implementation and tests.
3. Build simplest Unity vertical slice.
4. Implement B0/B1 baselines.
5. Add neural detector and B2.
6. Validate candidate differentiators one by one.
7. Add disturbance/recovery system.
8. Build Monte Carlo benchmark runner.
9. Build Unity UX around proven functionality.
10. Connect website to real exported benchmark data.
11. Stress test and reproduce results.
12. Package standalone executable and documentation.

## Never do first
- do not start with visual polish
- do not start with an AI model before defining ground truth
- do not invent metrics
- do not build a cross-process per-frame Python runtime loop
- do not add technology merely because it sounds advanced
- do not copy GPL code into the product

## Current architectural constraint
Runtime closed-loop simulation must remain self-contained inside Unity/C# for timing integrity. Python is the research/training/offline-analysis environment. The supplied team plan uses this separation explicitly.
