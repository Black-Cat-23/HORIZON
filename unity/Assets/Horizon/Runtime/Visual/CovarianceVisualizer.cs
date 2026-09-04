using System;
using UnityEngine;

namespace Horizon.Visual
{
    /// <summary>
    /// Visualizes the mathematical estimation uncertainty region derived from the Kalman filter covariance matrix.
    /// Never uses an arbitrary decorative ellipse — dimensions map strictly to covariance eigenvalues.
    /// </summary>
    [RequireComponent(typeof(LineRenderer))]
    public class CovarianceVisualizer : MonoBehaviour
    {
        public Horizon.Estimation.HorizonEstimator Estimator;
        public Transform TargetPlatform;
        public int SegmentCount = 48;
        public float ConfidenceScaleFactor = 2.0f; // 2-sigma (95% confidence interval)

        private LineRenderer _line;

        private void Awake()
        {
            _line = GetComponent<LineRenderer>();
            _line.positionCount = SegmentCount + 1;
            _line.startWidth = 0.04f;
            _line.endWidth = 0.04f;
            _line.useWorldSpace = true;
        }

        private void LateUpdate()
        {
            if (Estimator == null || TargetPlatform == null) return;

            Horizon.Estimation.AngularCovariance cov = Estimator.Covariance;
            Vector3 center = TargetPlatform.position;

            // Semi-axes scaled by confidence sigma
            float a = Mathf.Max(0.1f, cov.SemiMajorAxis * ConfidenceScaleFactor);
            float b = Mathf.Max(0.08f, cov.SemiMinorAxis * ConfidenceScaleFactor);
            float angleRad = cov.OrientationDeg * Mathf.Deg2Rad;

            float cosA = Mathf.Cos(angleRad);
            float sinA = Mathf.Sin(angleRad);

            // Compute ellipse vertices facing the camera/observer
            for (int i = 0; i <= SegmentCount; i++)
            {
                float t = (float)i / SegmentCount * Mathf.PI * 2.0f;
                float ex = Mathf.Cos(t) * a;
                float ey = Mathf.Sin(t) * b;

                // Rotate by covariance orientation
                float rx = (ex * cosA) - (ey * sinA);
                float ry = (ex * sinA) + (ey * cosA);

                Vector3 point = center + new Vector3(rx, ry, 0.0f);
                _line.SetPosition(i, point);
            }

            // Bind alpha to filter confidence
            Color c = Horizon.HorizonTokens.LockCyanColor;
            c.a = Mathf.Clamp(0.15f + (Estimator.OverallConfidence * 0.7f), 0.1f, 0.9f);
            _line.startColor = c;
            _line.endColor = c;
        }
    }
}
