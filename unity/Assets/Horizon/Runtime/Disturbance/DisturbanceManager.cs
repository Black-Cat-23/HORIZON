using System;
using UnityEngine;

namespace Horizon.Disturbance
{
    public enum DisturbancePreset
    {
        Nominal,
        Difficult,
        Severe,
        Recovery,
        Adversarial,
        Custom
    }

    /// <summary>
    /// Disturbance injection engine. Injects platform vibration, sensor noise,
    /// scintillation, temporal occlusion, and false distractors into the PAT loop.
    /// </summary>
    public class DisturbanceManager : MonoBehaviour
    {
        public DisturbancePreset ActivePreset = DisturbancePreset.Nominal;

        [Range(0f, 1f)] public float PlatformVibration = 0.0f;
        [Range(0f, 1f)] public float SensorNoise = 0.04f;
        [Range(0f, 1f)] public float MotionBlur = 0.0f;
        [Range(0f, 1f)] public float SignalScintillation = 0.0f;
        [Range(0f, 1f)] public float OcclusionDuration = 0.0f;
        [Range(0f, 1f)] public float Distractors = 0.0f;
        [Range(0f, 1f)] public float ActuatorLatency = 0.0f;

        [Header("Outputs")]
        public Vector2 VibrationAngularJitterDeg;
        public float EffectiveSensorNoise;
        public float ScintillationAttenuation;
        public bool IsTemporarilyOccluded;

        private float _simTime = 0.0f;

        public void ApplyPreset(DisturbancePreset preset)
        {
            ActivePreset = preset;
            switch (preset)
            {
                case DisturbancePreset.Nominal:
                    PlatformVibration = 0.0f;
                    SensorNoise = 0.04f;
                    MotionBlur = 0.0f;
                    SignalScintillation = 0.0f;
                    OcclusionDuration = 0.0f;
                    Distractors = 0.0f;
                    ActuatorLatency = 0.0f;
                    break;

                case DisturbancePreset.Difficult:
                    PlatformVibration = 0.25f;
                    SensorNoise = 0.18f;
                    MotionBlur = 0.20f;
                    SignalScintillation = 0.15f;
                    OcclusionDuration = 0.10f;
                    Distractors = 0.15f;
                    ActuatorLatency = 0.08f;
                    break;

                case DisturbancePreset.Severe:
                    PlatformVibration = 0.55f;
                    SensorNoise = 0.40f;
                    MotionBlur = 0.45f;
                    SignalScintillation = 0.35f;
                    OcclusionDuration = 0.30f;
                    Distractors = 0.35f;
                    ActuatorLatency = 0.22f;
                    break;

                case DisturbancePreset.Recovery:
                    PlatformVibration = 0.35f;
                    SensorNoise = 0.22f;
                    MotionBlur = 0.15f;
                    SignalScintillation = 0.20f;
                    OcclusionDuration = 0.45f;
                    Distractors = 0.10f;
                    ActuatorLatency = 0.12f;
                    break;

                case DisturbancePreset.Adversarial:
                    PlatformVibration = 0.70f;
                    SensorNoise = 0.55f;
                    MotionBlur = 0.60f;
                    SignalScintillation = 0.50f;
                    OcclusionDuration = 0.55f;
                    Distractors = 0.70f;
                    ActuatorLatency = 0.40f;
                    break;
            }
        }

        public void UpdateDisturbances(float dt)
        {
            _simTime += dt;

            // 1. Platform vibration: multi-frequency sinusoidal harmonic jitter
            float vibA = Mathf.Sin(_simTime * 45.0f) * 0.15f;
            float vibB = Mathf.Sin(_simTime * 18.0f) * 0.25f;
            float vibC = Mathf.Cos(_simTime * 85.0f) * 0.08f;
            float totalVib = (vibA + vibB + vibC) * PlatformVibration;
            VibrationAngularJitterDeg = new Vector2(totalVib, totalVib * 0.7f);

            // 2. Sensor noise
            EffectiveSensorNoise = SensorNoise + (MotionBlur * 0.5f);

            // 3. Scintillation attenuation
            float scintWave = (Mathf.Sin(_simTime * 8.0f) * 0.5f) + 0.5f;
            ScintillationAttenuation = scintWave * SignalScintillation * 0.85f;

            // 4. Temporal occlusion: periodic optical dropout window
            if (OcclusionDuration > 0.05f)
            {
                float period = 4.0f;
                float cycle = _simTime % period;
                float cutoff = OcclusionDuration * 1.8f;
                IsTemporarilyOccluded = cycle < cutoff;
            }
            else
            {
                IsTemporarilyOccluded = false;
            }
        }

        public float TotalSeverity()
        {
            return PlatformVibration + SensorNoise + MotionBlur + SignalScintillation + OcclusionDuration + Distractors + ActuatorLatency;
        }
    }
}
