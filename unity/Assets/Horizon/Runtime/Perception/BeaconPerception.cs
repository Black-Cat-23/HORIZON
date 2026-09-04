using System;
using UnityEngine;

namespace Horizon.Perception
{
    /// <summary>
    /// Physical optical beacon source mounted on the mobile target platform.
    /// Tagged: SOURCE_BACKED (standard optical communication laser source models).
    /// </summary>
    public class OpticalBeacon : MonoBehaviour
    {
        [Tooltip("Radiant power in Watts")]
        public float RadiantPowerWatts = 2.5f;

        [Tooltip("Wavelength in nanometers")]
        public float WavelengthNm = 850.0f;

        [Tooltip("Beam full-width divergence angle in mrad")]
        public float DivergenceMrad = 5.0f;

        [Tooltip("Active modulation frequency in kHz (for beacon identification)")]
        public float ModulationFreqKhz = 10.0f;

        public Vector3 EmissionPoint => transform.position;
    }

    public struct PerceptionObservation
    {
        public bool IsDetected;
        public Vector2 PixelCoordinates; // (u, v)
        public Vector2 AngularErrorDeg;  // (thetaX, thetaY)
        public float Confidence;         // [0, 1]
        public float SignalToNoiseRatio;
        public float EstimatedIntensity;
    }

    /// <summary>
    /// Beacon perception pipeline: converts optical beacon emissions into
    /// noisy sensor measurements using a Gaussian point-spread function (PSF) model.
    /// </summary>
    public class BeaconPerception : MonoBehaviour
    {
        public Horizon.Simulation.VirtualCameraController CameraController;
        public OpticalBeacon TargetBeacon;

        [Header("Optical Sensor Specs")]
        public float DarkCurrentNoiseStdDev = 1.2f; // pixels
        public float ShotNoiseGain = 0.8f;
        public float MinDetectionSnr = 3.0f; // dB

        [Header("Status")]
        public PerceptionObservation LatestObservation;

        public PerceptionObservation ProcessSensorFrame(float disturbanceNoise, float scintillationDrop, bool isOccluded)
        {
            PerceptionObservation obs = new PerceptionObservation
            {
                IsDetected = false,
                PixelCoordinates = Vector2.zero,
                AngularErrorDeg = Vector2.zero,
                Confidence = 0.0f,
                SignalToNoiseRatio = 0.0f,
                EstimatedIntensity = 0.0f
            };

            if (CameraController == null || TargetBeacon == null || isOccluded)
            {
                LatestObservation = obs;
                return obs;
            }

            // 1. Transform beacon position to camera-local coordinate frame
            Vector3 pCam = CameraController.WorldToCameraSpace(TargetBeacon.EmissionPoint);

            // If behind the camera focal plane, cannot be detected
            if (pCam.z <= 0.05f)
            {
                LatestObservation = obs;
                return obs;
            }

            // 2. Project onto sensor pixel plane using intrinsics
            Horizon.Math.CameraIntrinsics intrinsics = CameraController.Intrinsics;
            if (!intrinsics.WorldToPixel(pCam, out Vector2 truePixel))
            {
                LatestObservation = obs;
                return obs;
            }

            // 3. Check if inside sensor boundary
            if (!intrinsics.IsInSensorBounds(truePixel))
            {
                LatestObservation = obs;
                return obs;
            }

            // 4. Optical attenuation (1/r^2 path loss + scintillation)
            float rangeMeters = Mathf.Max(1.0f, pCam.magnitude);
            float pathLoss = 1.0f / (rangeMeters * rangeMeters);
            float receivedIrradiance = TargetBeacon.RadiantPowerWatts * pathLoss * Mathf.Max(0.01f, 1.0f - scintillationDrop);

            // 5. Sensor noise injection (Gaussian read noise + disturbance noise)
            float totalNoiseSigma = (DarkCurrentNoiseStdDev + disturbanceNoise * 8.0f) * ShotNoiseGain;
            float noiseX = UnityEngine.Random.Range(-1.0f, 1.0f) * totalNoiseSigma;
            float noiseY = UnityEngine.Random.Range(-1.0f, 1.0f) * totalNoiseSigma;

            Vector2 noisyPixel = new Vector2(truePixel.x + noiseX, truePixel.y + noiseY);

            // 6. Signal-to-Noise Ratio (SNR) and detection threshold
            float snr = 10.0f * Mathf.Log10(Mathf.Max(0.1f, (receivedIrradiance * 1000.0f) / (totalNoiseSigma + 0.1f)));
            if (snr < MinDetectionSnr)
            {
                LatestObservation = obs;
                return obs;
            }

            // 7. Calculate angular pointing errors via rigorous pinhole equation
            Vector2 angularErrorsDeg = intrinsics.PixelToAnglesDeg(noisyPixel);

            // 8. Confidence formulation based on SNR and eccentricity
            float pixelOffsetFromCenter = Vector2.Distance(noisyPixel, new Vector2(intrinsics.Cx, intrinsics.Cy));
            float maxRadius = Mathf.Sqrt(intrinsics.Cx * intrinsics.Cx + intrinsics.Cy * intrinsics.Cy);
            float centerBonus = 1.0f - Mathf.Clamp01(pixelOffsetFromCenter / maxRadius);
            float conf = Mathf.Clamp01((snr / 25.0f) * (0.5f + 0.5f * centerBonus));

            obs.IsDetected = true;
            obs.PixelCoordinates = noisyPixel;
            obs.AngularErrorDeg = angularErrorsDeg;
            obs.Confidence = conf;
            obs.SignalToNoiseRatio = snr;
            obs.EstimatedIntensity = receivedIrradiance;

            LatestObservation = obs;
            return obs;
        }
    }
}
