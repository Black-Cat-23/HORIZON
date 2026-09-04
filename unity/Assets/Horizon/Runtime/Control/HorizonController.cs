using System;
using UnityEngine;

namespace Horizon.Control
{
    public enum ControllerAlgorithm
    {
        B0_NaiveProportional,
        B1_ClassicalPID,
        B2_NeuralPID,
        Ours_AdaptiveFeedback
    }

    /// <summary>
    /// Precision closed-loop gimbal controller. Translates estimated angular errors
    /// and kinematics into actuator velocity commands (deg/s).
    /// </summary>
    public class HorizonController : MonoBehaviour
    {
        public ControllerAlgorithm Algorithm = ControllerAlgorithm.Ours_AdaptiveFeedback;

        [Header("PID Gains")]
        public float Kp = 3.2f;
        public float Ki = 0.4f;
        public float Kd = 0.85f;
        public float IntegratorWindupLimit = 15.0f;

        [Header("Adaptive Servo Gains")]
        public float AdaptiveVelocityDamping = 1.15f;
        public float FeedForwardGain = 0.95f;

        private Vector2 _integratedError = Vector2.zero;
        private Vector2 _previousError = Vector2.zero;

        public void ResetController()
        {
            _integratedError = Vector2.zero;
            _previousError = Vector2.zero;
        }

        /// <summary>
        /// Generates commanded gimbal rates [rateAzimuthDeg, rateElevationDeg] from estimated state.
        /// </summary>
        public Vector2 ComputeRateCommand(Horizon.Estimation.KinematicState estState, float dt)
        {
            if (dt <= 0.0001f) return Vector2.zero;

            Vector2 error = new Vector2(estState.ThetaX, estState.ThetaY);

            switch (Algorithm)
            {
                case ControllerAlgorithm.B0_NaiveProportional:
                    // Simple P-controller with fixed gain
                    return error * 2.0f;

                case ControllerAlgorithm.B1_ClassicalPID:
                case ControllerAlgorithm.B2_NeuralPID:
                    // Full PID with integrator clamping
                    _integratedError += error * dt;
                    _integratedError.x = Mathf.Clamp(_integratedError.x, -IntegratorWindupLimit, IntegratorWindupLimit);
                    _integratedError.y = Mathf.Clamp(_integratedError.y, -IntegratorWindupLimit, IntegratorWindupLimit);

                    Vector2 dError = (error - _previousError) / dt;
                    _previousError = error;

                    return (error * Kp) + (_integratedError * Ki) + (dError * Kd);

                case ControllerAlgorithm.Ours_AdaptiveFeedback:
                default:
                    // Adaptive state feedback with velocity feed-forward
                    _integratedError += error * dt;
                    _integratedError.x = Mathf.Clamp(_integratedError.x, -IntegratorWindupLimit, IntegratorWindupLimit);
                    _integratedError.y = Mathf.Clamp(_integratedError.y, -IntegratorWindupLimit, IntegratorWindupLimit);

                    Vector2 rateCmd = (error * Kp) + (_integratedError * Ki);

                    // Compensate for target apparent angular velocity
                    Vector2 targetVelocity = new Vector2(estState.OmegaX, estState.OmegaY);
                    rateCmd += targetVelocity * FeedForwardGain;

                    // Smooth high-frequency jitter
                    rateCmd -= new Vector2(estState.OmegaX, estState.OmegaY) * (AdaptiveVelocityDamping * 0.2f);

                    _previousError = error;
                    return rateCmd;
            }
        }
    }

    /// <summary>
    /// Confidence-aware 5-state tracking Mode Manager.
    /// States: SEARCH -> ACQUIRE -> TRACK -> DEGRADED -> REACQUIRE.
    /// </summary>
    public class ModeManager : MonoBehaviour
    {
        public TrackMode CurrentMode = TrackMode.Search;

