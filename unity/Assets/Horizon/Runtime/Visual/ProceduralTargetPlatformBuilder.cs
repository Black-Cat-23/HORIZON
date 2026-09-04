using System;
using UnityEngine;

namespace Horizon.Visual
{
    /// <summary>
    /// Procedurally constructs a compact aerospace mobile terminal platform carrying
    /// the designated optical beacon. Structural independence guaranteed via pure procedural mesh.
    /// </summary>
    public class ProceduralTargetPlatformBuilder : MonoBehaviour
    {
        public static Horizon.Perception.OpticalBeacon BuildTargetPlatform(GameObject root, Material busMat, Material panelMat, Material emitterMat, Material glowMat)
        {
            // 1. Central Avionics Bus Body (Hexagonal Prism)
            GameObject bus = CreateHexPrism("Target_Bus", root.transform, 0.42f, 0.30f, busMat);
            bus.transform.localPosition = Vector3.zero;

            // 2. Solar / Radiator Panels (Left and Right Wings)
            GameObject leftPanel = CreateBox("SolarPanel_Left", bus.transform, new Vector3(0.70f, 0.02f, 0.35f), panelMat);
            leftPanel.transform.localPosition = new Vector3(-0.65f, 0.0f, 0.0f);

            GameObject rightPanel = CreateBox("SolarPanel_Right", bus.transform, new Vector3(0.70f, 0.02f, 0.35f), panelMat);
            rightPanel.transform.localPosition = new Vector3(0.65f, 0.0f, 0.0f);

            // 3. Optical Beacon Emitter Turret Pod
            GameObject emitterPod = CreateCylinder("Beacon_TurretPod", bus.transform, 0.12f, 0.18f, 24, busMat);
            emitterPod.transform.localPosition = new Vector3(0.0f, 0.20f, 0.05f);

            // Optical Collimating Lens Ring
            GameObject lensRing = CreateCylinder("Collimator_Ring", emitterPod.transform, 0.09f, 0.04f, 24, emitterMat);
            lensRing.transform.localPosition = new Vector3(0.0f, 0.10f, 0.0f);

            // Beacon Luminous Core Emitter Quad (Visible in 3D world with OpticalBeaconGlow shader)
            GameObject glowQuad = CreateGlowBillboard("Beacon_GlowCore", lensRing.transform, 0.65f, glowMat);
            glowQuad.transform.localPosition = new Vector3(0.0f, 0.04f, 0.0f);

            // Point Light driving the URP bloom kernel per Section 3.2
            Light beaconLight = glowQuad.AddComponent<Light>();
            beaconLight.type = LightType.Point;
            beaconLight.color = new Color(0.498f, 0.831f, 0.910f, 1.0f); // #7fd4e8 cyan
            beaconLight.intensity = 8.5f; // HDR radiant intensity to trigger Bloom
            beaconLight.range = 80.0f;
            beaconLight.shadows = LightShadows.None;

            // 4. Attach and configure OpticalBeacon component
            Horizon.Perception.OpticalBeacon beacon = root.GetComponent<Horizon.Perception.OpticalBeacon>();
            if (beacon == null)
            {
                beacon = root.AddComponent<Horizon.Perception.OpticalBeacon>();
            }

            return beacon;
        }

