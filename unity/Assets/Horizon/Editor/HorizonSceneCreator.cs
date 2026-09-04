#if UNITY_EDITOR
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.SceneManagement;
using System.IO;
using Horizon;

namespace Horizon.Editor
{
    /// <summary>
    /// Editor utility to construct and save the complete 3D simulation scene
    /// with one click from the Unity menu bar or via command-line batch mode.
    /// </summary>
    public static class HorizonSceneCreator
    {
        [MenuItem("HORIZON/Build Complete 3D Simulation Scene")]
        public static void BuildSimulationScene()
        {
            Debug.Log("[HORIZON] Building 3D Simulation Environment Scene...");

            // 1. Create a new empty scene
            Scene scene = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);

            // 2. Instantiate Master Scene Bootstrapper
            GameObject masterGo = new GameObject("HORIZON_Simulation_Master");
            Horizon3DSceneBootstrapper bootstrapper = masterGo.AddComponent<Horizon3DSceneBootstrapper>();

            // 3. Ensure target directories exist
            string scenesDir = "Assets/Horizon/Scenes";
            if (!Directory.Exists(scenesDir))
            {
                Directory.CreateDirectory(scenesDir);
                AssetDatabase.Refresh();
            }

            // 4. Save Scene
            string scenePath = Path.Combine(scenesDir, "HorizonSimulationScene.unity").Replace("\\", "/");
            EditorSceneManager.SaveScene(scene, scenePath);
            Debug.Log($"[HORIZON] Scene successfully saved to: {scenePath}");

            // 5. Register in Build Settings
            EditorBuildSettingsScene[] currentScenes = EditorBuildSettings.scenes;
            bool alreadyInBuild = false;
            foreach (var s in currentScenes)
            {
                if (s.path == scenePath)
                {
                    alreadyInBuild = true;
                    break;
                }
            }

            if (!alreadyInBuild)
            {
                EditorBuildSettingsScene[] newScenes = new EditorBuildSettingsScene[currentScenes.Length + 1];
                currentScenes.CopyTo(newScenes, 0);
                newScenes[newScenes.Length - 1] = new EditorBuildSettingsScene(scenePath, true);
                EditorBuildSettings.scenes = newScenes;
                Debug.Log($"[HORIZON] Added {scenePath} to EditorBuildSettings.scenes");
            }

            AssetDatabase.SaveAssets();
            AssetDatabase.Refresh();

            Debug.Log("[HORIZON] 3D Simulation Environment is ready to run. Press Play!");
        }
    }
}
#endif
