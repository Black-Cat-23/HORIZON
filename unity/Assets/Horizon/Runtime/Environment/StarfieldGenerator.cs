using UnityEngine;

namespace Horizon.Environment
{
    /// <summary>
    /// Generates a 3-layer GPU starfield per Section 2.2 of the 3D World Design spec.
    /// Uses Unity's built-in ParticleSystem to create Near, Mid, and Far depth bands
    /// with different particle densities and independent drift speeds to sell depth parallax.
    /// </summary>
    public class StarfieldGenerator : MonoBehaviour
    {
        [Header("Starfield Settings")]
        public int nearStarCount = 500;
        public int midStarCount = 2000;
        public int farStarCount = 4000;

        public float fieldRadius = 1000f;
        
        [Header("Materials")]
        public Material starMaterial;

        private void Start()
        {
            CreateStarLayer("Stars_Near", nearStarCount, fieldRadius * 0.3f, 1.5f, 0.05f);
            CreateStarLayer("Stars_Mid", midStarCount, fieldRadius * 0.6f, 1.0f, 0.02f);
            CreateStarLayer("Stars_Far", farStarCount, fieldRadius, 0.5f, 0.005f);
        }

        private void CreateStarLayer(string layerName, int count, float radius, float baseSize, float driftSpeed)
        {
            GameObject layerObj = new GameObject(layerName);
            layerObj.transform.SetParent(this.transform, false);

            ParticleSystem ps = layerObj.AddComponent<ParticleSystem>();
            ParticleSystemRenderer psRenderer = layerObj.GetComponent<ParticleSystemRenderer>();

            if (starMaterial == null)
            {
                Shader unlitShader = Shader.Find("Universal Render Pipeline/Unlit");
                if (unlitShader == null) unlitShader = Shader.Find("Sprites/Default");
                starMaterial = new Material(unlitShader);
                starMaterial.name = "Mat_StarParticle";
                starMaterial.color = new Color(0.9f, 0.95f, 1.0f, 0.95f);
            }
            psRenderer.material = starMaterial;
            psRenderer.renderMode = ParticleSystemRenderMode.Billboard;

            var main = ps.main;
            main.loop = true;
            main.playOnAwake = true;
            main.duration = 100f;
            
            // Explicitly use MinMaxCurve to avoid any implicit casting errors in Unity 6
            main.startLifetime = new ParticleSystem.MinMaxCurve(100000f);
            main.startSpeed = new ParticleSystem.MinMaxCurve(0f);
            main.startSize = new ParticleSystem.MinMaxCurve(baseSize);
            
            main.simulationSpace = ParticleSystemSimulationSpace.World;
            main.maxParticles = count;

            var emission = ps.emission;
            emission.rateOverTime = new ParticleSystem.MinMaxCurve(0f);
            
            // Use the explicit modern constructor for Burst
            ParticleSystem.Burst burst = new ParticleSystem.Burst(0f, new ParticleSystem.MinMaxCurve((float)count));
            emission.SetBursts(new ParticleSystem.Burst[] { burst });

            var shape = ps.shape;
            shape.shapeType = ParticleSystemShapeType.Sphere;
            shape.radius = radius;
            shape.radiusThickness = 0.1f;
            
            var velocity = ps.velocityOverLifetime;
            velocity.enabled = true;
            velocity.space = ParticleSystemSimulationSpace.World;
            velocity.x = new ParticleSystem.MinMaxCurve(-driftSpeed, driftSpeed);
            velocity.y = new ParticleSystem.MinMaxCurve(-driftSpeed, driftSpeed);
            velocity.z = new ParticleSystem.MinMaxCurve(-driftSpeed, driftSpeed);

            ps.randomSeed = (uint)Mathf.Abs(layerName.GetHashCode());
            ps.Play();
        }
    }
}
