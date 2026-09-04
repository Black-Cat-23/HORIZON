using System;
using System.Collections.Generic;
using UnityEngine;

namespace Horizon.Telemetry
{
    [Serializable]
    public struct TelemetryRecord
    {
        public float SimTime;
        public int FrameIndex;
        public int RandomSeed;

        public Vector3 TruthPosition;
        public Vector2 TruthAnglesDeg;

        public bool IsMeasured;
        public Vector2 MeasuredPixel;
        public Vector2 MeasuredAnglesDeg;
        public float MeasuredConfidence;

        public float AngularErrorDeg;

        public Horizon.Estimation.KinematicState EstimatedState;
        public Horizon.Estimation.AngularCovariance Covariance;

        public Vector2 CommandedRatesDegPerSec;
        public Vector2 ActualGimbalAnglesDeg;
        public TrackMode Mode;
        public float LatencyMs;
        public float Fps;
    }

    /// <summary>
    /// Records immutable frame-by-frame telemetry history.
    /// Provides data export to canonical JSON for offline benchmarking and reporting.
    /// </summary>
    public class TelemetryRecorder : MonoBehaviour
    {
        public Horizon.TelemetryState LiveTelemetry = new Horizon.TelemetryState();
        public readonly List<TelemetryRecord> History = new List<TelemetryRecord>();

        public int MaxHistoryFrames = 10000;
        public int CurrentFrameIndex = 0;

        public void ResetRecorder(int seed)
        {
            History.Clear();
            CurrentFrameIndex = 0;
            LiveTelemetry = new Horizon.TelemetryState
            {
                ReplaySeed = seed,
                SimTime = 0.0f,
                HasBenchmark = false
            };
        }

        public void RecordFrame(TelemetryRecord record)
        {
            CurrentFrameIndex++;
            record.FrameIndex = CurrentFrameIndex;

            if (History.Count < MaxHistoryFrames)
            {
                History.Add(record);
            }

            // Synchronize shared live telemetry
            LiveTelemetry.SimTime = record.SimTime;
            LiveTelemetry.Fps = record.Fps;
            LiveTelemetry.LatencyMs = record.LatencyMs;
            LiveTelemetry.AngularErrorDeg = record.AngularErrorDeg;
            LiveTelemetry.Mode = record.Mode;

            LiveTelemetry.ThetaX = record.EstimatedState.ThetaX;
            LiveTelemetry.ThetaY = record.EstimatedState.ThetaY;
            LiveTelemetry.OmegaX = record.EstimatedState.OmegaX;
            LiveTelemetry.OmegaY = record.EstimatedState.OmegaY;
            LiveTelemetry.AccelX = record.EstimatedState.AccelX;
            LiveTelemetry.AccelY = record.EstimatedState.AccelY;

            LiveTelemetry.CovXX = record.Covariance.VarX;
            LiveTelemetry.CovXY = record.Covariance.CovXY;
            LiveTelemetry.CovYY = record.Covariance.VarY;
            LiveTelemetry.Confidence = record.MeasuredConfidence;
        }

        public void LogEvent(string eventText)
        {
            string entry = $"{LiveTelemetry.SimTime:F1}s — {eventText}";
            LiveTelemetry.Events.Insert(0, entry);
            if (LiveTelemetry.Events.Count > 10)
            {
                LiveTelemetry.Events.RemoveAt(LiveTelemetry.Events.Count - 1);
            }
        }
    }
}
