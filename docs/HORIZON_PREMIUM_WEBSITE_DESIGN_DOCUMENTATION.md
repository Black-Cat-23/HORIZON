# HORIZON — Premium Web Experience Design & Production Bible

**Project:** HORIZON  
**SIH Problem Statement:** SIH26169 — Development of an AI-Based Virtual Camera Tracking System for Coarse Alignment of Mobile Free Space Optical Communication (FSOC) Terminals  
**Primary experience reference:** IVRESS `brand.ivress.co.jp`  
**Secondary references:** `segerman.dev`, `boilerlab.ai`, `thorgal.com/albums`, `unitedcarriers.com`  
**Purpose:** Complete creative direction, UX architecture, motion language, 3D/WebGL strategy, content system, data strategy, production workflow and implementation acceptance criteria.

> **Reference policy:** Learn from observable interaction/design principles and publicly described production techniques. Independently author HORIZON's copy, visual assets, layouts, scene composition, animation timings, 3D models, audio and source code. Do not make an indistinguishable duplicate or reuse copyrighted/proprietary assets or source code.

---

# 1. NORTH STAR

HORIZON is not a conventional marketing website and it is not a game.

It is a **cinematic engineering narrative** explaining a software-in-the-loop coarse pointing, acquisition and tracking system through a continuous spatial experience.

The visitor should feel as if they have entered a virtual optical test range and are progressively learning the same sequence the underlying system must solve:

```text
UNKNOWN
   ↓
SEARCH
   ↓
ACQUIRE
   ↓
TRACK
   ↓
DISTURB
   ↓
LOSE
   ↓
REACQUIRE
   ↓
PROVE
```

The website has two jobs:

1. Make the engineering problem immediately understandable.
2. Demonstrate a level of interaction, motion and visual craft appropriate for a premium digital experience.

The website is **not** the Unity simulation. Unity remains the actual HORIZON experimental application. The website is the cinematic explanatory and proof layer around it.

---

# 2. PROJECT TRUTH — SOURCE OF AUTHORITY

The supplied SIH26169 problem statement requires a software system able to generate a configurable virtual environment, generate moving target(s), implement a movable virtual camera, automatically detect the target beacon, continuously track it, control/reposition the camera, inject disturbances, and display real-time performance/statistics.

The problem statement specifies camera/target defaults including a monochrome focal-plane camera, 640×480 default resolution, user-defined FOV with 4°×3° default, at least 30 Hz camera update rate, a beacon spot target, selectable target motion including straight line/circular/figure-eight/random, and pan/tilt speed limits. It also specifies benchmark checks involving centroiding error, automatically generated performance logs, and an external 30 FPS MP4 video input mode. 

**Website implication:** the cinematic layer must reinforce the real system rather than invent a different product.

Never fabricate:

- benchmark values;
- AI accuracy;
- “ISRO validated” claims;
- physical hardware performance;
- mission-specific information not supplied by the team;
- fake partnerships or customers;
- fake technical measurements;
- fake research novelty.

When a real benchmark is unavailable, show a neutral “measurement unavailable / awaiting benchmark export” state.

---

# 3. REFERENCE ANALYSIS

## 3.1 IVRESS — PRIMARY REFERENCE

### What the live experience establishes

The current IVRESS experience presents a dark, cinematic, chapter-driven journey. It opens with an explicit start interaction, uses a numbered progression through nine narrative chapters, makes scrolling the primary continuing interaction, and exposes a hold/tap interaction for selected moments.

### What the production team publicly confirmed

The IVRESS production interview is unusually useful because it describes the actual workflow:

- rough Blender blocking was done first;
- blocking was used to design space, camera movement and timing/rhythm;
- the team did not simply export the Blender world to the browser;
- lighting, fog, gradients, particles, materials and camera behavior were reconstructed for realtime rendering;
- Three.js WebGPU was used, with WebGL considerations for compatibility;
- expensive content was converted into lighter/baked/point-style representations when appropriate;
- particle density and scene detail were repeatedly iterated;
- sound and sound effects were part of the experience design.

