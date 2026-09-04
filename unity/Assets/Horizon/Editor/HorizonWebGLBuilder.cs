#if UNITY_EDITOR
using UnityEditor;
using UnityEditor.Build.Reporting;
using UnityEngine;
using System.IO;

namespace Horizon.Editor
{
    /// <summary>
    /// Builds the Unity 3D simulation to WebAssembly (WebGL) directly targeting
    /// the web application folder for seamless website integration.
    /// </summary>
    public static class HorizonWebGLBuilder
    {
        [MenuItem("HORIZON/Build to WebGL (for Web App Integration)")]
        public static void BuildWebGL()
        {
            Debug.Log("[HORIZON] Starting WebGL compilation for website integration...");

            string scenePath = "Assets/Horizon/Scenes/HorizonSimulationScene.unity";
            if (!File.Exists(scenePath))
            {
                Debug.Log("[HORIZON] Scene not found. Generating scene first...");
                HorizonSceneCreator.BuildSimulationScene();
            }

            // Target output folder in web application
            string projectRoot = Directory.GetParent(Application.dataPath).FullName;
            string workspaceRoot = Directory.GetParent(projectRoot).FullName;
            string outputFolder = Path.Combine(workspaceRoot, "app", "unity_build");

            if (!Directory.Exists(outputFolder))
            {
                Directory.CreateDirectory(outputFolder);
            }

            // WebGL Player Settings
            PlayerSettings.WebGL.compressionFormat = WebGLCompressionFormat.Disabled; // Uncompressed for immediate local testing
            PlayerSettings.WebGL.decompressionFallback = true;
            PlayerSettings.WebGL.memorySize = 512;
            PlayerSettings.runInBackground = true;

            BuildPlayerOptions buildOptions = new BuildPlayerOptions
            {
                scenes = new[] { scenePath },
                locationPathName = outputFolder,
                target = BuildTarget.WebGL,
                options = BuildOptions.None
            };

            BuildReport report = BuildPipeline.BuildPlayer(buildOptions);
            BuildSummary summary = report.summary;

            if (summary.result == BuildResult.Succeeded)
            {
                Debug.Log($"[HORIZON] WebGL build succeeded! Output: {outputFolder} (Size: {summary.totalSize / (1024 * 1024)} MB)");
            }
            else if (summary.result == BuildResult.Failed)
            {
                Debug.LogError($"[HORIZON] WebGL build failed with {summary.totalErrors} errors.");
            }
        }
    }
}
#endif
