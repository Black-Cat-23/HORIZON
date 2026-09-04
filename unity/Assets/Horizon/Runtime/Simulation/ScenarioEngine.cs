using System;
using UnityEngine;

namespace Horizon.Simulation
{
    public enum TrajectoryProfile
    {
        LinearFlyby,
        SinusoidalWeave,
        HighDynamicManeuver,
        CircularOrbit
    }

    /// <summary>
    /// Owns ground-truth target motion, position, velocity, and acceleration.
    /// Ground truth is immutable and cannot be modified by the perception/tracking pipeline.
    /// </summary>
    public class ScenarioEngine : MonoBehaviour
    {
        [Header("Target Ground Truth")]
        public Transform TargetPlatform;
        public TrajectoryProfile Profile = TrajectoryProfile.SinusoidalWeave;

        [Header("Trajectory Parameters")]
        public float BaseSpeedMetersPerSec = 15.0f;
        public float BaseDistanceMeters = 50.0f;
        public float WeaveAmplitudeMeters = 8.0f;
        public float WeaveFrequencyHz = 0.25f;
        public float InitialAngularOffsetDeg = 8.0f;

        [Header("Deterministic Seed")]
        public int RandomSeed = 42;

        [Header("Runtime State")]
        [SerializeField] private Vector3 _groundTruthPosition;
        [SerializeField] private Vector3 _groundTruthVelocity;
        [SerializeField] private Vector3 _groundTruthAcceleration;
        [SerializeField] private float _simTime = 0.0f;

        public Vector3 GroundTruthPosition => _groundTruthPosition;
        public Vector3 GroundTruthVelocity => _groundTruthVelocity;
        public Vector3 GroundTruthAcceleration => _groundTruthAcceleration;
        public float SimulationTime => _simTime;

        private Vector3 _initialOrigin;
        private System.Random _prng;

        public void InitializeScenario(int seed)
        {
            RandomSeed = seed;
            _prng = new System.Random(seed);
            _simTime = 0.0f;

            // Offset initial target position based on requested angular offset
            float angleRad = InitialAngularOffsetDeg * Mathf.Deg2Rad;
            float offsetX = Mathf.Sin(angleRad) * BaseDistanceMeters;
            float offsetZ = Mathf.Cos(angleRad) * BaseDistanceMeters;
            _initialOrigin = new Vector3(offsetX, 1.5f, offsetZ);

            _groundTruthPosition = _initialOrigin;
            _groundTruthVelocity = Vector3.zero;
            _groundTruthAcceleration = Vector3.zero;

            if (TargetPlatform != null)
            {
                TargetPlatform.position = _groundTruthPosition;
            }
        }

        private void Start()
        {
            InitializeScenario(RandomSeed);
        }

        public void StepSimulation(float dt)
        {
            _simTime += dt;
            Vector3 prevPos = _groundTruthPosition;
            Vector3 prevVel = _groundTruthVelocity;

            switch (Profile)
            {
                case TrajectoryProfile.LinearFlyby:
                    _groundTruthPosition = _initialOrigin + new Vector3(
                        -_simTime * BaseSpeedMetersPerSec * 0.4f,
                        0.0f,
                        _simTime * BaseSpeedMetersPerSec * 0.1f
                    );
                    break;

                case TrajectoryProfile.SinusoidalWeave:
                    float phase = _simTime * WeaveFrequencyHz * 2.0f * Mathf.PI;
                    _groundTruthPosition = _initialOrigin + new Vector3(
                        Mathf.Sin(phase) * WeaveAmplitudeMeters,
                        Mathf.Cos(phase * 0.6f) * (WeaveAmplitudeMeters * 0.35f),
                        Mathf.Sin(phase * 0.3f) * 4.0f
                    );
                    break;

                case TrajectoryProfile.HighDynamicManeuver:
                    float t = _simTime;
                    float jerk = Mathf.Sign(Mathf.Sin(t * 1.5f)) * 4.0f;
                    _groundTruthPosition = _initialOrigin + new Vector3(
                        Mathf.Sin(t * 0.8f) * WeaveAmplitudeMeters * 1.5f + jerk,
                        Mathf.Sin(t * 1.2f) * 4.0f,
                        Mathf.Cos(t * 0.5f) * 6.0f
                    );
                    break;

                case TrajectoryProfile.CircularOrbit:
                    float theta = _simTime * (BaseSpeedMetersPerSec / BaseDistanceMeters);
                    _groundTruthPosition = new Vector3(
                        Mathf.Sin(theta) * BaseDistanceMeters,
                        1.5f + Mathf.Sin(_simTime * 0.5f) * 2.0f,
                        Mathf.Cos(theta) * BaseDistanceMeters
                    );
                    break;
            }

            // Differentiate velocity and acceleration for state vector ground truth
            if (dt > 0.0001f)
            {
                _groundTruthVelocity = (_groundTruthPosition - prevPos) / dt;
                _groundTruthAcceleration = (_groundTruthVelocity - prevVel) / dt;
            }

            if (TargetPlatform != null)
            {
                TargetPlatform.position = _groundTruthPosition;
            }
        }
    }
}