### HORIZON principle

**Use the same production philosophy, not the same artwork.**

```text
story
 ↓
blocking
 ↓
camera choreography
 ↓
art direction
 ↓
realtime reconstruction
 ↓
optimization
 ↓
interaction
```

### What to borrow conceptually

- scrolling as the main narrative transport;
- continuous spatial continuity;
- camera movement as storytelling;
- meaningful rather than ubiquitous interaction;
- atmosphere and depth over UI clutter;
- authored 3D scenes;
- transitions motivated by visual elements;
- sound as a supporting narrative layer;
- Blender for timing/blocking before final realtime production.

---

## 3.2 UNITED CARRIERS — SPATIAL PROPOSITION

The current United Carriers site places a large proposition next to a persistent geographic/logistics visual language, then transitions into evidence, services, industries, insights and contact. The site makes its spatial metaphor carry meaning rather than existing only as decoration.

### HORIZON principle

Do not copy the globe. Copy the idea that **the core 3D object should embody the proposition**.

For United Carriers:

```text
journey → network → outcome
```

For HORIZON:

```text
uncertainty → pointing → acquisition → tracking → recovery
```

Use a persistent 3D test range instead of disconnected hero illustrations.

---

## 3.3 THORGAL — WORLD / GATE / CHAPTER NAVIGATION

The current Thorgal albums experience exposes numbered “doors” for major areas such as universe, albums, characters, authors and community. The albums area then provides category filters and a large editorial content field.

### HORIZON principle

Build a sense of **entering a world**.

HORIZON's chapters become controlled entry points:

```text
01 PROLOGUE
02 SIGNAL
03 CAMERA
04 SEARCH
05 ACQUIRE
06 TRACK
07 DISTURBANCE
08 RECOVERY
09 SYSTEM
10 PROOF
```

Do not turn navigation into a videogame menu. Keep it quiet.

---

## 3.4 BOILER LAB — TYPOGRAPHIC CONFIDENCE + EVIDENCE

The current Boiler Lab site begins with an oversized statement, continues through supporting explanation, quantified evidence, ecosystem elements, and long-form product progression.

### HORIZON principle

Typography can become the visual architecture.

Use short, decisive statements:

```text
FIND THE SIGNAL.
KEEP IT IN VIEW.
SURVIVE DISTURBANCE.
RECOVER THE LOCK.
```

Every large statement must be followed by visual/technical evidence.

---

## 3.5 SEGERMAN — RESTRAINT

The current Segerman portfolio is extremely sparse: name, role, one positioning statement, project index, contact and availability.

### HORIZON principle

Premium does not mean maximum density.

Use deliberate quiet intervals between major cinematic events.

```text
high density → silence → high density → silence
```

This contrast makes the important moments feel expensive rather than noisy.

---

# 4. HORIZON DESIGN DNA

## Keywords

Cinematic, atmospheric, precise, technical, spatial, editorial, restrained, dark, tactile, scientific, confident.

## Explicitly avoid

Cyberpunk overload, generic AI aesthetics, gamer HUDs, giant glowing lasers, random satellites, floating hologram grids, excessive glassmorphism, rainbow gradients, pointless particle storms, fake dashboards, arbitrary camera shake, bouncy UI motion, AI-generated-looking telemetry.

---

# 5. INFORMATION ARCHITECTURE

The experience is one persistent world, not a collection of unrelated page templates.

Recommended chapter sequence:

```text
00 PRELOAD / INITIALIZATION
01 THE UNKNOWN SIGNAL
02 THE CAMERA
03 SEARCH
04 ACQUISITION
05 TRACK
06 DISTURBANCE
07 LOSS
08 REACQUISITION
09 SYSTEM
10 PROOF
11 CLOSING
```

The exact scroll ratio per chapter is tunable after storyboard testing.

---

# 6. MASTER STORYBOARD

## 00 — INITIALIZATION

### Purpose
Create a deliberate “enter the experience” moment.

