# HORIZON

**Homing & Optical Intelligence for Robust Zone-Oriented Navigation**

Visual language: **HORIZON**. Tokens and motion live in `/docs/`.

## Run the operator UI

Open `app/index.html` in a local static server (ES modules). From this folder:

```bash
npx --yes serve app -p 5173
```

Then open `http://localhost:5173`.

## Screens

| Rail | Screen | Role |
|------|--------|------|
| 1 | Mission Setup | Scenario config + same-world 3D preview |
| 2 | Live Simulation | Full-viewport feed, mode graph, telemetry, event log |
| 3 | Tracking Console | State vector, covariance ellipse, predicted vs actual |
| 4 | Stress Lab | Live disturbance injection |
| 5 | Benchmark Lab | Monte Carlo comparison, envelope, failure replay |

All screens subscribe to one `HorizonStore`. Mission Setup preview, Live Simulation, and Stress Lab render the same world. Benchmark Lab shows an explicit empty state until a run completes — no placeholder metrics.

Unity C# mirrors (`unity/Assets/Horizon/`) bind the same token names and telemetry shape so UGUI can attach without a second data story.

