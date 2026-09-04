using System;
using UnityEngine;
using Horizon.Simulation;
using Horizon.Perception;
using Horizon.Estimation;
using Horizon.Control;
using Horizon.Disturbance;
using Horizon.Visual;
using Horizon.Environment;
using Horizon.Telemetry;

namespace Horizon
{
    public enum ActiveViewMode
    {
        ObserverView,
        SensorView,
        DiagnosticView
    }

    /// <summary>
    /// Master orchestrator for the HORIZON 3D simulation laboratory.
    /// Assembles platforms, materials, shaders, cameras, and closed-loop PAT physics.
    /// </summary>
    public class Horizon3DSceneBootstrapper : MonoBehaviour
    {
        [Header("Scene Configuration")]
        public int SimulationSeed = 42;
        public ActiveViewMode ViewMode = ActiveViewMode.ObserverView;

        [Header("Core Subsystems")]
        public ScenarioEngine ScenarioEngine;
        public VirtualCameraController CameraController;
        public BeaconPerception Perception;
        public HorizonEstimator Estimator;
        public HorizonController Controller;
        public ModeManager ModeManager;
        public DisturbanceManager DisturbanceManager;
        public TelemetryRecorder Telemetry;

        [Header("Visualization Subsystems")]
        public FrustumMeshGenerator FrustumGen;
        public LosRenderer LosRenderer;
        public CovarianceVisualizer CovVisualizer;
        public TrajectoryVisualizer TrajVisualizer;
        public HorizonEnvironmentDirector EnvironmentDirector;

        [Header("Cameras")]
        public UnityEngine.Camera ObserverCamera;
        public UnityEngine.Camera SensorCamera;

        private Material _bodyMat;
        private Material _yokeMat;
        private Material _lensMat;
        private Material _emitterMat;
        private Material _glowMat;
        private Material _frustumMat;
        private Material _beamMat;

        private void Awake()
        {
            InitializeMaterials();
            BuildSceneHierarchy();
        }

        private void Start()
        {
            if (ScenarioEngine != null) ScenarioEngine.InitializeScenario(SimulationSeed);
            if (Telemetry != null) Telemetry.ResetRecorder(SimulationSeed);
            if (ModeManager != null) ModeManager.ResetMode();

            Telemetry.LogEvent("Simulation initialized — armed in SEARCH mode");
        }

        private void InitializeMaterials()
        {
            Shader urpLitShader = Shader.Find("Universal Render Pipeline/Lit");
            if (urpLitShader == null) urpLitShader = Shader.Find("Standard");
            if (urpLitShader == null) urpLitShader = Shader.Find("Unlit/Color");

            Shader urpUnlitShader = Shader.Find("Universal Render Pipeline/Unlit");
            if (urpUnlitShader == null) urpUnlitShader = Shader.Find("Sprites/Default");

            _bodyMat = new Material(urpLitShader);
            _bodyMat.name = "Mat_AerospaceTitanium";
            SetMaterialColorAndProperties(_bodyMat, new Color(0.12f, 0.15f, 0.22f), 0.85f, 0.75f);

            _yokeMat = new Material(urpLitShader);
            _yokeMat.name = "Mat_AerospaceGraphite";
            SetMaterialColorAndProperties(_yokeMat, new Color(0.08f, 0.10f, 0.15f), 0.90f, 0.80f);

            _lensMat = new Material(urpLitShader);
            _lensMat.name = "Mat_CoatedObjectiveLens";
            SetMaterialColorAndProperties(_lensMat, new Color(0.1f, 0.45f, 0.55f, 0.85f), 0.95f, 0.95f);

            _emitterMat = new Material(urpLitShader);
            _emitterMat.name = "Mat_BeaconEmitterPod";
            SetMaterialColorAndProperties(_emitterMat, new Color(0.18f, 0.22f, 0.32f), 0.70f, 0.60f);

            // Custom procedural shaders
            Shader glowShader = Shader.Find("Horizon/OpticalBeaconGlow");
            _glowMat = new Material(glowShader != null ? glowShader : urpUnlitShader);

            Shader frustumShader = Shader.Find("Horizon/FrustumVolume");
            _frustumMat = new Material(frustumShader != null ? frustumShader : urpUnlitShader);
            _frustumMat.color = new Color(0.498f, 0.831f, 0.910f, 0.15f); // 15% opacity cyan cone

            Shader beamShader = Shader.Find("Horizon/LaserBoresight");
            _beamMat = new Material(beamShader != null ? beamShader : urpUnlitShader);
            _beamMat.color = new Color(0.498f, 0.831f, 0.910f, 1.0f);
        }

