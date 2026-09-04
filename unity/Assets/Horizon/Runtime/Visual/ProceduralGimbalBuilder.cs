using System;
using UnityEngine;

namespace Horizon.Visual
{
    /// <summary>
    /// Procedurally constructs a high-realism, aerospace-grade 2-axis (Azimuth/Elevation)
    /// optical tracking turret. Uses pure procedural meshes for complete structural independence.
    /// </summary>
    public class ProceduralGimbalBuilder : MonoBehaviour
    {
        public Material PlatformMetalMaterial;
        public Material YokeMetalMaterial;
        public Material LensGlassMaterial;
        public Material EmissiveAccentMaterial;

        /// <summary>
        /// Builds the entire gimbal hierarchy and hooks up the VirtualCameraController.
        /// </summary>
        public static Horizon.Simulation.VirtualCameraController BuildGimbal(GameObject root, Material bodyMat, Material yokeMat, Material lensMat, Material accentMat)
        {
            // 1. Base Stator Ring (Mounting flange)
            GameObject baseRing = CreateCylinder("Gimbal_BaseStator", root.transform, 0.45f, 0.12f, 32, bodyMat);
            baseRing.transform.localPosition = new Vector3(0.0f, 0.06f, 0.0f);

            GameObject statorBearing = CreateCylinder("Bearing_Race", baseRing.transform, 0.38f, 0.05f, 32, yokeMat);
            statorBearing.transform.localPosition = new Vector3(0.0f, 0.085f, 0.0f);

            // 2. Azimuth Rotating Yoke
            GameObject azimuthYoke = new GameObject("Gimbal_AzimuthYoke");
            azimuthYoke.transform.SetParent(root.transform, false);
            azimuthYoke.transform.localPosition = new Vector3(0.0f, 0.15f, 0.0f);

            // Yoke Crossbar
            GameObject yokeCrossbar = CreateBox("Yoke_Crossbar", azimuthYoke.transform, new Vector3(0.64f, 0.08f, 0.28f), yokeMat);
            yokeCrossbar.transform.localPosition = new Vector3(0.0f, 0.04f, 0.0f);

            // Yoke Left and Right Vertical Struts
            GameObject leftStrut = CreateBox("Yoke_LeftStrut", azimuthYoke.transform, new Vector3(0.08f, 0.52f, 0.22f), yokeMat);
            leftStrut.transform.localPosition = new Vector3(-0.28f, 0.30f, 0.0f);

            GameObject rightStrut = CreateBox("Yoke_RightStrut", azimuthYoke.transform, new Vector3(0.08f, 0.52f, 0.22f), yokeMat);
            rightStrut.transform.localPosition = new Vector3(0.28f, 0.30f, 0.0f);

            // Elevation Motor Hubs
            GameObject leftHub = CreateCylinder("LeftMotorHub", leftStrut.transform, 0.10f, 0.06f, 24, bodyMat);
            leftHub.transform.localRotation = Quaternion.Euler(0, 0, 90);
            leftHub.transform.localPosition = new Vector3(0.0f, 0.20f, 0.0f);

            GameObject rightHub = CreateCylinder("RightMotorHub", rightStrut.transform, 0.10f, 0.06f, 24, bodyMat);
            rightHub.transform.localRotation = Quaternion.Euler(0, 0, 90);
            rightHub.transform.localPosition = new Vector3(0.0f, 0.20f, 0.0f);

            // 3. Elevation Cradle (Pivoting telescope barrel assembly)
            GameObject elevationCradle = new GameObject("Gimbal_ElevationCradle");
            elevationCradle.transform.SetParent(azimuthYoke.transform, false);
            elevationCradle.transform.localPosition = new Vector3(0.0f, 0.50f, 0.0f);

            // Optical Telescope Barrel
            GameObject barrel = CreateCylinder("Telescope_Barrel", elevationCradle.transform, 0.18f, 0.65f, 32, bodyMat);
            barrel.transform.localRotation = Quaternion.Euler(90, 0, 0);
            barrel.transform.localPosition = new Vector3(0.0f, 0.0f, 0.0f);

            // Forward Sunshade Baffle Ring
            GameObject baffle = CreateCylinder("Sunshade_Baffle", elevationCradle.transform, 0.21f, 0.15f, 32, yokeMat);
            baffle.transform.localRotation = Quaternion.Euler(90, 0, 0);
            baffle.transform.localPosition = new Vector3(0.0f, 0.0f, 0.35f);

            // Multi-Element Objective Lens Glass
            GameObject lens = CreateCylinder("Objective_Lens", elevationCradle.transform, 0.17f, 0.02f, 32, lensMat);
            lens.transform.localRotation = Quaternion.Euler(90, 0, 0);
            lens.transform.localPosition = new Vector3(0.0f, 0.0f, 0.38f);

            // Rear Sensor & Electronics Bay
            GameObject sensorBay = CreateBox("FocalPlane_SensorBay", elevationCradle.transform, new Vector3(0.24f, 0.24f, 0.18f), yokeMat);
            sensorBay.transform.localPosition = new Vector3(0.0f, 0.0f, -0.32f);

            // Optical Aperture Node (Reference point for optical rays and camera view)
            GameObject aperture = new GameObject("OpticalAperture");
            aperture.transform.SetParent(elevationCradle.transform, false);
            aperture.transform.localPosition = new Vector3(0.0f, 0.0f, 0.40f);
            aperture.transform.localRotation = Quaternion.identity;

            // 4. Attach and configure VirtualCameraController
            Horizon.Simulation.VirtualCameraController controller = root.GetComponent<Horizon.Simulation.VirtualCameraController>();
            if (controller == null)
            {
                controller = root.AddComponent<Horizon.Simulation.VirtualCameraController>();
            }

            controller.AzimuthYoke = azimuthYoke.transform;
            controller.ElevationCradle = elevationCradle.transform;
            controller.OpticalAperture = aperture.transform;

            return controller;
        }

