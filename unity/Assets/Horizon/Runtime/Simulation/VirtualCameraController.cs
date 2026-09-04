using System;
using System.Collections.Generic;
using UnityEngine;

namespace Horizon.Simulation
{
    /// <summary>
    /// Models physical gimbal motor limits including angular velocity saturation,
    /// angular acceleration saturation, and pure transport latency.
    /// Tagged: PROVISIONAL (Engineering reference bounds for fine/coarse PAT gimbals).
    /// </summary>
    [Serializable]
    public class ActuatorDynamics
    {
        [Tooltip("Maximum slew rate in deg/s")]
        public float MaxAngularVelocityDegPerSec = 45.0f;

        [Tooltip("Maximum angular acceleration in deg/s^2")]
        public float MaxAngularAccelDegPerSec2 = 120.0f;

        [Tooltip("Transport delay in seconds (actuator + processing latency)")]
        public float LatencySeconds = 0.04f;

        private struct CommandPacket
        {
            public float Timestamp;
            public Vector2 VelocityCommand; // deg/s
        }

        private readonly Queue<CommandPacket> _commandQueue = new Queue<CommandPacket>();
        private Vector2 _currentVelocity = Vector2.zero;

        public Vector2 CurrentVelocity => _currentVelocity;

        public void Reset()
        {
            _commandQueue.Clear();
            _currentVelocity = Vector2.zero;
        }

        /// <summary>
        /// Applies rate command through the latency queue and physical torque/accel clamps.
        /// Returns the executed delta angle for this timestep.
        /// </summary>
        public Vector2 Update(Vector2 commandedVelocity, float dt, float currentTime)
        {
            if (dt <= 0.0001f) return Vector2.zero;

            // Enqueue command with timestamp
            _commandQueue.Enqueue(new CommandPacket
            {
                Timestamp = currentTime,
                VelocityCommand = commandedVelocity
            });

            // Retrieve command delayed by LatencySeconds
            Vector2 activeCmd = _currentVelocity;
            while (_commandQueue.Count > 0)
            {
                if (currentTime - _commandQueue.Peek().Timestamp >= LatencySeconds)
                {
                    activeCmd = _commandQueue.Dequeue().VelocityCommand;
                }
                else
                {
                    break;
                }
            }

            // Velocity saturation clamp
            float maxVel = MaxAngularVelocityDegPerSec;
            activeCmd.x = Mathf.Clamp(activeCmd.x, -maxVel, maxVel);
            activeCmd.y = Mathf.Clamp(activeCmd.y, -maxVel, maxVel);

            // Acceleration saturation clamp
            float maxDeltaV = MaxAngularAccelDegPerSec2 * dt;
            Vector2 deltaV = activeCmd - _currentVelocity;
            deltaV.x = Mathf.Clamp(deltaV.x, -maxDeltaV, maxDeltaV);
            deltaV.y = Mathf.Clamp(deltaV.y, -maxDeltaV, maxDeltaV);

            _currentVelocity += deltaV;

            // Integrated position delta
            return _currentVelocity * dt;
        }
    }

    /// <summary>
    /// Owns virtual camera state, mechanical gimbal axes (Azimuth/Elevation),
    /// and actuator constraints. Operates in local observer platform frame.
    /// </summary>
    public class VirtualCameraController : MonoBehaviour
    {
        [Header("Optical Intrinsics")]
        public Horizon.Math.CameraIntrinsics Intrinsics = new Horizon.Math.CameraIntrinsics(1920, 1080, 40.0f);

        [Header("Actuator Dynamics")]
        public ActuatorDynamics Actuator = new ActuatorDynamics();

        [Header("Mechanical Limits (deg)")]
        public float MinAzimuthDeg = -170.0f;
        public float MaxAzimuthDeg = 170.0f;
        public float MinElevationDeg = -30.0f;
        public float MaxElevationDeg = 85.0f;

        [Header("Gimbal Transforms")]
        public Transform AzimuthYoke;
        public Transform ElevationCradle;
        public Transform OpticalAperture;

        [Header("State")]
        [SerializeField] private float _currentAzimuthDeg = 0.0f;
        [SerializeField] private float _currentElevationDeg = 0.0f;

        public float CurrentAzimuthDeg => _currentAzimuthDeg;
        public float CurrentElevationDeg => _currentElevationDeg;

        public Vector3 BoresightForward => OpticalAperture != null ? OpticalAperture.forward : transform.forward;
        public Vector3 AperturePosition => OpticalAperture != null ? OpticalAperture.position : transform.position;

        private void Awake()
        {
            if (Intrinsics == null)
            {
                Intrinsics = new Horizon.Math.CameraIntrinsics(1920, 1080, 40.0f);
            }
        }

        /// <summary>
        /// Applies angular rate commands [azimuthRateDeg, elevationRateDeg].
        /// </summary>
        public void ApplyRateCommand(Vector2 rateCommandDegPerSec, float dt, float simTime)
        {
            Vector2 deltaAngle = Actuator.Update(rateCommandDegPerSec, dt, simTime);

            _currentAzimuthDeg = Mathf.Clamp(_currentAzimuthDeg + deltaAngle.x, MinAzimuthDeg, MaxAzimuthDeg);
            _currentElevationDeg = Mathf.Clamp(_currentElevationDeg + deltaAngle.y, MinElevationDeg, MaxElevationDeg);

            UpdateTransforms();
        }

        public void SetGimbalAngles(float azimuthDeg, float elevationDeg)
        {
            _currentAzimuthDeg = Mathf.Clamp(azimuthDeg, MinAzimuthDeg, MaxAzimuthDeg);
            _currentElevationDeg = Mathf.Clamp(elevationDeg, MinElevationDeg, MaxElevationDeg);
            Actuator.Reset();
            UpdateTransforms();
        }

        private void UpdateTransforms()
        {
            if (AzimuthYoke != null)
            {
                AzimuthYoke.localRotation = Quaternion.Euler(0.0f, _currentAzimuthDeg, 0.0f);
            }

            if (ElevationCradle != null)
            {
                ElevationCradle.localRotation = Quaternion.Euler(-_currentElevationDeg, 0.0f, 0.0f);
            }
        }

        /// <summary>
        /// Transforms a world-space point into the optical camera's local reference frame.
        /// </summary>
        public Vector3 WorldToCameraSpace(Vector3 worldPoint)
        {
            Transform camTransform = OpticalAperture != null ? OpticalAperture : transform;
            return camTransform.InverseTransformPoint(worldPoint);
        }
    }
}
