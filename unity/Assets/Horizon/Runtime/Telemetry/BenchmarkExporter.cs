using System;
using System.Collections.Generic;
using System.IO;
using UnityEngine;

namespace Horizon.Telemetry
{
    [Serializable]
    public class BenchmarkExportData
    {
        public string Timestamp;
        public int TotalTrials;
        public List<string> EvaluatedAlgorithms = new List<string>();
        public List<BenchmarkMetricRow> Metrics = new List<BenchmarkMetricRow>();
        public List<FailureReplayEntry> FailureReplays = new List<FailureReplayEntry>();
    }

    [Serializable]
    public class BenchmarkMetricRow
    {
        public string MetricId;
        public string Label;
        public string Better; // "high" or "low"
        public float B0;
        public float B1;
        public float B2;
        public float Ours;
    }

    [Serializable]
    public class FailureReplayEntry
    {
        public int TrialIndex;
        public int RandomSeed;
        public float LostAtSeconds;
        public string Cause;
    }

    /// <summary>
    /// Exports statistical Monte Carlo benchmark runs from Unity into canonical JSON.
    /// The website consumes this exact file for zero-fabrication metrics display.
    /// </summary>
    public static class BenchmarkExporter
    {
        public static string ExportBenchmarkJson(BenchmarkExportData data, string customPath = null)
        {
            string json = JsonUtility.ToJson(data, true);

            string targetDir = customPath;
            if (string.IsNullOrEmpty(targetDir))
            {
                string projectRoot = Directory.GetParent(Application.dataPath).FullName;
                string workspaceRoot = Directory.GetParent(projectRoot).FullName;
                targetDir = Path.Combine(workspaceRoot, "Benchmarks", "results");
            }

            if (!Directory.Exists(targetDir))
            {
                Directory.CreateDirectory(targetDir);
            }

            string targetFile = Path.Combine(targetDir, "horizon_benchmark_canonical.json");
            File.WriteAllText(targetFile, json);
            Debug.Log($"[HORIZON] Benchmark results successfully exported to: {targetFile}");

            return targetFile;
        }
    }
}