        private void SetMaterialColorAndProperties(Material mat, Color col, float metallic, float smoothness)
        {
            if (mat.HasProperty("_BaseColor")) mat.SetColor("_BaseColor", col);
            if (mat.HasProperty("_Color")) mat.SetColor("_Color", col);
            if (mat.HasProperty("_Metallic")) mat.SetFloat("_Metallic", metallic);
            if (mat.HasProperty("_Smoothness")) mat.SetFloat("_Smoothness", smoothness);
            if (mat.HasProperty("_Glossiness")) mat.SetFloat("_Glossiness", smoothness);
        }

        private void BuildSceneHierarchy()
        {
            // 1. Environment & Lighting
            GameObject envGo = new GameObject("EnvironmentDirector");
            envGo.transform.SetParent(transform, false);
            EnvironmentDirector = envGo.AddComponent<HorizonEnvironmentDirector>();
            EnvironmentDirector.SetupEnvironment();

            // 2. Observer Platform with Gimbal
            GameObject observerPlatform = new GameObject("ObserverPlatform");
            observerPlatform.transform.SetParent(transform, false);
            observerPlatform.transform.position = Vector3.zero;

            CameraController = ProceduralGimbalBuilder.BuildGimbal(observerPlatform, _bodyMat, _yokeMat, _lensMat, _bodyMat);

            // 3. Target Platform with Beacon
            GameObject targetPlatform = new GameObject("TargetPlatform");
            targetPlatform.transform.SetParent(transform, false);
            targetPlatform.transform.position = new Vector3(8.0f, 1.5f, 50.0f);

            OpticalBeacon beacon = ProceduralTargetPlatformBuilder.BuildTargetPlatform(targetPlatform, _bodyMat, _yokeMat, _emitterMat, _glowMat);

            // 4. Scenario Engine
            GameObject simGo = new GameObject("ScenarioEngine");
            simGo.transform.SetParent(transform, false);
            ScenarioEngine = simGo.AddComponent<ScenarioEngine>();
            ScenarioEngine.TargetPlatform = targetPlatform.transform;

            // 5. Perception
            GameObject percGo = new GameObject("BeaconPerception");
            percGo.transform.SetParent(transform, false);
            Perception = percGo.AddComponent<BeaconPerception>();
            Perception.CameraController = CameraController;
            Perception.TargetBeacon = beacon;

            // 6. Estimator
            GameObject estGo = new GameObject("HorizonEstimator");
            estGo.transform.SetParent(transform, false);
            Estimator = estGo.AddComponent<HorizonEstimator>();

            // 7. Controller & Mode Manager
            GameObject ctrlGo = new GameObject("HorizonController");
            ctrlGo.transform.SetParent(transform, false);
            Controller = ctrlGo.AddComponent<HorizonController>();

            GameObject modeGo = new GameObject("ModeManager");
            modeGo.transform.SetParent(transform, false);
            ModeManager = modeGo.AddComponent<ModeManager>();

            // 8. Disturbance Engine
            GameObject distGo = new GameObject("DisturbanceManager");
            distGo.transform.SetParent(transform, false);
            DisturbanceManager = distGo.AddComponent<DisturbanceManager>();

            // 9. Telemetry Logger
            GameObject telemGo = new GameObject("TelemetryRecorder");
            telemGo.transform.SetParent(transform, false);
            Telemetry = telemGo.AddComponent<TelemetryRecorder>();

            // 10. Visualization Assets
            // FOV Frustum
            GameObject frustumGo = new GameObject("FOV_FrustumVolume");
            frustumGo.transform.SetParent(CameraController.OpticalAperture, false);
            FrustumGen = frustumGo.AddComponent<FrustumMeshGenerator>();
            FrustumGen.CameraController = CameraController;
            MeshRenderer frustumMr = frustumGo.GetComponent<MeshRenderer>();
            frustumMr.sharedMaterial = _frustumMat;

            // Line of Sight
            GameObject losGo = new GameObject("Optical_LineOfSight");
            losGo.transform.SetParent(transform, false);
            LineRenderer losLine = losGo.AddComponent<LineRenderer>();
            losLine.sharedMaterial = _beamMat;
            LosRenderer = losGo.AddComponent<LosRenderer>();
            LosRenderer.CameraAperture = CameraController.OpticalAperture;
            LosRenderer.TargetBeacon = targetPlatform.transform;
            LosRenderer.ModeManager = ModeManager;

            // Covariance Uncertainty Ellipse
            GameObject covGo = new GameObject("CovarianceUncertainty");
            covGo.transform.SetParent(transform, false);
            LineRenderer covLine = covGo.AddComponent<LineRenderer>();
            covLine.sharedMaterial = new Material(Shader.Find("Sprites/Default"));
            CovVisualizer = covGo.AddComponent<CovarianceVisualizer>();
            CovVisualizer.Estimator = Estimator;
            CovVisualizer.TargetPlatform = targetPlatform.transform;

            // Trajectory Visualizer
            GameObject trajGo = new GameObject("TrajectoryVisualizer");
            trajGo.transform.SetParent(transform, false);
            TrajVisualizer = trajGo.AddComponent<TrajectoryVisualizer>();

            GameObject actualTrail = new GameObject("Trail_Actual");
            actualTrail.transform.SetParent(trajGo.transform, false);
            TrajVisualizer.ActualTrailRenderer = actualTrail.AddComponent<LineRenderer>();
            TrajVisualizer.ActualTrailRenderer.sharedMaterial = new Material(Shader.Find("Sprites/Default"));

            GameObject predTrail = new GameObject("Trail_Predicted");
            predTrail.transform.SetParent(trajGo.transform, false);
            TrajVisualizer.PredictedTrailRenderer = predTrail.AddComponent<LineRenderer>();
            TrajVisualizer.PredictedTrailRenderer.sharedMaterial = new Material(Shader.Find("Sprites/Default"));

            // 11. Multi-Camera Rig
            SetupCameras();
        }