        private static GameObject CreateHexPrism(string name, Transform parent, float radius, float height, Material mat)
        {
            GameObject go = new GameObject(name);
            go.transform.SetParent(parent, false);

            MeshFilter mf = go.AddComponent<MeshFilter>();
            MeshRenderer mr = go.AddComponent<MeshRenderer>();
            mr.sharedMaterial = mat;

            mf.sharedMesh = GenerateHexPrismMesh(radius, height);
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

        private static GameObject CreateGlowBillboard(string name, Transform parent, float size, Material mat)
        {
            GameObject go = new GameObject(name);
            go.transform.SetParent(parent, false);

            MeshFilter mf = go.AddComponent<MeshFilter>();
            MeshRenderer mr = go.AddComponent<MeshRenderer>();
            mr.sharedMaterial = mat;

            Mesh mesh = new Mesh();
            mesh.name = "GlowQuad";
            float h = size * 0.5f;
            mesh.vertices = new Vector3[]
            {
                new Vector3(-h, -h, 0), new Vector3(h, -h, 0),
                new Vector3(h, h, 0), new Vector3(-h, h, 0)
            };
            mesh.uv = new Vector2[] { new Vector2(0, 0), new Vector2(1, 0), new Vector2(1, 1), new Vector2(0, 1) };
            mesh.triangles = new int[] { 0, 1, 2, 0, 2, 3 };
            mesh.RecalculateNormals();

            mf.sharedMesh = mesh;
            return go;
        }

        private static Mesh GenerateHexPrismMesh(float radius, float height)
        {
            Mesh mesh = new Mesh();
            mesh.name = "ProceduralHexPrism";
            int sides = 6;

            Vector3[] vertices = new Vector3[sides * 2 + 2];
            int[] triangles = new int[sides * 12];

            float halfH = height * 0.5f;

            for (int i = 0; i < sides; i++)
            {
                float angle = (i / 6.0f) * Mathf.PI * 2.0f;
                float x = Mathf.Cos(angle) * radius;
                float z = Mathf.Sin(angle) * radius;

                vertices[i] = new Vector3(x, -halfH, z);
                vertices[i + sides] = new Vector3(x, halfH, z);
            }

            int topCenter = sides * 2;
            int botCenter = sides * 2 + 1;
            vertices[topCenter] = new Vector3(0, halfH, 0);
            vertices[botCenter] = new Vector3(0, -halfH, 0);

            int t = 0;
            for (int i = 0; i < sides; i++)
            {
                int next = (i + 1) % sides;

                // Side quads
                triangles[t++] = i;
                triangles[t++] = i + sides;
                triangles[t++] = next + sides;

                triangles[t++] = i;
                triangles[t++] = next + sides;
                triangles[t++] = next;

                // Top cap
                triangles[t++] = topCenter;
                triangles[t++] = next + sides;
                triangles[t++] = i + sides;

                // Bottom cap
                triangles[t++] = botCenter;
                triangles[t++] = i;
                triangles[t++] = next;
            }

            mesh.vertices = vertices;
            mesh.triangles = triangles;
            mesh.RecalculateNormals();
            mesh.RecalculateBounds();
            return mesh;
        }

        private static Mesh GenerateBoxMesh(Vector3 size)
        {
            Mesh mesh = new Mesh();
            mesh.name = "ProceduralBox";
            Vector3 h = size * 0.5f;

            mesh.vertices = new Vector3[]
            {
                new Vector3(-h.x, -h.y,  h.z), new Vector3( h.x, -h.y,  h.z),
                new Vector3( h.x,  h.y,  h.z), new Vector3(-h.x,  h.y,  h.z),
                new Vector3( h.x, -h.y, -h.z), new Vector3(-h.x, -h.y, -h.z),
                new Vector3(-h.x,  h.y, -h.z), new Vector3( h.x,  h.y, -h.z)
            };

            mesh.triangles = new int[]
            {
                0,1,2, 0,2,3, 4,5,6, 4,6,7, 3,2,7, 3,7,6,
                0,5,4, 0,4,1, 1,4,7, 1,7,2, 0,3,6, 0,6,5
            };
            mesh.RecalculateNormals();
            return mesh;
        }

        private static Mesh GenerateCylinderMesh(float radius, float height, int segments)
        {
            Mesh mesh = new Mesh();
            mesh.name = "ProceduralCylinder";
            int vCount = (segments + 1) * 2;
            Vector3[] v = new Vector3[vCount];
            float halfH = height * 0.5f;
            int idx = 0;

            for (int i = 0; i <= segments; i++)
            {
                float u = (float)i / segments;
                float a = u * Mathf.PI * 2.0f;
                float x = Mathf.Cos(a) * radius;
                float z = Mathf.Sin(a) * radius;

                v[idx++] = new Vector3(x, -halfH, z);
                v[idx++] = new Vector3(x, halfH, z);
            }

            int[] tris = new int[segments * 6];
            int t = 0;
            for (int i = 0; i < segments; i++)
            {
                int b = i * 2;
                tris[t++] = b;
                tris[t++] = b + 1;
                tris[t++] = b + 3;

                tris[t++] = b;
                tris[t++] = b + 3;
                tris[t++] = b + 2;
            }

            mesh.vertices = v;
            mesh.triangles = tris;
            mesh.RecalculateNormals();
            return mesh;
        }
    }
}
