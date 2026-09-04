# HORIZON — The 3D World Itself (Unity Scene Design)

Distinct from `UNITY_APP_UI_SPEC.md` (the UGUI overlay screens). This file is about what actually
exists IN the 3D scene those screens look at: the environment, the beacon, the camera rig
representation, disturbance visualization, lighting, and materials. Every element below states its
purpose before its implementation — if something can't earn a "why," it doesn't go in the scene.

Grounded in verified current Unity 6 URP capability, checked directly rather than assumed:
- Bloom (official URP Volume Override) — confirmed current, built-in.
- URP has NO native volumetric fog as of early 2026 (Unity has confirmed this is a known gap,
  no committed timeline) — so volumetric light shafts need a community package, not a built-in
  toggle. `CristianQiu/Unity-URP-Volumetric-Light` is a real, actively maintained, Unity-6-Render-
  Graph-compatible package for exactly this — verified current on GitHub.
- Adaptive Probe Volumes (APV) — real, built-in Unity 6 global-illumination system. Deliberately
  NOT used in this scene — see 1.4.

---

## 1. First principles — what this scene is actually for

### 1.1 It has two audiences with different needs, at the same time
A judge watching the Live Simulation screen needs to *feel* the problem (drift, disturbance, the
stakes of losing lock). The algorithm's detector needs a rendered frame that is honest sensor
data, not a stylized picture. **These are not the same image**, and treating them as one is the
single biggest mistake this scene could make. See Section 4 for how the two coexist.

### 1.2 Nothing is decoration
Every object in this scene either (a) is part of the actual simulated physics the algorithm
reasons about, or (b) exists specifically to make an invisible quantity visible to a human. If an
element is neither, it does not belong in the scene, no matter how good it looks in a screenshot.

### 1.3 Two different performance budgets — know which one you're building for
The Monte Carlo benchmark runs (Build Plan Section 6.10) execute headless via
`-batchmode -nographics` — there is no screen, no rendering, no GPU cost for these thousand-trial
runs. Everything in this document about visual fidelity applies ONLY to the interactive/demo
views (Screens 2–4 of the UI spec). Do not let visual-fidelity concerns creep into or slow down
the batch-simulation code path — they are architecturally separate concerns.

### 1.4 Restraint is a technical decision, not just a taste one
Adaptive Probe Volumes are Unity 6's real answer to complex indirect lighting on detailed
geometry. This scene has almost no geometry — void, a beacon, a camera rig, sparse particles.
APV's baking pipeline would spend engineering time solving a lighting-complexity problem this
scene doesn't have. Skip it. Two direct lights and Bloom will outperform it here, in both result
and time spent.

---

## 2. The Environment

### 2.1 The void
**What:** near-black background (`--void` #070912, matching the website's token — deliberate,
Section 8 of the UI/UX doc already established this continuity requirement).
**Why this exact value and not pure black:** pure black (#000000) reads as "nothing rendered" —
a bug, not a design choice, especially on projector displays with poor black levels at a judging
venue. A near-black with a whisper of blue keeps the space legible as an intentional void.

### 2.2 Starfield — NOT a skybox texture
**What:** a GPU particle system (VFX Graph), not a static skybox cubemap.
**Why particles, specifically:** a skybox is infinitely far and never moves relative to camera
translation — it would look painted-on and dead. A particle-based starfield at several depth
layers gives genuine parallax as the camera moves during acquisition/search sequences, which is
the single cheapest way to make the space feel like a volume instead of a backdrop. Three depth
bands (near/mid/far), each with different particle density and subtle independent drift speed,
sized in inverse proportion to distance so nearer "stars" are marginally brighter — this alone
sells depth without any additional lighting cost.
**What it must NOT do:** twinkle, pulse, or animate decoratively. Real distant light sources don't
flicker at a rate a camera 1/30s exposure would show. Static brightness, only positional parallax.

### 2.3 No ground plane, no horizon
**Why:** this is a coarse-alignment problem in open space/near-Earth relative motion — introducing
a ground plane or horizon line implies a reference frame (up/down, near/far in a terrestrial
sense) that does not exist in the actual problem and would misrepresent it. The absence of a
horizon is itself doing communicative work: it signals "there is no up here, only relative
angle," which is the actual physics.

---

## 3. The Beacon (Target)

### 3.1 Why it must NOT be a glowing sphere with a nice material
A sphere with an emissive material is legible to a human. It is not what a real optical beacon
looks like to a camera sensor, and this project's entire credibility argument (Build Plan Section
7) rests on refusing exactly this kind of "looks right, isn't real" shortcut.

