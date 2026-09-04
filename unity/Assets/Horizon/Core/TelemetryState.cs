using System;
using System.Collections.Generic;

namespace Horizon
{
    public enum TrackMode { Search, Acquire, Track, Degraded, Reacquire }

    /// <summary>Single telemetry object every screen binds to. No per-screen fake values.</summary>
    [Serializable]
    public class TelemetryState
    {
        public float SimTime;
        public float Fps;
        public float LatencyMs;
        public float AngularErrorDeg;
        public TrackMode Mode;
        public float ThetaX, ThetaY, OmegaX, OmegaY, AccelX, AccelY;
        public float CovXX, CovXY, CovYY;
        public float Confidence;
        public readonly List<string> Events = new List<string>();
        public int ReplaySeed;
        public bool HasBenchmark;
    }
}
