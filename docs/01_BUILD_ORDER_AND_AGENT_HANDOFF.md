# HORIZON — Build Order & Agent Handoff

## Goal
Two coding agents are allowed, but there must be ONE source-controlled repository and ONE architecture.

### Recommended ownership
CURSOR:
- Unity project
- Unity C# runtime
- scene construction
- virtual camera
- target simulation
- runtime perception inference integration
- state estimation implementation in C#
- mode manager
- control engine
- disturbance engine
- benchmark runtime
- Unity UI
- standalone build

ANTIGRAVITY:
- Python research environment
- dataset preparation
- synthetic data generation utilities outside runtime
- model training/export
- benchmark analysis and statistics
- research notebooks/scripts
- technical documentation
- public-facing web experience, if implemented in same repo
- integration review and documentation consistency

Important: do NOT let the two agents independently redefine interfaces or architecture.

## Repository contract
Suggested root:
/horizon
  /UnityApp
  /Research
  /Benchmarks
  /Website
  /Reports
  /docs

Shared contracts are stored under:
/docs/contracts/

Every cross-module interface must be documented there before implementation.

## Phase gates
### Gate 0 — Specification
No production UI. No AI model training. Freeze coordinate systems, camera model, state definition, actuator model, disturbance taxonomy and metric definitions.

### Gate 1 — Research reference
Python proves the equations and simple controller behavior against known synthetic trajectories.

### Gate 2 — Vertical slice
Unity proves target -> camera -> detection -> angular error -> control -> recentering.

### Gate 3 — Baselines
B0/B1 work and log metrics.

### Gate 4 — Neural perception
B2 works and is benchmarked against B1.

### Gate 5 — Differentiator
Only add one candidate improvement at a time; run ablation against the previous best baseline.

### Gate 6 — Robustness
Disturbances + loss + reacquisition.

### Gate 7 — Benchmark Lab
Seeded trials, confidence intervals/percentiles, failure replay.

### Gate 8 — UX
Mission Setup, Live Simulation, Tracking Console, Stress Lab, Benchmark Lab.

### Gate 9 — Presentation website
The web experience consumes exported benchmark JSON from the actual product.

### Gate 10 — Release
Standalone executable + technical report + user manual + performance report.

## Agent discipline
Every coding session must begin by reading:
- this file
- `00_MASTER_PROJECT_CONTRACT.md`
- the relevant domain spec

Before changing architecture:
1. state what requirement is being addressed
2. state what existing interface is affected
3. make the smallest viable change
4. run relevant tests
5. report exact files changed and test results

Do not rewrite working modules merely to match personal style.
