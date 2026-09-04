# SHARED CODING PROTOCOL — TWO AI AGENTS, ONE WINNING SYSTEM

## Rule 1 — One repository
Cursor and Antigravity work on the same Git repository. Never maintain two divergent implementations.

## Rule 2 — Interface before implementation
Any cross-boundary change requires a contract under `/docs/contracts/` first.

## Rule 3 — No fake metrics
Placeholder UI can use labels such as `NO RUNS YET`. It cannot display fake benchmark values.

## Rule 4 — No silent scientific assumptions
Every camera, filter, controller and disturbance parameter must have a source, derivation, or explicit provisional label.

## Rule 5 — Research first, runtime second
Python is the fast research/reference environment. Unity is the final runtime. A candidate algorithm is accepted into Unity only after the research harness has a known test case and measured behavior.

## Rule 6 — Baselines are mandatory
Never call something "Ours" until B0/B1/B2 have a reproducible benchmark result.

## Rule 7 — Improvement must be attributable
When adding a feature, run an ablation that isolates its contribution.

## Rule 8 — Failure is data
Log failures. Provide replayable seeds. Do not hide difficult scenarios.

## Rule 9 — Presentation must use real output
Website, application and final report must consume the same canonical telemetry/benchmark data.

## Rule 10 — Agents must report uncertainty
At the end of each session, state:
- what is proven
- what is implemented but not validated
- what assumptions remain
- what needs human/domain review