### Visual state
Nearly black. Extremely sparse particles/stars. Tiny distant signal.

### Text
```text
HORIZON

AI-ASSISTED COARSE ALIGNMENT
FOR MOBILE FSOC TERMINALS

INITIALIZING VIRTUAL TEST RANGE
```

Then a small start prompt:

```text
CLICK TO ENTER
SCROLL TO CONTINUE
```

### Motion
Slow ambient drift. Title fades/reveals vertically. No bounce.

### Rule
Loading progress must correspond to actual loading progress.

---

## 01 — THE UNKNOWN SIGNAL

### Purpose
Make the acquisition problem instantly understandable.

Start with a very wide shot. The terminal is small. The beacon exists far outside the camera's pointing direction.

Large statement:

```text
THE SIGNAL
IS THERE.

WE DON'T
KNOW WHERE.
```

Visual elements:

- terminal;
- distant target;
- FOV cone;
- boresight;
- target uncertainty region;
- optional initial angular-offset readout.

Transition: camera approaches the terminal.

---

## 02 — THE CAMERA

### Purpose
Make the virtual camera the protagonist.

Sequence:

1. camera approaches terminal;
2. close-up on pan/tilt mechanism;
3. camera begins rotating;
4. FOV cone appears;
5. scene aligns with optical axis;
6. view transitions toward sensor domain.

Headline:

```text
A NARROW WINDOW
ON THE WORLD.
```

The 3D camera rotation must have conceptual consistency with the camera model used by the product.

---

## 03 — SEARCH

### Purpose
Explain acquisition.

The camera sweeps through the uncertainty region. A subtle search path may be shown.

Headline:

```text
SEARCH.
```

Then smaller supporting text:

```text
The beacon is not yet inside the camera's useful view.
```

No giant sci-fi “radar.” The search path itself should do the explaining.

---

## 04 — ACQUISITION

When the virtual sensor's field reaches the beacon:

```text
SIGNAL FOUND
ACQUIRE
```

Show a detection marker, confidence or centroid only when it reflects an actual selected demonstration.

Use the lens/aperture as a transition device into the sensor image.

The visitor should understand:

```text
world view → sensor observation → detected signal
```

---

## 05 — TRACK

Target now follows a meaningful trajectory.

Show, selectively:

- target trajectory;
- estimated trajectory;
- camera boresight;
- LOS;
- target position;
- angular/pixel error;
- state label.

Minimal telemetry example:

```text
MODE      TRACK
AZ ERROR  +0.12°
EL ERROR  −0.08°
LOCK      TRUE
FPS       58
```

These are **example field structures only**. Values must be actual HORIZON telemetry before publication.

The camera should visibly follow the target instead of simply teleporting toward it.

---

## 06 — DISTURBANCE

This is the narrative low point.

Visual changes may include:

- atmospheric contrast reduction;
- controlled jitter;
- sensor noise;
- subtle blur/degradation;
- target visibility reduction;
- uncertainty growth.

State:

```text
TRACK
  ↓
DEGRADED
```

The disturbance must correspond to an actual disturbance parameter in the conceptual model.

Do not add random camera shaking just for drama.

---

## 07 — LOSS

The beacon becomes unavailable or unreliable.

State:

```text
DEGRADED
  ↓
LOST
```

The scene becomes visually quieter.

Headline:

```text
LOCK LOST.
```

Supporting line:

```text
RECOVERY IS PART OF THE PROBLEM.
```

---

## 08 — REACQUISITION

The system searches again using the recovery concept.

State:

```text
REACQUIRE
  ↓
TRACK
```

The visual payoff is stabilization rather than an action-movie climax.

The beacon reappears. The camera settles. The environment becomes readable again.

Headline:

```text
RECOVER.
```

---

## 09 — SYSTEM

The environment becomes a visual architecture explanation.

```text
SCENARIO
   ↓
SENSOR / VIRTUAL CAMERA
   ↓
PERCEPTION
   ↓
TARGET ASSOCIATION
   ↓
STATE ESTIMATION
   ↓
MODE MANAGER
   ↓
CONTROL
   ↓
CAMERA
```