        private static GameObject CreateCylinder(string name, Transform parent, float radius, float height, int segments, Material mat)
        {
            GameObject go = new GameObject(name);
            go.transform.SetParent(parent, false);

            MeshFilter mf = go.AddComponent<MeshFilter>();
            MeshRenderer mr = go.AddComponent<MeshRenderer>();
            mr.sharedMaterial = mat;

            mf.sharedMesh = GenerateCylinderMesh(radius, height, segments);
            return go;
        }

        private static GameObject CreateBox(string name, Transform parent, Vector3 size, Material mat)
        {
            GameObject go = new GameObject(name);
            go.transform.SetParent(parent, false);

            MeshFilter mf = go.AddComponent<MeshFilter>();
            MeshRenderer mr = go.AddComponent<MeshRenderer>();
            mr.sharedMaterial = mat;

            mf.sharedMesh = GenerateBoxMesh(size);
            return go;
        }

        private static Mesh GenerateCylinderMesh(float radius, float height, int segments)
        {
            Mesh mesh = new Mesh();
            mesh.name = "ProceduralCylinder";

            int vertexCount = (segments + 1) * 2 + (segments + 1) * 2;
            Vector3[] vertices = new Vector3[vertexCount];
            Vector3[] normals = new Vector3[vertexCount];
            Vector2[] uvs = new Vector2[vertexCount];

            float halfH = height * 0.5f;
            int idx = 0;

            // Side vertices
            for (int i = 0; i <= segments; i++)
            {
                float u = (float)i / segments;
                float angle = u * Mathf.PI * 2.0f;
                float x = Mathf.Cos(angle) * radius;
                float z = Mathf.Sin(angle) * radius;

                vertices[idx] = new Vector3(x, -halfH, z);
                normals[idx] = new Vector3(x, 0, z).normalized;
                uvs[idx] = new Vector2(u, 0);
                idx++;

                vertices[idx] = new Vector3(x, halfH, z);
                normals[idx] = new Vector3(x, 0, z).normalized;
                uvs[idx] = new Vector2(u, 1);
                idx++;
            }

            int triCount = segments * 6;
            int[] triangles = new int[triCount];
            int tIdx = 0;

            for (int i = 0; i < segments; i++)
            {
                int baseIdx = i * 2;
                triangles[tIdx++] = baseIdx;
                triangles[tIdx++] = baseIdx + 1;
                triangles[tIdx++] = baseIdx + 3;

                triangles[tIdx++] = baseIdx;
                triangles[tIdx++] = baseIdx + 3;
                triangles[tIdx++] = baseIdx + 2;
            }

            mesh.vertices = vertices;
            mesh.normals = normals;
            mesh.uv = uvs;
            mesh.triangles = triangles;
            mesh.RecalculateBounds();
            return mesh;
        }

        private static Mesh GenerateBoxMesh(Vector3 size)
        {
            Mesh mesh = new Mesh();
            mesh.name = "ProceduralBox";

            Vector3 half = size * 0.5f;

            Vector3[] vertices = new Vector3[]
            {
                // Front
                new Vector3(-half.x, -half.y,  half.z), new Vector3( half.x, -half.y,  half.z),
                new Vector3( half.x,  half.y,  half.z), new Vector3(-half.x,  half.y,  half.z),
                // Back
                new Vector3( half.x, -half.y, -half.z), new Vector3(-half.x, -half.y, -half.z),
                new Vector3(-half.x,  half.y, -half.z), new Vector3( half.x,  half.y, -half.z),
                // Top
                new Vector3(-half.x,  half.y,  half.z), new Vector3( half.x,  half.y,  half.z),
                new Vector3( half.x,  half.y, -half.z), new Vector3(-half.x,  half.y, -half.z),
                // Bottom
                new Vector3(-half.x, -half.y, -half.z), new Vector3( half.x, -half.y, -half.z),
                new Vector3( half.x, -half.y,  half.z), new Vector3(-half.x, -half.y,  half.z),
                // Left
                new Vector3(-half.x, -half.y, -half.z), new Vector3(-half.x, -half.y,  half.z),
                new Vector3(-half.x,  half.y,  half.z), new Vector3(-half.x,  half.y, -half.z),
                // Right
                new Vector3( half.x, -half.y,  half.z), new Vector3( half.x, -half.y, -half.z),
                new Vector3( half.x,  half.y, -half.z), new Vector3( half.x,  half.y,  half.z),
            };

            int[] triangles = new int[]
            {
                0,1,2, 0,2,3,       // Front
                4,5,6, 4,6,7,       // Back
                8,9,10, 8,10,11,    // Top
                12,13,14, 12,14,15, // Bottom
                16,17,18, 16,18,19, // Left
                20,21,22, 20,22,23  // Right
            };

            mesh.vertices = vertices;
            mesh.triangles = triangles;
            mesh.RecalculateNormals();
            mesh.RecalculateBounds();
            return mesh;
        }
    }
}