        [Header("Thresholds (deg)")]
        public float LockAcquisitionThresholdDeg = 1.8f;
        public float LockLossThresholdDeg = 6.0f;
        public float FineTrackThresholdDeg = 0.6f;

        [Header("Confidence Thresholds")]
        public float MinTrackConfidence = 0.45f;
        public float DegradedConfidenceThreshold = 0.25f;

        [Header("Search Scan Parameters")]
        public float SpiralScanRadiusDeg = 15.0f;
        public float SpiralScanSpeedDegPerSec = 8.0f;

        private float _searchTimer = 0.0f;

        public event Action<TrackMode, TrackMode> OnModeChanged;

        public void ResetMode()
        {
            TrackMode prev = CurrentMode;
            CurrentMode = TrackMode.Search;
            _searchTimer = 0.0f;
            if (prev != CurrentMode) OnModeChanged?.Invoke(prev, CurrentMode);
        }

        public void UpdateMode(bool isDetected, float angularErrorDeg, float confidence, float disturbanceLevel)
        {
            TrackMode previous = CurrentMode;

            switch (CurrentMode)
            {
                case TrackMode.Search:
                    if (isDetected && confidence >= DegradedConfidenceThreshold)
                    {
                        CurrentMode = angularErrorDeg <= LockAcquisitionThresholdDeg ? TrackMode.Track : TrackMode.Acquire;
                    }
                    break;

                case TrackMode.Acquire:
                    if (!isDetected)
                    {
                        CurrentMode = TrackMode.Search;
                    }
                    else if (angularErrorDeg <= LockAcquisitionThresholdDeg && confidence >= MinTrackConfidence)
                    {
                        CurrentMode = TrackMode.Track;
                    }
                    break;

                case TrackMode.Track:
                    if (!isDetected || angularErrorDeg > LockLossThresholdDeg)
                    {
                        CurrentMode = TrackMode.Reacquire;
                    }
                    else if (confidence < DegradedConfidenceThreshold || disturbanceLevel > 0.65f)
                    {
                        CurrentMode = TrackMode.Degraded;
                    }
                    break;

                case TrackMode.Degraded:
                    if (!isDetected || angularErrorDeg > LockLossThresholdDeg)
                    {
                        CurrentMode = TrackMode.Reacquire;
                    }
                    else if (confidence >= MinTrackConfidence && disturbanceLevel <= 0.45f)
                    {
                        CurrentMode = TrackMode.Track;
                    }
                    break;

                case TrackMode.Reacquire:
                    if (isDetected && angularErrorDeg <= LockAcquisitionThresholdDeg)
                    {
                        CurrentMode = TrackMode.Track;
                    }
                    else if (!isDetected && _searchTimer > 5.0f)
                    {
                        // Fall back to wide search
                        CurrentMode = TrackMode.Search;
                        _searchTimer = 0.0f;
                    }
                    break;
            }

            if (previous != CurrentMode)
            {
                _searchTimer = 0.0f;
                OnModeChanged?.Invoke(previous, CurrentMode);
            }
        }

        /// <summary>
        /// Generates an Archimedean spiral search trajectory for acquisition/reacquisition.
        /// </summary>
        public Vector2 GenerateSearchScanVelocity(float dt)
        {
            _searchTimer += dt;
            float t = _searchTimer;
            float r = Mathf.Min(SpiralScanRadiusDeg, 0.8f * t * SpiralScanSpeedDegPerSec * 0.15f);
            float theta = t * 3.5f;

            float scanX = Mathf.Cos(theta) * r;
            float scanY = Mathf.Sin(theta) * r;

            // Velocity tangent
            float vx = (-Mathf.Sin(theta) * 3.5f * r) + (Mathf.Cos(theta) * 0.8f);
            float vy = (Mathf.Cos(theta) * 3.5f * r) + (Mathf.Sin(theta) * 0.8f);

            return new Vector2(vx, vy);
        }
    }
}
