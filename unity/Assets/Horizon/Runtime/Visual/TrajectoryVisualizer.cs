using System;
using System.Collections.Generic;
using UnityEngine;

namespace Horizon.Visual
{
    /// <summary>
    /// Visualizes ground truth trajectory and filter predicted trajectory trails in 3D world space.
    /// </summary>
    public class TrajectoryVisualizer : MonoBehaviour
    {
        public LineRenderer ActualTrailRenderer;
        public LineRenderer PredictedTrailRenderer;

        public int MaxTrailPoints = 250;
        public float MinPointDistance = 0.2f;

        private readonly List<Vector3> _actualPoints = new List<Vector3>();
        private readonly List<Vector3> _predictedPoints = new List<Vector3>();

        private void Awake()
        {
            if (ActualTrailRenderer != null)
            {
                ActualTrailRenderer.startWidth = 0.03f;
                ActualTrailRenderer.endWidth = 0.015f;
                ActualTrailRenderer.startColor = Horizon.HorizonTokens.LockCyanColor;
                ActualTrailRenderer.endColor = new Color(0.498f, 0.831f, 0.910f, 0.1f);
            }

            if (PredictedTrailRenderer != null)
            {
                PredictedTrailRenderer.startWidth = 0.02f;
                PredictedTrailRenderer.endWidth = 0.01f;
                PredictedTrailRenderer.startColor = new Color(0.498f, 0.831f, 0.910f, 0.45f);
                PredictedTrailRenderer.endColor = new Color(0.498f, 0.831f, 0.910f, 0.05f);
            }
        }

        public void AddTrajectoryStep(Vector3 actualPos, Vector3 predictedPos)
        {
            if (_actualPoints.Count == 0 || Vector3.Distance(_actualPoints[_actualPoints.Count - 1], actualPos) > MinPointDistance)
            {
                _actualPoints.Add(actualPos);
                if (_actualPoints.Count > MaxTrailPoints) _actualPoints.RemoveAt(0);

                if (ActualTrailRenderer != null)
                {
                    ActualTrailRenderer.positionCount = _actualPoints.Count;
                    ActualTrailRenderer.SetPositions(_actualPoints.ToArray());
                }
            }

            if (_predictedPoints.Count == 0 || Vector3.Distance(_predictedPoints[_predictedPoints.Count - 1], predictedPos) > MinPointDistance)
            {
                _predictedPoints.Add(predictedPos);
                if (_predictedPoints.Count > MaxTrailPoints) _predictedPoints.RemoveAt(0);

                if (PredictedTrailRenderer != null)
                {
                    PredictedTrailRenderer.positionCount = _predictedPoints.Count;
                    PredictedTrailRenderer.SetPositions(_predictedPoints.ToArray());
                }
            }
        }

        public void ClearTrails()
        {
            _actualPoints.Clear();
            _predictedPoints.Clear();

            if (ActualTrailRenderer != null) ActualTrailRenderer.positionCount = 0;
            if (PredictedTrailRenderer != null) PredictedTrailRenderer.positionCount = 0;
        }
    }
}