Modules should appear in the same spatial world rather than as unrelated cards.

Hovering/clicking a module should reveal a concise explanation of what enters, what leaves and why the module exists.

---

## 10 — PROOF

This is the most factual section.

Use actual exported HORIZON benchmark results.

Recommended evidence:

- acquisition-time distribution;
- RMSE / tracking-error distribution;
- reacquisition distribution;
- lock-retention distribution;
- FPS distribution;
- processing-time distribution;
- scenario count;
- trial count;
- selected run replay.

Display sample count and algorithm/scenario context.

Never present an isolated percentage without context.

---

## 11 — CLOSING

Return to the opening atmosphere.

The beacon is locked. The camera is stable.

```text
FROM SEARCH
TO LOCK.

HORIZON
```

Supporting line:

```text
A SOFTWARE-IN-THE-LOOP TEST RANGE
FOR COARSE POINTING, ACQUISITION AND TRACKING.
```

---

# 7. VISUAL SYSTEM

## Core palette

```text
VOID        #05070B
DEEP FIELD  #0B1018
FIELD       #121A24
TEXT        #F0F3F4
MUTED       #89929A
SIGNAL      #A9D8E8
LOCK        #6FE8A8
WARNING     #E8A15C
LOSS        #E86F7F
```

Semantic rules:

- Signal/cyan = optical/system information.
- Green = confirmed lock/success.
- Amber = actual disturbance/warning.
- Red = target loss/error.
- White/gray = structure/explanation.

Never use red or amber as decoration.

---

# 8. TYPOGRAPHY

Use a high-character contemporary grotesk/editorial sans for display, a legible neutral sans for body text, and a monospaced family for telemetry.

Recommended display sizing:

```css
font-size: clamp(4rem, 10vw, 11rem);
```

where the exact value is adjusted per composition.

Typography must be treated spatially: large text establishes the chapter idea, smaller text provides engineering context.

Never turn every paragraph into a giant headline.

---

# 9. LAYOUT

Desktop uses a generous 12-column conceptual grid.

The 3D canvas should feel permanent.

```text
┌─────────────────────────────────────────────┐
│ HORIZON / quiet navigation                  │
├─────────────────────────────────────────────┤
│                                             │
│          PERSISTENT 3D WORLD                │
│                                             │
│    chapter text                 progress    │
│                                             │
│                                             │
├─────────────────────────────────────────────┤
│ secondary information / controls             │
└─────────────────────────────────────────────┘
```

Do not mount a new WebGL canvas for every chapter.

---

# 10. NAVIGATION

Primary navigation should be quiet:

```text
HORIZON
01 02 03 04 05 06 07 08 09 10
```

or a vertical chapter rail.

Behavior:

- current chapter visible;
- inactive chapters subdued;
- clicking smoothly moves to chapter progress;
- scrolling updates current chapter;
- 3D world remains mounted.

---

# 11. CURSOR

Desktop custom pointer is optional.

States:

- normal: tiny dot;
- interactive: slightly expanded ring;
- drag/scrub: directional cue.

Never use a huge neon cursor trail.

---

# 12. MOTION LANGUAGE

Motion categories:

### Micro
100–250 ms: hover, small UI response.

### UI
300–700 ms: panel/state reveal.

### Scene
0.9–2 s: object reveal/transition.

### Cinematic
2–8 s: major camera travel or world transformation.

Rules:

- no elastic/bouncy UI;
- no arbitrary spring animations;
- no constant camera motion;
- use anticipation before large movements;
- use settling after movement;
- maintain spatial continuity.

---

# 13. CAMERA CHOREOGRAPHY

Camera is the primary narrative instrument.

Required principles:

1. Every movement needs a reason.
2. The camera must often pause.
3. Major movement should feel weighted.
4. The visitor should understand where they are moving.
5. Avoid motion sickness.
6. Never rotate the world just to fake a camera move when the semantic event is a camera move.
7. Keep target/camera/terrain spatial relationships legible.

