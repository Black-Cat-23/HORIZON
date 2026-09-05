# HORIZON — Unity Application UI Spec (5 screens)

Applies the design system in `.cursor/rules/design-system.mdc` to the actual in-app UGUI screens.
This did not exist before — the website doc (THE LOCK-ON) only referenced "extend this language
to the app" without specifying how. This file closes that gap.

Navigation: a persistent left-edge rail (5 icons, `--field` background) switches between the five
screens below. Active screen icon uses `--lock-cyan`; inactive icons are 40% opacity neutral gray.
No page-reload feel between screens — cross-fade only, ≤200ms, no slide/bounce.

---

## Screen 1 — Mission Setup

**Purpose:** configure a scenario before running it.

**Layout:** two-column. Left column (35% width, `--field` panel): grouped config sections —
Target (speed, acceleration, initial angular offset), Camera (FOV, resolution), Disturbance
(preset dropdown: NOMINAL / DIFFICULT / SEVERE / RECOVERY / ADVERSARIAL), Algorithm (checkboxes:
B0-Naive, B1-Classical, B2-Neural, Ours — multi-select, since Benchmark Lab needs multiple
selected for comparison). Right column (65%): a simplified static 3D preview of the initial
camera/target arrangement, rendered in the same world used elsewhere in the app (not a mockup).

**Typography:** section labels in Space Grotesk, all-caps, small, `--lock-cyan`. Every numeric
input field uses monospace for the value itself even while editable.

**Primary action:** `RUN` button, bottom-right of the right column, `--lock-cyan` fill, large.
Pressing it transitions (cross-fade, damped) to Screen 2.

---

## Screen 2 — Live Simulation

**Purpose:** the primary demo screen — full-viewport 3D camera feed, minimal chrome over it.

**Layout:** the 3D view fills the screen. Overlaid HUD elements, all on translucent `--field`
panels at ~85% opacity so the scene stays visible underneath:
- **Top-left:** the Mode Manager mini state-graph (SEARCH → ACQUIRE → TRACK → DEGRADED →
  REACQUIRE) — same visual introduced on the website in Act IV. The current active node is filled
  solid in its state color (TRACK = `--confirm-green`, DEGRADED = `--disturbance-amber`,
  REACQUIRE = `--lost-red`, SEARCH/ACQUIRE = `--lock-cyan`); inactive nodes are outline-only.
- **Top-right:** live metrics readout, monospace, updating every frame: angular error, FPS,
  processing latency (ms). No decorative animation on these numbers — they update by replacing
  the value, not by counting/tweening, because this is live telemetry, not a marketing counter.
- **Bottom strip:** a scrolling event log (timestamped: "12.4s — target acquired", "13.3s —
  disturbance: vibration active", etc.) — this is the in-app version of the "failure replay"
  concept from the Build Plan; keep the last ~8 events visible, oldest fades out.

**Motion:** the HUD panels themselves never move or animate decoratively — they are instruments,
not UI flourishes. Only the state-graph node fill and the telemetry values change.

---

## Screen 3 — Tracking Console

**Purpose:** deeper real-time introspection than Screen 2 — for when a judge asks "show me what
the estimator is actually doing," not just the outcome.

**Layout:** three stacked panels, all `--field` on `--void`:
1. **State vector panel** — the live `[θx, θy, ωx, ωy, ax, ay]` values in a fixed-width monospace
   grid, updating every frame. Label each value's unit (deg, deg/s, deg/s²) small and dim below it.
2. **Uncertainty visualization** — a 2D plot (angular space) showing the predicted position as a
   point with a covariance ellipse around it, `--lock-cyan` outline, fill opacity scales with
   confidence (more opaque = more confident). This is the single most technically credible visual
   in the whole app — do not simplify it into a generic loading spinner or icon.
3. **Predicted vs. actual trajectory overlay** — a trailing line of actual detected positions
   (solid `--lock-cyan`) against the estimator's predicted path (dashed, dimmer).

---

## Screen 4 — Stress Lab

**Purpose:** the disturbance injection console — where a judge (or the team) deliberately breaks
the system on demand, live.

**Layout:** left column, sliders/toggles for each disturbance type from the Disturbance Engine
(vibration, sensor noise, motion blur, signal-intensity fluctuation, occlusion duration, false
distractor count, actuator latency) — each slider's active/non-zero state highlights its label in
`--disturbance-amber` (this is the one screen where amber appears constantly, correctly, because
this screen's entire purpose IS disturbance). Right column: the same live 3D view as Screen 2,
so the effect of every slider is visible immediately, not just implied.

**Preset row** at the top: five buttons — NOMINAL, DIFFICULT, SEVERE, RECOVERY, ADVERSARIAL — each
sets all sliders at once to the named preset's values. Selected preset button fills solid;
manually adjusting any slider after a preset selection deselects the preset (shows "Custom").

---

## Screen 5 — Benchmark Lab

**Purpose:** the actual proof screen — Monte Carlo comparison across algorithms. This is the
in-app counterpart to Act V of the website; the numbers shown here are the same numbers exported
into that website section, not a separate dataset.

**Layout, top to bottom:**
1. **Run configuration row:** algorithm checkboxes (same as Screen 1, editable here too), trial
   count input (default 500), `RUN N TRIALS` button (`--lock-cyan`, large — this is the screen's
   primary action, and running it should visibly indicate progress: a monospace trial counter
   ticking up, e.g. `247 / 500`, not a generic progress bar).
2. **Results table:** rows = metrics (acquisition success %, median/P95 time-to-lock, mean/P95/P99
   tracking error, lock retention %, reacquisition time, false-lock rate), columns = one per
   selected algorithm. The "Ours" column, if better than all baselines on a given row, gets that
   cell's value in `--confirm-green`; if worse, `--lost-red`; ties/neutral stay default text
   color. This is the one place in the whole app where color directly encodes a comparative
   result — do this only here, do not replicate this pattern elsewhere.
3. **Robustness envelope plot:** the 2D operating-region chart from Build Plan Section 6.9 — do
   not omit this in favor of just the table; it's the differentiator visual.
4. **Failure replay:** a list of specific trials where the selected "Ours" run lost lock, each
   with a `REPLAY` button that re-renders that exact seeded trial on Screen 2.

---

## Cross-screen rule
Every screen reads from the same underlying telemetry/state objects — there is no screen-specific
"fake" data anywhere, including Mission Setup's preview render. If a screen cannot yet get real
data (e.g., Benchmark Lab before any run has completed), show an explicit empty state
("No runs yet — configure and press RUN"), never a placeholder number.