        private void SetupCameras()
        {
            // Observer Camera (Tactical 3D view)
            GameObject obsCamGo = new GameObject("ObserverCamera");
            obsCamGo.transform.SetParent(transform, false);
            obsCamGo.transform.position = new Vector3(-3.5f, 2.8f, -6.5f);
            obsCamGo.transform.LookAt(new Vector3(0.0f, 1.2f, 10.0f));

            ObserverCamera = obsCamGo.AddComponent<UnityEngine.Camera>();
            ObserverCamera.tag = "MainCamera";
            ObserverCamera.clearFlags = CameraClearFlags.SolidColor;
            ObserverCamera.backgroundColor = HorizonTokens.VoidColor;
            ObserverCamera.fieldOfView = 50.0f;

            // Sensor Camera (Attached to optical telescope aperture)
            GameObject sensorCamGo = new GameObject("SensorCamera");
            sensorCamGo.transform.SetParent(CameraController.OpticalAperture, false);
            sensorCamGo.transform.localPosition = Vector3.zero;
            sensorCamGo.transform.localRotation = Quaternion.identity;

            SensorCamera = sensorCamGo.AddComponent<UnityEngine.Camera>();
            SensorCamera.clearFlags = CameraClearFlags.SolidColor;
            SensorCamera.backgroundColor = HorizonTokens.VoidColor;
            SensorCamera.fieldOfView = CameraController.Intrinsics.HorizontalFovDeg;

            UpdateCameraViewports();
        }

        public void SetViewMode(ActiveViewMode mode)
        {
            ViewMode = mode;
            UpdateCameraViewports();
        }

        private void UpdateCameraViewports()
        {
            if (ObserverCamera == null || SensorCamera == null) return;

            switch (ViewMode)
            {
                case ActiveViewMode.ObserverView:
                    ObserverCamera.rect = new Rect(0, 0, 1, 1);
                    ObserverCamera.depth = 1;
                    SensorCamera.rect = new Rect(0.72f, 0.70f, 0.26f, 0.26f); // Picture-in-picture sensor view
                    SensorCamera.depth = 2;
                    break;

                case ActiveViewMode.SensorView:
                    SensorCamera.rect = new Rect(0, 0, 1, 1);
                    SensorCamera.depth = 1;
                    ObserverCamera.rect = new Rect(0.72f, 0.70f, 0.26f, 0.26f);
                    ObserverCamera.depth = 2;
                    break;

                case ActiveViewMode.DiagnosticView:
                    ObserverCamera.rect = new Rect(0, 0, 0.5f, 1);
                    ObserverCamera.depth = 1;
                    SensorCamera.rect = new Rect(0.5f, 0, 0.5f, 1);
                    SensorCamera.depth = 1;
                    break;
            }
        }