Preferred motion types:

- slow dolly;
- spline travel;
- controlled orbital reveal;
- damped follow;
- deliberate pan/tilt;
- slow settle.

---

# 14. TRANSITION GRAMMAR

Build reusable transition primitives.

## Camera-through
The camera physically moves through/into the next scene.

## Aperture
The optical aperture becomes the transition into sensor space.

## Signal
Beacon glow/particles transform into the next information layer.

## Decomposition
One world separates into system modules.

## Crystallization
Chaotic scene transitions into structured benchmark data.

## Dark pause
Used sparingly to give the visitor a reset.

Avoid generic `fadeIn/fadeOut` as the main transition language.

---

# 15. 3D WORLD SPECIFICATION

## World hierarchy

```text
World
├── Environment
│   ├── Sky
│   ├── Atmosphere
│   ├── Terrain
│   └── Distant landmarks
├── Observer
│   ├── Terminal
│   ├── Pan stage
│   ├── Tilt stage
│   └── Virtual camera
├── Target space
│   ├── Beacon
│   ├── Target body
│   ├── Distractors
│   └── Trajectory
├── Optical visualization
│   ├── FOV
│   ├── Boresight
│   ├── LOS
│   ├── Search path
│   └── Error marker
└── Effects
    ├── Signal particles
    ├── Atmosphere
    ├── Disturbance visualization
    └── Transition particles
```

## Object purpose rule

Every object must answer:

> “Why is this object in the scene?”

If the answer is “because it looks cool,” remove it.

---

# 16. BLENDER PRODUCTION WORKFLOW

The Blender stage follows the lesson of the researched IVRESS production process: block the experience before polishing it.

## Phase A — Blocking

Use primitive geometry only.

Define:

- camera path;
- major objects;
- scene scale;
- light direction;
- fog density;
- text anchor positions;
- approximate timing.

Deliver a short preview for every chapter.

## Phase B — Art direction

Replace primitive geometry with authored models and controlled material/lighting design.

## Phase C — Look development

Tune:

- exposure;
- silhouette;
- roughness;
- fog;
- signal intensity;
- particle density;
- atmospheric depth.

## Phase D — Runtime optimization

Export only what the browser needs.

Use GLB/glTF, compressed textures, instancing, baked animation/lightweight data and shaders where appropriate.

Do not send an enormous unoptimized Blender scene into the browser.

---

# 17. SHADERS

Each custom shader needs a declared purpose.

Suggested modules:

```text
AtmosphereShader
SignalGlowShader
DisturbanceShader
TechnicalLineShader
TerrainDetailShader
```

Shader documentation must record:

- visual role;
- parameters;
- expected cost;
- low-quality fallback;
- disable behavior.

---

# 18. PARTICLES

Use particles for:

- atmosphere;
- signal presence;
- uncertainty;
- transitions;
- subtle environmental movement.

Provide quality levels:

```text
HIGH
MEDIUM
LOW
OFF
```

Particle quantity is tuned for the story and hardware rather than copying a fixed reference count.

---

# 19. LIGHTING

Priority order:

1. readable silhouette;
2. beacon visibility;
3. terminal separation;
4. atmospheric depth;
5. surface detail.

The beacon should normally be the brightest meaningful optical signal in the scene.

Do not turn the environment into a neon light show.

---

# 20. SOUND

Sound is optional and should never block understanding.

Suggested layers:

- quiet environment;
- subtle terminal/mechanical sound;
- acquisition confirmation;
- disturbance tension layer;
- lock/recovery resolution cue.

Respect browser autoplay restrictions and provide explicit sound enable/mute controls.

---

# 21. HORIZON VISUAL VOCABULARY

## Target
A clear moving object with a distinct beacon point.

## Beacon
Small, high-salience optical signal.

## FOV
Transparent cone or frustum.

## Boresight
Thin directional line from the camera.

## LOS
Dashed line between camera and target.

## Ground truth
Dedicated reference style.

