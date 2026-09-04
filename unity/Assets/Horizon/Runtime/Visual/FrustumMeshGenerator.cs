using System;
using UnityEngine;

namespace Horizon.Visual
{
    /// <summary>
    /// Procedurally builds and updates a 4-sided translucent viewing frustum
    /// representing the optical camera's field of view in 3D world space.
    /// </summary>
    [RequireComponent(typeof(MeshFilter), typeof(MeshRenderer))]
    public class FrustumMeshGenerator : MonoBehaviour
    {
        public Horizon.Simulation.VirtualCameraController CameraController;
        public float FrustumLength = 45.0f;

        private MeshFilter _meshFilter;
        private Mesh _frustumMesh;

        private void Awake()
        {
            _meshFilter = GetComponent<MeshFilter>();
            _frustumMesh = new Mesh();
            _frustumMesh.name = "DynamicCameraFrustum";
            _meshFilter.sharedMesh = _frustumMesh;
        }

        public void UpdateFrustumGeometry()
        {
            if (CameraController == null || _frustumMesh == null) return;

            float hFovDeg = CameraController.Intrinsics.HorizontalFovDeg;
            float vFovDeg = CameraController.Intrinsics.VerticalFovDeg;

            float hHalfRad = (hFovDeg * 0.5f) * Mathf.Deg2Rad;
            float vHalfRad = (vFovDeg * 0.5f) * Mathf.Deg2Rad;

            float z = FrustumLength;
            float halfW = Mathf.Tan(hHalfRad) * z;
            float halfH = Mathf.Tan(vHalfRad) * z;

            // 5 vertices: Apex at origin, 4 far-plane corners
            Vector3 apex = Vector3.zero;
            Vector3 topLeft = new Vector3(-halfW, halfH, z);
            Vector3 topRight = new Vector3(halfW, halfH, z);
            Vector3 botRight = new Vector3(halfW, -halfH, z);
            Vector3 botLeft = new Vector3(-halfW, -halfH, z);

            Vector3[] vertices = new Vector3[]
            {
                // Top face
                apex, topLeft, topRight,
                // Right face
                apex, topRight, botRight,
                // Bottom face
                apex, botRight, botLeft,
                // Left face
                apex, botLeft, topLeft,
                // Far face
                topLeft, botLeft, botRight,
                topLeft, botRight, topRight
            };

            int[] triangles = new int[]
            {
                0, 1, 2,     // Top
                3, 4, 5,     // Right
                6, 7, 8,     // Bottom
                9, 10, 11,   // Left
                12, 13, 14,  // Far 1
                15, 16, 17   // Far 2
            };

            _frustumMesh.vertices = vertices;
            _frustumMesh.triangles = triangles;
            _frustumMesh.RecalculateNormals();
            _frustumMesh.RecalculateBounds();
        }

        private void LateUpdate()
        {
            UpdateFrustumGeometry();
        }
    }
}