### 3.2 What it actually is
A small, near-dimensionless point light source with:
- **Bloom** (URP Bloom Volume Override) driving the visible "size" of the point — the beacon's
  apparent size on screen is not geometry, it's the bloom kernel responding to intensity, exactly
  matching how a real bright point source blooms on a real camera sensor. This is not a visual
  trick chosen for looks — it is the physically correct behavior, and it happens to also look
  good, which is the right order of justification.
- **Intensity that is a live, bound variable**, not a fixed value — the Disturbance Engine's
  "signal-intensity fluctuation" (Build Plan Section 6.8) directly drives this value. When the
  Stress Lab (UI Spec Screen 4) increases signal fluctuation, the beacon visibly, physically dims
  and flickers — not a separate "disturbance FX" layered on top, the actual light value changing.
- **A soft, very subtle chromatic fringe at high bloom intensity** (a cheap post-process addition)
  — this reads as "optical," specifically distinguishing the beacon from the flat white dots of
  the starfield without needing separate geometry or color.

### 3.3 Distractor beacons (false targets)
Visually near-identical to the real beacon at a glance — this is deliberate and important: if a
distractor were visually distinguishable to a human eye, it would misrepresent the actual
detection problem (Build Plan Section 6.3's false-acquisition metric exists specifically because
distractors are NOT trivially distinguishable). The only difference: real beacon carries a subtle,
consistent signal-modulation pattern in its intensity over time (justified by 3.2's live-intensity
binding) that the classical/hybrid detector can key on — distractors modulate randomly or not at
all. This is not decoration, it's the literal mechanism Detector A (UI Spec / Build Plan Section
6.3) uses to reject false locks, made visible.

---

## 4. The Camera Rig — solving the "two audiences" problem from 1.1

### 4.1 The dual-view, and why it's not a stylistic choice
Real PAT/tracking operator consoles (and, structurally, most sensor-teleoperation UIs — gimbal
control software, telescope-tracking consoles) universally split into an external "world view" for
human situational awareness and a raw "sensor view" showing exactly what the algorithm sees. This
project adopts that same split for an honest, non-decorative reason: the external view proves the
scenario to a judge unfamiliar with the domain, and the raw sensor view proves the algorithm is
operating on the same noisy, bloomed, cluttered image a real detector would receive — not a clean
abstraction.
- **Main viewport (Screen 2, large):** third-person external framing — camera platform (a simple,
  low-poly gimbal/housing form, not a photorealistic satellite model; see 4.3 for why), the
  beacon, and a translucent frustum cone from the virtual camera showing its current field of
  view. The frustum cone's opacity is low (~15%) so it reads as instrumentation, not a solid
  object competing with the beacon for attention.
- **Inset (Screen 2, small, bottom-right corner):** the literal first-person render the detector
  algorithm receives — same synthetic image, same noise, same blur, same bloom — proving the
  detection is real by letting the judge watch it happen on the same feed the code sees.

### 4.2 The angular-error visualization
A thin reticle/crosshair rendered in the inset view (not the external view — it belongs to the
sensor's frame of reference, not the world's), offset from frame-center by the actual live
angular error. This is the single most information-dense element in the whole scene: a judge who
understands nothing else about PAT can watch this reticle chase the beacon and immediately grasp
"is it locked or not" without reading a single number.

