# HORIZON — Website Implementation Contract

This is the execution companion to `HORIZON_PREMIUM_WEBSITE_DESIGN_DOCUMENTATION.md`.

## 1. Objective

Build an original, premium HORIZON web experience inspired by the observable interaction sophistication of IVRESS, United Carriers, Thorgal, Boiler Lab and Segerman.

Do not duplicate reference source code, assets, exact compositions, audio or branding.

## 2. Stack

- Next.js
- React
- TypeScript
- Three.js
- WebGPU where available
- WebGL fallback
- GSAP + ScrollTrigger
- optional smooth scrolling
- GLSL/TSL/custom shaders
- GLB/glTF
- compressed textures
- JSON-driven benchmark data

## 3. Repository

```text
horizon-web/
├── app/
├── components/
│   ├── experience/
│   ├── navigation/
│   ├── typography/
│   ├── benchmark/
│   └── accessibility/
├── three/
│   ├── core/
│   ├── scenes/
│   ├── camera/
│   ├── shaders/
│   ├── particles/
│   └── assets/
├── data/
│   ├── benchmark-summary.json
│   ├── scenarios.json
│   └── telemetry/
├── public/
│   ├── models/
│   ├── textures/
│   ├── audio/
│   └── stills/
├── styles/
├── lib/
└── docs/
```

## 4. Runtime architecture

```text
ExperienceRoot
 ├── RenderCanvas
 ├── SceneController
 ├── CameraRig
 ├── TimelineController
 ├── ChapterRail
 ├── TextLayer
 ├── AudioLayer
 └── DataLayer
```

## 5. Chapter IDs

```text
PRELOAD
PROLOGUE
UNKNOWN
CAMERA
SEARCH
ACQUIRE
TRACK
DISTURBANCE
LOSS
REACQUIRE
SYSTEM
PROOF
CLOSING
```

## 6. Scroll system

Normalize global progress to `[0, 1]`. Each chapter maps that progress into a local chapter range. All major animations derive from this state rather than scattered scroll listeners.

## 7. Camera system

Every chapter owns:

- start transform;
- end transform;
- look target;
- FOV;
- easing;
- optional follow target;
- maximum movement rate.

Use spline/damped motion where appropriate. Avoid frame-dependent accumulation.

## 8. Transition primitives

Implement reusable primitives:

```text
CameraThrough
Aperture
SignalParticle
SpatialDecompose
DataTransform
DarkPause
```

## 9. Persistent canvas

Use one primary renderer/canvas. Do not mount and destroy a separate WebGL scene for each chapter.

## 10. Asset rules

Every asset receives:

- semantic name;
- source/provenance record;
- license record;
- intended chapter;
- display size target;
- fallback.

## 11. Blender handoff

For every finished chapter export:

```text
chapter.blend
chapter-preview.mp4
chapter-camera.json
chapter-notes.md
```

Camera JSON: time, position, rotation, look target, FOV.

## 12. Shader rules

Each shader must document:

- purpose;
- parameters;
- GPU cost expectation;
- low-quality fallback;
- disable behavior.

## 13. Particle quality tiers

```text
HIGH
MEDIUM
LOW
OFF
```

## 14. Data rules

All performance data must come from exported HORIZON files.

If data is absent:

```text
MEASUREMENT UNAVAILABLE
```

Never insert plausible fake numbers.

## 15. Benchmark presentation

Support, when available:

- run ID;
- algorithm;
- scenario;
- seed;
- acquisition time;
- tracking error;
- RMSE;
- max error;
- reacquisition time;
- lock retention;
- FPS;
- processing time;
- failure/loss state.

Always show context/sample count.

## 16. Website ↔ Unity boundary

Unity is responsible for actual simulation/benchmark behavior.

The website is responsible for narrative, visual explanation, exported replay/telemetry visualization and proof presentation.

## 17. Responsive quality levels

```text
HIGH
MEDIUM
LOW
FALLBACK
```

Use capability detection. Do not ship full desktop effects unchanged to mobile.

## 18. Accessibility

Implement keyboard navigation, focus visibility, reduced-motion mode, semantic headings, labels, contrast, captions where necessary and a meaningful non-WebGL fallback.

## 19. Error handling

If a 3D asset fails, fall back without breaking the page.

If benchmark JSON fails, show a data-unavailable state.

## 20. AI agent anti-hallucination rules

Stop and request clarification/source material when:

- a benchmark value is missing;
- a technical fact is uncertain;
- an asset license is unclear;
- a mission-specific claim is not sourced;
- required visual behavior conflicts with the design bible.

Do not “fill in realistic values.”

## 21. AI agent anti-copy rules

Do not:

- scrape/copy IVRESS source;
- copy IVRESS models/textures/music;
- reproduce exact composition;
- reproduce exact camera choreography;
- copy logos or branding;
- create an indistinguishable clone.

Implement original HORIZON equivalents.

## 22. Development order

```text
01 STORYBOARD
02 BLENDER BLOCKING
03 GREYBOX WEB EXPERIENCE
04 CAMERA SYSTEM
05 TYPOGRAPHY
06 TRANSITIONS
07 FINAL 3D ASSETS
08 SHADERS
09 PARTICLES
10 SOUND
11 DATA LAYER
12 RESPONSIVE/FALLBACK
13 PERFORMANCE
14 ACCESSIBILITY
15 FINAL POLISH
```

## 23. Quality gates

### Gate A — Greybox

Must show complete chapter sequence, camera timing and text timing.

### Gate B — Art block

Must establish composition, materials, lighting and atmosphere.

### Gate C — Realtime

Must show optimized GLB, shaders, particles and responsive behavior.

### Gate D — Data

Must show real benchmark JSON, units and no fabricated values.

### Gate E — Production

Must pass desktop/tablet/mobile/reduced-motion/WebGL fallback checks.

## 24. Agent completion report

Every phase ends with:

```text
IMPLEMENTED
BLOCKED
MEASURED
NOT YET IMPLEMENTED
RISKS
NEXT GATE
```

“Complete” is not allowed to mean “the page renders.”

## 25. Definition of Done

- all chapters exist;
- camera paths are authored;
- transitions have narrative meaning;
- assets have provenance;
- benchmark data is source-backed;
- mobile fallback works;
- reduced-motion works;
- WebGL failure does not destroy content;
- performance is measured;
- the page feels like one coherent world;
- no visual effect exists only because the agent thought it looked cool.
