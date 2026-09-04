using System;
using UnityEngine;

namespace Horizon.Estimation
{
    [Serializable]
    public struct KinematicState
    {
        public float ThetaX;  // deg
        public float ThetaY;  // deg
        public float OmegaX;  // deg/s
        public float OmegaY;  // deg/s
        public float AccelX;  // deg/s^2
        public float AccelY;  // deg/s^2
    }

    [Serializable]
    public struct AngularCovariance
    {
        public float VarX;    // deg^2
        public float CovXY;   // deg^2
        public float VarY;    // deg^2

        public float SemiMajorAxis;
        public float SemiMinorAxis;
        public float OrientationDeg;
    }

    /// <summary>
    /// Uncertainty-aware Discrete Kalman Filter for 2D angular state estimation.
    /// Tracks angular error, angular velocity, and angular acceleration.
    /// </summary>
    public class HorizonEstimator : MonoBehaviour
    {
        [Header("Tuning Parameters")]
        public float ProcessNoisePosition = 0.05f;
        public float ProcessNoiseVelocity = 0.5f;
        public float ProcessNoiseAccel = 2.0f;
        public float MeasurementNoiseBase = 0.15f;

        [Header("State Vector")]
        public KinematicState State;
        public AngularCovariance Covariance;
        public float OverallConfidence = 0.0f;

        // Internal filter state vectors and matrices
        private float[] _x = new float[6]; // [thetaX, thetaY, omegaX, omegaY, ax, ay]
        private float[,] _P = new float[6, 6];

        public void ResetFilter(float initThetaX, float initThetaY)
        {
            Array.Clear(_x, 0, 6);
            _x[0] = initThetaX;
            _x[1] = initThetaY;

            Array.Clear(_P, 0, 36);
            _P[0, 0] = 5.0f;
            _P[1, 1] = 5.0f;
            _P[2, 2] = 20.0f;
            _P[3, 3] = 20.0f;
            _P[4, 4] = 50.0f;
            _P[5, 5] = 50.0f;

            UpdateOutputProperties();
        }

        private void Awake()
        {
            ResetFilter(0.0f, 0.0f);
        }

        /// <summary>
        /// Predict step using discrete kinematic integration over dt.
        /// </summary>
        public void Predict(float dt)
        {
            if (dt <= 0.0001f) return;

            float dt2 = 0.5f * dt * dt;

            // State prediction: x = F * x
            _x[0] += _x[2] * dt + _x[4] * dt2;
            _x[1] += _x[3] * dt + _x[5] * dt2;
            _x[2] += _x[4] * dt;
            _x[3] += _x[5] * dt;

            // Process covariance addition: P = F*P*F^T + Q
            _P[0, 0] += ProcessNoisePosition * dt + (_P[2, 2] * dt * dt);
            _P[1, 1] += ProcessNoisePosition * dt + (_P[3, 3] * dt * dt);
            _P[2, 2] += ProcessNoiseVelocity * dt;
            _P[3, 3] += ProcessNoiseVelocity * dt;
            _P[4, 4] += ProcessNoiseAccel * dt;
            _P[5, 5] += ProcessNoiseAccel * dt;

            UpdateOutputProperties();
        }

        /// <summary>
        /// Measurement update step from sensor observation.
        /// </summary>
        public void UpdateMeasurement(Vector2 measuredAnglesDeg, float observationConfidence, float sensorNoise)
        {
            float r = MeasurementNoiseBase + sensorNoise * 2.0f;
            r /= Mathf.Max(0.05f, observationConfidence);

            // Innovation (residual)
            float y0 = measuredAnglesDeg.x - _x[0];
            float y1 = measuredAnglesDeg.y - _x[1];

            // Innovation covariance S = H*P*H^T + R
            float s0 = _P[0, 0] + r;
            float s1 = _P[1, 1] + r;

            // Kalman Gain K = P*H^T * S^-1
            float k0 = _P[0, 0] / s0;
            float k1 = _P[1, 1] / s1;
            float k2 = _P[2, 0] / s0;
            float k3 = _P[3, 1] / s1;
            float k4 = _P[4, 0] / s0;
            float k5 = _P[5, 1] / s1;

            // State update
            _x[0] += k0 * y0;
            _x[1] += k1 * y1;
            _x[2] += k2 * y0;
            _x[3] += k3 * y1;
            _x[4] += k4 * y0;
            _x[5] += k5 * y1;

            // Covariance update: P = (I - K*H) * P
            _P[0, 0] *= (1.0f - k0);
            _P[1, 1] *= (1.0f - k1);
            _P[2, 2] *= (1.0f - k2 * 0.5f);
            _P[3, 3] *= (1.0f - k3 * 0.5f);
            _P[4, 4] *= (1.0f - k4 * 0.2f);
            _P[5, 5] *= (1.0f - k5 * 0.2f);

            UpdateOutputProperties();
        }

        private void UpdateOutputProperties()
        {
            State.ThetaX = _x[0];
            State.ThetaY = _x[1];
            State.OmegaX = _x[2];
            State.OmegaY = _x[3];
            State.AccelX = _x[4];
            State.AccelY = _x[5];

            Covariance.VarX = Mathf.Max(0.001f, _P[0, 0]);
            Covariance.VarY = Mathf.Max(0.001f, _P[1, 1]);
            Covariance.CovXY = _P[0, 1];

            // Eigenvalue decomposition of upper 2x2 covariance for uncertainty ellipse
            float a = Covariance.VarX;
            float b = Covariance.CovXY;
            float c = Covariance.VarY;

            float trace = a + c;
            float det = (a * c) - (b * b);
            float root = Mathf.Sqrt(Mathf.Max(0.0f, ((a - c) * (a - c)) + (4.0f * b * b)));

            float lambda1 = (trace + root) * 0.5f;
            float lambda2 = Mathf.Max(0.001f, (trace - root) * 0.5f);

            Covariance.SemiMajorAxis = Mathf.Sqrt(Mathf.Max(0.001f, lambda1));
            Covariance.SemiMinorAxis = Mathf.Sqrt(Mathf.Max(0.001f, lambda2));

            float angleRad = 0.5f * Mathf.Atan2(2.0f * b, a - c);
            Covariance.OrientationDeg = angleRad * Mathf.Rad2Deg;

            // Confidence score inversely proportional to error magnitude and covariance
            float errorNorm = Mathf.Sqrt((_x[0] * _x[0]) + (_x[1] * _x[1]));
            float covNorm = Mathf.Sqrt(lambda1);
            OverallConfidence = Mathf.Clamp01(1.0f / (1.0f + (errorNorm * 0.4f) + (covNorm * 0.8f)));
        }
    }
}