### 4.3 Why the camera platform housing is deliberately simple, low-poly
A detailed, textured satellite/terminal model invites exactly the wrong question from a judge —
"did you model this from a real ISRO terminal spec?" — which this project cannot honestly answer
yes to (Build Plan Section 11's risk register: never claim hardware-equivalent fidelity). A
simple, clearly abstracted geometric form (a hexagonal prism housing, matte material, no
brand-like detailing) correctly signals "this represents a generic mobile FSOC terminal," which is
what the PS actually asks for, without overclaiming specificity the project hasn't earned.

---

## 5. Disturbance Visualization

Each disturbance type from the Disturbance Engine (Build Plan Section 6.8) gets ONE specific,
non-overlapping visual signature — never a generic "everything shakes" response, because that
would destroy the diagnostic value of watching which disturbance is currently active.

| Disturbance | Visual signature | Why this specific mapping |
|---|---|---|
| Platform vibration | The external-view camera rig housing itself micro-shakes (positional jitter on the housing mesh) | This is literally what vibration means — the platform, not the image |
| Sensor noise | Grain/speckle overlaid on the INSET view only | Sensor noise is a property of the detector's image, not the world — must not appear in the external view |
| Motion blur | Directional blur on the beacon in the inset view, scaled to relative angular velocity | Physically correct: blur is a function of the sensor's exposure vs. motion, visible only where the sensor "sees" it |
| Signal-intensity fluctuation | The beacon light itself dims/flickers (already specified in 3.2) | Already the correct, physical mechanism — no separate FX layer needed |
| Occlusion | The beacon's light fully cuts off; a very faint, barely-visible dark silhouette drifts across the frustum area | The faint occluding shape gives a human viewer a "why," even though the detector genuinely only sees "signal gone" |
| Actuator latency | NOT visualized as a separate effect — it shows up honestly as a lag between the reticle (4.2) and the beacon's true position | Inventing a visual for latency would be decorating a number that is already correctly visible as an emergent effect of 4.2 |
| False distractors | Section 3.3 | — |

**Explicit rule:** amber (`--disturbance-amber`, per the design-system rule file) tints the HUD
border and event-log entries when ANY disturbance is active, and only then — this is the same
"state colors mean something because they're rare" discipline from the design system rules,
applied inside the 3D view's surrounding chrome.

---

## 6. Lighting Setup

Two lights, deliberately, not more:
1. **A single, very dim, cool-blue directional "ambient starlight"** — just enough to give the
   camera rig housing (4.3) a readable silhouette and a faint specular highlight, so it doesn't
   read as a flat black cutout against the void.
2. **The beacon itself** (Section 3) — the only light source that meaningfully illuminates
   anything at proximity, because in the real scenario, the beacon genuinely is the dominant local
   light source. This is the same discipline as everywhere else in this document: light the scene
   the way the actual physics would, don't add lights because a dark scene "needs more."

No fill light, no rim light, no three-point studio setup — those are conventions for making an
object look good from a fixed hero angle. This scene's camera moves continuously (it's being
actively tracked); a studio lighting rig would visibly fail to make sense from most of those
angles and would call attention to itself as artificial.

---

## 7. Post-Processing Stack (URP Volume Profile)

| Effect | Setting philosophy | Purpose |
|---|---|---|
| Bloom | Threshold tuned so ONLY the beacon and, faintly, the brightest near-field stars trigger it | This is what makes the beacon read as a genuine light source rather than a lit shape — see 3.2 |
| Volumetric light (community package, Section header) | Very subtle, only visible as a faint shaft when the beacon is near the frustum cone's edge | Confirms visually that the frustum is a real spatial volume, not a flat cone billboard — used sparingly, this is expensive to overuse |
| Color grading | Minimal — a slight cool lift matching `--void`/`--field` tokens, nothing stylized | Consistency with the website's palette (Section 4.1 of THE LOCK-ON doc), not a separate "look" |
| Vignette | Very light, only in the external view, never the sensor inset | The inset must stay an honest, undistorted sensor image — a vignette there would misrepresent the detector's actual input |
| Chromatic aberration, film grain, lens flare presets | Not used | These are cinematic-generic defaults with no justification here — exactly the kind of unjustified decoration Section 1.2 rules out |

---

## 8. What this document deliberately does not specify

Exact particle counts, exact bloom threshold numbers, exact light intensity values — these need
empirical tuning once the scene exists and should be treated as implementation details to dial in
against the actual build, not numbers to guess correctly on paper. What this document fixes is
the *reasoning* behind each element, so that whoever tunes those numbers later — human or agent —
knows what each one is supposed to be doing and won't "fix" something by breaking its purpose.