## Estimated trajectory
Distinct but restrained line style.

## Uncertainty
Soft volume/halo rather than giant rings.

## Detection
Reticle/box only when detection is active.

---

# 22. INTERACTION MODEL

Primary interaction:

**scroll**

Secondary interactions:

- chapter jump;
- start/enter;
- optional audio toggle;
- optional diagnostic hover/click;
- optional benchmark trial selection.

Avoid turning the site into a collection of mini-games.

---

# 23. DATA CONTRACT

Benchmark proof must be data-driven.

Recommended public data shape:

```text
/public/data/
  benchmark-summary.json
  scenarios.json
  telemetry/
    demo-track.json
```

Example:

```json
{
  "schema_version": "1.0",
  "source": "HORIZON Benchmark Lab",
  "scenarios": 5,
  "algorithms": ["B0", "B1", "B2", "OURS"],
  "metrics": {
    "acquisition_time_s": {},
    "tracking_rmse_px": {},
    "reacquisition_time_s": {},
    "lock_retention_pct": {},
    "fps": {}
  }
}
```

Do not hardcode benchmark claims into JSX.

If data is absent, render a neutral unavailable state.

---

# 24. WEBSITE ↔ UNITY RESPONSIBILITY BOUNDARY

## Unity owns

- actual simulation;
- virtual camera behavior;
- target dynamics;
- disturbances;
- perception/tracking;
- benchmark execution;
- automatic logs.

## Website owns

- story;
- visual explanation;
- narrative 3D scene;
- selected demo/replay visualization;
- exported benchmark presentation;
- project communication.

## Shared contract

- state names;
- telemetry vocabulary;
- visual semantic colors;
- benchmark schema;
- major diagrams.

---

# 25. RESPONSIVE STRATEGY

## Desktop

Full cinematic experience.

## Tablet

Reduce:

- particles;
- post-processing;
- simultaneous object count;
- texture quality.

Maintain the chapter story and camera choreography.

## Mobile

Do not simply shrink desktop.

Use:

- shorter camera travel;
- fewer objects;
- simplified atmospheric effects;
- reduced particle layers;
- simplified system visualization;
- static/video fallback for expensive scenes if required.

---

# 26. PERFORMANCE BUDGET

Initial targets:

- 60 FPS on capable desktop hardware;
- graceful 30 FPS behavior on weaker hardware;
- no severe frame drop during chapter transitions;
- no giant blocking assets;
- progressively load noncritical scenes.

Measure during development:

- frame time;
- FPS;
- draw calls;
- triangle count;
- texture memory where available;
- asset load time;
- chapter transition cost;
- memory growth.

---

# 27. LOADING

```text
PRELOAD
  ↓
LOAD CORE
  ↓
ENTER
  ↓
LAZY LOAD FUTURE CONTENT
```

Any visible progress value must correspond to real loading.

No artificial 20-second loading theatre.

---

# 28. ACCESSIBILITY

Provide:

- keyboard navigation;
- visible focus;
- reduced-motion mode;
- meaningful labels;
- semantic headings;
- sufficient text contrast;
- caption/transcript support for important audio;
- meaningful non-WebGL fallback.

Reduced-motion mode should preserve the narrative while replacing long camera travel with short transitions.

---

# 29. SEO / FALLBACK

Critical content must exist as semantic HTML, not only as pixels inside WebGL.

Provide:

- metadata;
- OG/social metadata;
- semantic headings;
- content equivalents;
- fallback stills or video for major visual scenes.

---

# 30. CONTENT VOICE

Use confident technical language.

Preferred:

> A software-in-the-loop test range for coarse optical pointing, acquisition and tracking.

Avoid:

> Revolutionary next-generation AI space magic.

Avoid generic startup clichés and unsupported superlatives.

---

# 31. HORIZON COPY SYSTEM

Every chapter uses:

```text
BIG IDEA
↓
1–2 sentence explanation
↓
visual proof
↓
optional technical detail
```

Example:

```text
FIND
THE SIGNAL.

Before tracking begins, the system must locate a beacon
whose angular position is uncertain.
```

Then immediately show the camera/search relationship.

---

# 32. BENCHMARK PROOF DESIGN

Show distributions and context rather than single vanity numbers.

Preferred:

```text
500 trials
5 scenarios
3 disturbance classes

Acquisition time
median / P95

Tracking error
RMSE / P95

Recovery
median / P95

Lock retention
distribution

FPS
distribution
```

Numbers must come from real HORIZON exports.

---

# 33. SYSTEM ARCHITECTURE VISUALIZATION

The visitor should understand data flow:

```text
SCENARIO
  │
  ▼
SENSOR
  │
  ▼
PERCEPTION
  │
  ▼
ESTIMATION
  │
  ▼
MODE
  │
  ▼
CONTROL
  │
  ▼
CAMERA
  │
  └──────── feedback ───────►
```

Hover/click isolates the relevant flow and dims unrelated modules.

---

# 34. ANIMATION ANTI-PATTERNS

Never use:

- character-scrambling text for no reason;
- permanent cursor trails;
- random parallax;
- constant camera drift;
- every element flying in from a different direction;
- UI bounce;
- giant light flashes for ordinary state changes;
- generic fade transitions as the only transition mechanism.

---

# 35. CREATIVE QA QUESTIONS

Before accepting a scene:

1. What is the viewer supposed to understand here?
2. What changed from the previous scene?
3. Why is the camera moving?
4. Which object carries the narrative meaning?
5. Does the text reinforce the visual event rather than repeat it?
6. Is any effect purely decorative?
7. Does the scene remain legible without sound?
8. Does the scene remain plausible within HORIZON's technical story?

If an effect has no answer, remove it.

---

# 36. IMPLEMENTATION ARCHITECTURE

Preferred web stack:

```text
Next.js / React / TypeScript
        │
        ├── Three.js
        ├── WebGPU renderer when available
        ├── WebGL fallback
        ├── GSAP / ScrollTrigger
        ├── optional smooth-scroll layer
        ├── custom shaders
        ├── audio manager
        ├── chapter state machine
        └── HORIZON telemetry adapter
```

Core modules:

```text
ExperienceRoot
SceneController
CameraRig
ScrollTimeline
ChapterController
WorldRenderer
AssetManager
ShaderManager
ParticleManager
AudioManager
TelemetryStore
BenchmarkVisualizer
AccessibilityController
DeviceCapabilityManager
```

---

# 37. CHAPTER DATA MODEL

```ts
type Chapter = {
  id: string;
  title: string;
  progressStart: number;
  progressEnd: number;
  camera: CameraTimeline;
  visualState: VisualState;
  copy: CopyBlock;
  telemetry?: TelemetryBinding;
};
```

Animation should be data-driven enough that camera/timing values can be tuned without rewriting the component hierarchy.

---

# 38. BLENDER HANDOFF PACKAGE

Every authored chapter should generate:

```text
scene_name.blend
scene_name_preview.mp4
scene_name_camera.json
scene_name_notes.md
```

Camera JSON should store:

- timestamp;
- position;
- rotation;
- look target;
- FOV.

The runtime should implement the authored choreography, not invent a different one.

---

# 39. TEST MATRIX

Every chapter must pass:

## Functional

- correct scroll entry/exit;
- chapter navigation works;
- asset failures have fallbacks;
- state transitions complete.

## Visual

- composition readable;
- beacon readable;
- text does not collide with key geometry;
- camera path works;
- contrast remains controlled.

## Performance

- load time measured;
- peak frame time measured;
- transition cost measured;
- mobile quality tier tested.

## Accessibility

- keyboard navigation;
- reduced motion;
- no-WebGL fallback;
- focus visibility.

---

# 40. AI AGENT OPERATING RULES

The coding/design agent must:

