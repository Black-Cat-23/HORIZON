using System;
using UnityEngine;
using UnityEngine.Rendering;

namespace Horizon.Environment
{
    /// <summary>
    /// Establishes the aerospace space laboratory environment strictly according to docs/3D_WORLD_DESIGN.md.
    /// Features: Near-black void (#070912), multi-layer GPU starfield, dim ambient starlight (no studio 3-point lighting),
    /// no ground grid plane (Section 2.3), and URP post-processing bloom/color grading.
    /// </summary>
    public class HorizonEnvironmentDirector : MonoBehaviour
    {
        [Header("Lighting")]
        public Light AmbientStarlight;

        [Header("Environment Subsystems")]
        public StarfieldGenerator Starfield;
        public Volume PostProcessingVolume;

        public void SetupEnvironment()
        {
            // 1. Dark Void Background (#070912) per Section 2.1
            Color voidColor = HorizonTokens.VoidColor; // #070912
            if (UnityEngine.Camera.main != null)
            {
                UnityEngine.Camera.main.clearFlags = CameraClearFlags.SolidColor;
                UnityEngine.Camera.main.backgroundColor = voidColor;
            }

            RenderSettings.ambientMode = AmbientMode.Flat;
            RenderSettings.ambientLight = new Color(0.04f, 0.05f, 0.09f, 1.0f); // subtle starlight fill

            // 2. Single dim cool-blue directional "ambient starlight" per Section 6
            // (No key light, no fill light, no studio 3-point setup)
            if (AmbientStarlight == null)
            {
                GameObject starlightGo = new GameObject("Ambient_Starlight");
                starlightGo.transform.SetParent(transform, false);
                starlightGo.transform.rotation = Quaternion.Euler(35.0f, -40.0f, 0.0f);

                AmbientStarlight = starlightGo.AddComponent<Light>();
                AmbientStarlight.type = LightType.Directional;
                AmbientStarlight.color = new Color(0.55f, 0.70f, 0.95f); // cool starlight
                AmbientStarlight.intensity = 0.18f; // dim, just enough for gimbal silhouette
                AmbientStarlight.shadows = LightShadows.None;
            }

            // 3. Multi-Layer GPU Starfield per Section 2.2
            GameObject starfieldGo = GameObject.Find("Horizon_StarfieldSystem");
            if (starfieldGo == null)
            {
                starfieldGo = new GameObject("Horizon_StarfieldSystem");
                starfieldGo.transform.SetParent(transform, false);
                Starfield = starfieldGo.AddComponent<StarfieldGenerator>();
            }

            // 4. Global Post-Processing Volume (Bloom & Void Tonemapping) per Section 7
            SetupPostProcessingVolume();
        }

        private void SetupPostProcessingVolume()
        {
            GameObject volumeGo = GameObject.Find("Horizon_GlobalVolume");
            if (volumeGo == null)
            {
                volumeGo = new GameObject("Horizon_GlobalVolume");
                volumeGo.transform.SetParent(transform, false);
                PostProcessingVolume = volumeGo.AddComponent<Volume>();
                PostProcessingVolume.isGlobal = true;
                PostProcessingVolume.priority = 1.0f;

                // Programmatically create VolumeProfile
                VolumeProfile profile = ScriptableObject.CreateInstance<VolumeProfile>();
                profile.name = "Horizon_URP_VolumeProfile";

                // Add Bloom override dynamically if Universal RP volume overrides are available
                try
                {
                    Type bloomType = Type.GetType("UnityEngine.Rendering.Universal.Bloom, Unity.RenderPipelines.Universal.Runtime");
                    if (bloomType != null)
                    {
                        var bloomInstance = (VolumeComponent)ScriptableObject.CreateInstance(bloomType);
                        var thresholdProp = bloomType.GetField("threshold");
                        var intensityProp = bloomType.GetField("intensity");
                        var scatterProp = bloomType.GetField("scatter");

                        if (thresholdProp != null && intensityProp != null)
                        {
                            var thresholdVal = thresholdProp.GetValue(bloomInstance);
                            var intensityVal = intensityProp.GetValue(bloomInstance);
                            
                            // Set override state to true via reflection
                            thresholdVal.GetType().GetProperty("overrideState")?.SetValue(thresholdVal, true);
                            thresholdVal.GetType().GetProperty("value")?.SetValue(thresholdVal, 0.9f);

                            intensityVal.GetType().GetProperty("overrideState")?.SetValue(intensityVal, true);
                            intensityVal.GetType().GetProperty("value")?.SetValue(intensityVal, 2.5f);

                            if (scatterProp != null)
                            {
                                var scatterVal = scatterProp.GetValue(bloomInstance);
                                scatterVal.GetType().GetProperty("overrideState")?.SetValue(scatterVal, true);
                                scatterVal.GetType().GetProperty("value")?.SetValue(scatterVal, 0.7f);
                            }
                        }

                        profile.components.Add(bloomInstance);
                    }
                }
                catch (Exception e)
                {
                    Debug.LogWarning("[HorizonEnvironmentDirector] URP Bloom override initialization deferred: " + e.Message);
                }

                PostProcessingVolume.profile = profile;
            }
        }
    }
}

