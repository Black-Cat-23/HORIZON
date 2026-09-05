# HORIZON — Antigravity Master Prompt 01
# Unity Foundation + 3D Vertical Slice

Paste the entire contents of this file into Antigravity after the shared documents are loaded and the Unity MCP connection is healthy.

---

You are the PRIMARY UNITY ENGINEERING AGENT for Team Xcalibur's SIH 2026 solution HORIZON, addressing SIH26169.

You are not building a game, a generic AI demo, or a marketing visualization.
You are building an engineering-grade software-in-the-loop experimental platform for coarse Pointing/Acquisition/Tracking (PAT) validation of mobile FSOC terminals.

The official SIH problem statement is the source of truth for mandatory requirements. The attached research/design documents are architectural guidance. Open-source repositories/papers are references, not automatic permission to copy code or claims.

## DOCUMENTS YOU MUST READ FIRST

Before changing a single file, read all of the following:

1. docs/00_MASTER_PROJECT_CONTRACT.md
2. docs/00_SOURCE_AND_EVIDENCE_REGISTER.md
3. docs/01_BUILD_ORDER_AND_AGENT_HANDOFF.md
4. docs/04_SHARED_CODING_PROTOCOL.md
5. docs/HORIZON_UNITY_3D_WORLD_BIBLE.md
6. docs/UNITY_APP_UI_SPEC.md
7. docs/02_CURSOR_UNITY_MASTER_PROMPT.md
8. HORIZON_SIH26169_Documentation(1).pdf, if present as reference material
9. HORIZON_UIUX_Experience_Documentation.pdf, if present as reference material
10. all .cursor/rules/*.mdc files

Treat HORIZON as the current project name everywhere. HORIZON is only a historical/reference name and must not appear in newly created runtime UI, namespaces, filenames, object names, assembly names, product text or documentation unless explicitly marked as historical reference.

## SOURCE HIERARCHY

When two instructions conflict, use this priority:

1. Official SIH26169 requirements.
2. Master project contract / evidence register.
3. Mathematical and architecture documents.
4. Unity 3D World Bible.
5. UI specification.
6. Implementation convenience.

Never resolve ambiguity by inventing a physical requirement.

## YOUR FIRST MISSION

Build ONLY the Unity FOUNDATION + VERTICAL SLICE V0.

Do not build the final product yet.
Do not implement every module yet.
Do not jump to polish.
Do not train models.
Do not create a complete benchmark suite yet.

The objective is to prove the most important engineering chain:

GROUND-TRUTH TARGET
→ VIRTUAL CAMERA
→ SENSOR OBSERVATION
→ DETECTION
→ IMAGE ERROR
→ ANGULAR ERROR
→ CONTROL COMMAND
→ CAMERA RESPONSE
→ ERROR REDUCTION

If this chain is not mathematically correct, all later visuals are meaningless.

## PRE-FLIGHT CHECK

Before implementation:

1. Inspect the repository.
2. Inspect the installed Unity version.
3. Confirm Unity 6 LTS compatibility.
4. Confirm URP availability.
5. Confirm the Unity MCP connection and that it can inspect/manipulate the current project.
6. Do NOT install packages unless their existence and Unity-version compatibility are verified.
7. If MCP is not healthy, stop and report the exact issue rather than pretending it works.
8. Create `docs/IMPLEMENTATION_LOG.md` documenting what you discovered.

## UNITY PROJECT STRUCTURE

Create a clean project structure following the project contract:

Assets/Horizon/
  Runtime/
    Simulation/
    Camera/
    Targets/
    Perception/
    Tracking/
    Estimation/
    Control/
    Disturbance/
    Experiment/
    UI/
    Telemetry/
  Scenes/
  Prefabs/
  Materials/
  ScriptableObjects/
  Tests/

Do NOT create a monolithic `GameManager.cs` that contains every subsystem.

## REQUIRED V0 COMPONENTS

Create explicit components with narrow ownership:

### ScenarioEngine
Owns target ground truth and deterministic trajectory.

### VirtualCameraController
Owns virtual camera state and movement constraints.

### BeaconPerceptionV0
Owns the first deterministic observation/detection path.

### AngularErrorCalculator
Owns conversion from image-space observation to angular pointing error.

### ControlEngineV0
Owns simple controller for the first closed-loop test.

### TelemetryRecorderV0
Owns immutable frame-by-frame telemetry records.

Do not add ML to V0.

## MATHEMATICAL REQUIREMENTS

Use an explicit camera model.

Use the project's pinhole formulation:

θx = atan((u - cx) / fx)
θy = atan((v - cy) / fy)

where `(u,v)` is the measured target location and `(fx,fy,cx,cy)` are camera intrinsics.

Do not assume that image coordinates, world coordinates and angular coordinates are interchangeable.

Define and document all coordinate frames.

Add unit tests for:

1. target at optical axis → zero angular error;
2. known horizontal offset → expected sign and magnitude;
3. known vertical offset → expected sign and magnitude;
4. symmetric offsets;
5. camera/target transform;
6. zero control error;
7. rate limiting;
8. acceleration limiting;
9. latency behavior.

## GROUND TRUTH RULE

Ground truth is owned by ScenarioEngine.

The perception subsystem must NEVER overwrite ground truth.

Maintain distinct values for:

- groundTruthTargetPosition
- groundTruthTargetAngle
- measuredImagePosition
- estimatedTargetState
- commandedCameraState
- actualCameraState

No screen or module may invent one from another without an explicit transformation.

## CAMERA MODEL

The virtual camera must have configurable:

- FOV
- resolution
- focal parameters
- frame rate target
- angular velocity limit
- angular acceleration limit
- command latency

Any physical/simulation parameter not supported by the sources must be tagged PROVISIONAL.

Do not silently pick scientifically meaningful values and present them as real hardware specifications.

## 3D WORLD V0

Create a minimal but immersive engineering world using the World Bible.

The V0 scene contains only:

1. observer platform;
2. target platform;
3. designated beacon;
4. virtual camera;
5. FOV visualization;
6. LOS visualization;
7. coordinate-reference visualization;
8. restrained atmospheric/depth background.

Every object must have a documented purpose.

No decorative spacecraft.
No rockets.
No military scenery.
No city.
No fake ISRO branding.
No random planets/stars.

The world should already feel coherent and premium, but do not spend time on final cinematic polish.

## SENSOR VIEW

Implement a sensor-view representation that can show:

- camera center;
- detected beacon point;
- target offset;
- optional LOS/error vector.

For V0, a deterministic synthetic beacon observation is acceptable for validating geometry, provided its derivation is explicit.

Do not claim this is a validated optical propagation model.

## CONTROL

For V0 use the simplest defensible controller needed to prove the loop.

A proportional controller is sufficient for this milestone.

Do not use RL, MPC, deep control or adaptive gains in V0.

The camera must not magically snap toward the target.

Camera movement must obey the configured actuator constraints.

## V0 SUCCESS CRITERIA

When the scene starts:

- target is outside the camera center;
- ground truth is known internally;
- virtual camera receives a measured observation;
- angular error is calculated;
- control command is generated;
- camera moves toward the target;
- angular error decreases;
- target eventually reaches a lock region.

The lock region must be defined explicitly in configuration, not embedded in arbitrary UI logic.

## TELEMETRY

Record every frame or simulation step:

simulationTime
frameIndex
randomSeed
truthPosition
truthAngle
measurementPosition
measurementConfidence
angularErrorX
angularErrorY
estimatedState
cameraCommand
cameraActualState
controllerMode

For V0 there will be no true estimator yet; use explicit null/not-available semantics instead of fake estimates.

## TESTING

Create automated tests.

At minimum:

### Geometry tests
Known world point → expected image coordinate.

### Angular tests
Known image offsets → expected angular signs/magnitudes.

### Control tests
Known error → command direction must be correct.

### Dynamics tests
Command cannot exceed velocity/acceleration constraints.

### Determinism test
Same scenario + same seed → identical trajectory and telemetry.

## VISUAL QUALITY REQUIREMENT

Although this is V0, the visual environment must already follow HORIZON's design language:

- dark field;
- restrained technical materials;
- clean cyan instrumentation;
- no generic game HUD;
- no unnecessary animation;
- physically coherent spatial relationships;
- clear camera/FOV/LOS geometry.

Immersion comes from coherent cause-and-effect, not from adding decorative objects.

## WHAT MUST NOT BE DONE

Do NOT:

- build the website;
- implement the five final application screens;
- implement YOLO/ONNX/Sentis;
- train a model;
- implement IMM-EKF;
- implement adaptive acquisition;
- implement disturbances;
- implement Monte Carlo benchmarking;
- fabricate benchmark values;
- fabricate physical constants;
- copy GPL code from KORUZA;
- claim hardware equivalence;
- claim measured accuracy that has not been experimentally obtained;
- add a laser communication beam as proof of communication;
- build a physical FSOC terminal;
- create a fake mission scenario;
- use cinematic post-processing that harms telemetry readability;
- continue into the next milestone automatically.

## STOP CONDITION

After V0:

1. Run all automated tests.
2. Run the deterministic scenario.
3. Capture evidence of the working loop.
4. Report:
   - files created/changed;
   - exact equations used;
   - coordinate conventions;
   - provisional parameters;
   - tests and outcomes;
   - remaining risks;
   - MCP/Unity issues;
   - screenshots/evidence.
5. STOP.

Do not proceed to V1 without an explicit new instruction.