        private void Update()
        {
            // View Mode hotkeys: 1 for Observer, 2 for Sensor, 3 for Diagnostic
            if (Input.GetKeyDown(KeyCode.Alpha1)) SetViewMode(ActiveViewMode.ObserverView);
            if (Input.GetKeyDown(KeyCode.Alpha2)) SetViewMode(ActiveViewMode.SensorView);
            if (Input.GetKeyDown(KeyCode.Alpha3)) SetViewMode(ActiveViewMode.DiagnosticView);

            float dt = Time.deltaTime;
            if (dt <= 0.0001f) return;

            // 1. Step Scenario Engine (Target ground truth)
            ScenarioEngine.StepSimulation(dt);

            // 2. Step Disturbance Engine
            DisturbanceManager.UpdateDisturbances(dt);

            // 3. Sensor Perception Step
            PerceptionObservation obs = Perception.ProcessSensorFrame(
                DisturbanceManager.EffectiveSensorNoise,
                DisturbanceManager.ScintillationAttenuation,
                DisturbanceManager.IsTemporarilyOccluded
            );

            // 4. Estimation Step (Kalman Predict & Update)
            Estimator.Predict(dt);
            if (obs.IsDetected)
            {
                Estimator.UpdateMeasurement(obs.AngularErrorDeg, obs.Confidence, DisturbanceManager.EffectiveSensorNoise);
            }

            // 5. Mode Manager Update
            float currentErrorNorm = Mathf.Sqrt((Estimator.State.ThetaX * Estimator.State.ThetaX) + (Estimator.State.ThetaY * Estimator.State.ThetaY));
            ModeManager.UpdateMode(obs.IsDetected, currentErrorNorm, Estimator.OverallConfidence, DisturbanceManager.TotalSeverity());

            // 6. Control Step
            Vector2 commandedRate;
            if (ModeManager.CurrentMode == TrackMode.Search || ModeManager.CurrentMode == TrackMode.Reacquire)
            {
                // Execute active spiral search scan
                commandedRate = ModeManager.GenerateSearchScanVelocity(dt);
            }
            else
            {
                // Closed-loop tracking rate command
                commandedRate = Controller.ComputeRateCommand(Estimator.State, dt);
            }

            // Add mechanical platform vibration to actuator command
            commandedRate += DisturbanceManager.VibrationAngularJitterDeg;

            // 7. Actuator Kinematics Update
            CameraController.ApplyRateCommand(commandedRate, dt, ScenarioEngine.SimulationTime);

            // 8. Update Trajectory Trails
            Vector3 targetPos = ScenarioEngine.GroundTruthPosition;
            Vector3 predictedPos = targetPos + (ScenarioEngine.GroundTruthVelocity * 0.15f);
            TrajVisualizer.AddTrajectoryStep(targetPos, predictedPos);

            // 9. Telemetry Recording
            TelemetryRecord record = new TelemetryRecord
            {
                SimTime = ScenarioEngine.SimulationTime,
                RandomSeed = SimulationSeed,
                TruthPosition = targetPos,
                TruthAnglesDeg = obs.AngularErrorDeg,
                IsMeasured = obs.IsDetected,
                MeasuredPixel = obs.PixelCoordinates,
                MeasuredAnglesDeg = obs.AngularErrorDeg,
                MeasuredConfidence = obs.Confidence,
                AngularErrorDeg = currentErrorNorm,
                EstimatedState = Estimator.State,
                Covariance = Estimator.Covariance,
                CommandedRatesDegPerSec = commandedRate,
                ActualGimbalAnglesDeg = new Vector2(CameraController.CurrentAzimuthDeg, CameraController.CurrentElevationDeg),
                Mode = ModeManager.CurrentMode,
                LatencyMs = CameraController.Actuator.LatencySeconds * 1000.0f,
                Fps = 1.0f / dt
            };
            Telemetry.RecordFrame(record);
        }
    }
}
