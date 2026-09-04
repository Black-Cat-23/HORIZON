# HORIZON — Agent Instructions

Team Xcalibur · SIH 2026 · PS26169. Read this before any task. Full detail lives in `/docs/` —
this file is deliberately short; consult the referenced doc when a task touches its area.

## Non-negotiable: math ownership
Filter tuning (Kalman/EKF/IMM), camera projection math, and disturbance models must never be
generated and trusted silently. Flag invented numerical constants (noise covariance, damping
coefficients) explicitly as placeholders needing human validation. Never claim a
filter/controller "works" without the user having independently verified it against ground truth.
This project's entire competitive edge depends on this math being correct, not just plausible.

## Fixed stack — do not substitute without asking
Unity 6 LTS, URP (not HDRP), Unity Sentis for ONNX inference at runtime (training happens in
Python, Unity only loads a trained .onnx), hand-written C# for filters/control (no external
package — deliberate, see math ownership above), UGUI, `-batchmode -nographics` for headless
Monte Carlo batch runs.

## Design system — see `/docs/design-system.md` for full token list
Colors are STATE, not palette: `--disturbance-amber` and `--lost-red` and `--confirm-green`
appear ONLY when that literal state is active, never decoratively. All numeric/telemetry values
render in monospace (JetBrains Mono / Space Mono), no exceptions. No bounce/spring easing
anywhere. Banned fonts: Inter, Roboto, Open Sans, Arial, any default system font.

## Module ownership — do not blur these boundaries
Scenario Engine / Virtual Camera / Beacon Perception / State Estimation / Mode Manager / Control
Engine / Disturbance Lab / Experiment Engine / Benchmark Lab — each owns exactly what its name
says. Full breakdown: `/docs/BUILD_PLAN.md`.

## UI and 3D world specs — do not improvise layout or scene content
Screen-by-screen UI: `/docs/UNITY_APP_UI_SPEC.md`. The 3D scene itself (environment, beacon,
camera rig, disturbance visuals, lighting): `/docs/3D_WORLD_DESIGN.md`. Every element in that
scene has a stated reason to exist — if a task requires adding something not covered there, ask
before improvising, don't default to a generic game-dev convention.

## Verification discipline
Before importing any package or dependency, verify it actually exists and is compatible with
Unity 6 LTS / the current stack — do not assume based on training data. Say so and ask if unsure.

## Website (separate track, same repo)
React Three Fiber + Motion (`motion/react`, not the old `framer-motion` package name) + Lenis +
GSAP/ScrollTrigger. Single persistent WebGL canvas behind the DOM, camera on a scroll-driven
rail (`CatmullRomCurve3`), never per-section disconnected animations. Must degrade to a fully
static, non-animated version under `prefers-reduced-motion` with identical content — this is a
hard requirement, not optional polish. Never autoplay audio.

## General behavior
Be concise. Do not explain standard patterns unless asked. If a generated solution is effectively
identical to existing code, say so rather than re-explaining it. Never commit without review.