1. Read this document before implementation.
2. Preserve chapter order unless a human explicitly changes it.
3. Never fabricate benchmark data.
4. Never introduce mission-specific facts without a trusted source.
5. Never add random 3D objects.
6. Never turn the website into a generic AI landing page.
7. Use authored camera paths rather than arbitrary movement.
8. Keep rendering modular.
9. Keep content separate from rendering.
10. Keep benchmark data external and data-driven.
11. Implement responsive degradation instead of assuming desktop hardware.
12. Record performance regressions.
13. Stop when a missing source or measurement prevents an honest implementation.

---

# 41. REFERENCE-DERIVED VS ORIGINAL

## Reference-derived interaction principles

- continuous narrative progression;
- persistent spatial world;
- cinematic camera choreography;
- meaningful interaction;
- chapter/gate navigation;
- kinetic typography;
- metrics as evidence;
- quiet/minimal intervals;
- realtime performance-aware 3D.

## HORIZON-original material

- all HORIZON story content;
- all HORIZON copy;
- all 3D models;
- all scene compositions;
- all camera paths;
- all textures/materials;
- all audio;
- all benchmark visualizations;
- all technical diagrams;
- all code.

---

# 42. THE EXPERIENCE MUST NOT FEEL LIKE FIVE WEBSITES

Do not create:

```text
IVRESS page
+ United Carriers page
+ Thorgal page
+ Boiler Lab page
+ Segerman page
```

Instead:

```text
               HORIZON
                  │
          one coherent world
                  │
    ┌─────────────┼─────────────┐
    │             │             │
  cinematic     editorial      proof
  camera        type           data
    │             │             │
    └─────────────┼─────────────┘
                  │
             one experience
```

The visitor should remember HORIZON, not the references.

---

# 43. FINAL EMOTIONAL ARC

The desired psychological sequence:

```text
CURIOUS
  ↓
ORIENTED
  ↓
UNCERTAIN
  ↓
UNDERSTANDING
  ↓
IMPRESSED
  ↓
TENSION
  ↓
RELIEF
  ↓
TRUST
```

The final impression must be:

> “They actually built and measured something.”

Not:

> “They know how to make pretty websites.”

---

# 44. DEFINITION OF “IVRESS-CLASS”

In this project, “IVRESS-class” means the following production qualities:

- authored 3D world;
- cinematic camera;
- deliberate spatial transitions;
- scroll as narrative transport;
- strong art direction;
- subtle atmospheric effects;
- purposeful typography;
- selective interaction;
- sound integrated but optional;
- realtime performance engineering;
- responsive fallback.

It does **not** mean a pixel-for-pixel clone.

---

# 45. FINAL NORTH-STAR TEST

The site is ready only when a first-time visitor can answer, without a team member talking over the experience:

1. What problem is HORIZON solving?
2. What is the beacon?
3. What is the virtual camera doing?
4. Why does the camera need to search?
5. What happens when the environment is disturbed?
6. What does recovery mean?
7. What does the system architecture look like?
8. Where is the evidence that it works?

And a technically minded reviewer should also be able to tell:

- which visuals are narrative;
- which values are actual measurements;
- which data is exported from HORIZON;
- which elements are illustrative rather than measured.

---

# 46. SOURCE REGISTER

## HORIZON / SIH source

Official supplied SIH26169 problem statement. This is the authority for project requirements and evaluation criteria.

## IVRESS

Live site:
https://brand.ivress.co.jp/

Production interview — concept, Blender blocking, realtime rendering, camera/timing:
https://www.s5-style.com/interviews/35/

Production interview — scenes, particles, audio, performance:
https://www.s5-style.com/interviews/36/

## Segerman

https://segerman.dev/

## Boiler Lab

https://boilerlab.ai/

## Thorgal

https://www.thorgal.com/albums

## United Carriers

https://unitedcarriers.com/

---

# 47. FINAL PRINCIPLE

**Do not make HORIZON look like a spacecraft command center merely because aerospace is involved.**

Make an abstract engineering problem physically understandable.

The strongest visual metaphor is:

> **A narrow camera searching for a moving optical signal inside an uncertain, changing world.**

Everything else exists to support that idea.
