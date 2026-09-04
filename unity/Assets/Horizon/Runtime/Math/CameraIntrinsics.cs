using System;
using UnityEngine;

namespace Horizon.Math
{
    /// <summary>
    /// Explicit pinhole camera intrinsics and coordinate transformations.
    /// Source-backed by standard geometric optics and project contract.
    /// </summary>
    [Serializable]
    public class CameraIntrinsics
    {
        [Tooltip("Horizontal focal length in pixels")]
        public float Fx = 1430.0f;

        [Tooltip("Vertical focal length in pixels")]
        public float Fy = 1430.0f;

        [Tooltip("Principal point X coordinate in pixels")]
        public float Cx = 960.0f;

        [Tooltip("Principal point Y coordinate in pixels")]
        public float Cy = 540.0f;

        [Tooltip("Sensor resolution width in pixels")]
        public int ImageWidth = 1920;

        [Tooltip("Sensor resolution height in pixels")]
        public int ImageHeight = 1080;

        [Tooltip("Field of view in degrees (horizontal)")]
        public float HorizontalFovDeg = 40.0f;

        public CameraIntrinsics() { }

        public CameraIntrinsics(int width, int height, float hFovDeg)
        {
            SetFromResolutionAndFov(width, height, hFovDeg);
        }

        public void SetFromResolutionAndFov(int width, int height, float hFovDeg)
        {
            ImageWidth = width;
            ImageHeight = height;
            HorizontalFovDeg = hFovDeg;

            Cx = width * 0.5f;
            Cy = height * 0.5f;

            float hFovRad = hFovDeg * Mathf.Deg2Rad;
            Fx = (width * 0.5f) / Mathf.Tan(hFovRad * 0.5f);
            Fy = Fx; // Square pixels assumption (PROVISIONAL)
        }

        public float VerticalFovDeg
        {
            get
            {
                float vFovRad = 2.0f * Mathf.Atan((ImageHeight * 0.5f) / Fy);
                return vFovRad * Mathf.Rad2Deg;
            }
        }

        /// <summary>
        /// Converts 3D camera-frame coordinates [Xc, Yc, Zc] into 2D image coordinates (u, v).
        /// Returns false if target is behind the camera (Zc <= 0).
        /// </summary>
        public bool WorldToPixel(Vector3 pCam, out Vector2 pixel)
        {
            if (pCam.z <= 0.001f)
            {
                pixel = Vector2.zero;
                return false;
            }

            float u = (Fx * (pCam.x / pCam.z)) + Cx;
            float v = (Fy * (pCam.y / pCam.z)) + Cy;
            pixel = new Vector2(u, v);
            return true;
        }

        /// <summary>
        /// Converts 2D pixel coordinates (u, v) into boresight angular errors (thetaX, thetaY) in radians.
        /// Formulation: thetaX = atan((u - Cx) / Fx), thetaY = atan((v - Cy) / Fy).
        /// </summary>
        public Vector2 PixelToAnglesRad(Vector2 pixel)
        {
            float thetaX = Mathf.Atan((pixel.x - Cx) / Fx);
            float thetaY = Mathf.Atan((pixel.y - Cy) / Fy);
            return new Vector2(thetaX, thetaY);
        }

        /// <summary>
        /// Converts 2D pixel coordinates (u, v) into boresight angular errors (thetaX, thetaY) in degrees.
        /// </summary>
        public Vector2 PixelToAnglesDeg(Vector2 pixel)
        {
            Vector2 rad = PixelToAnglesRad(pixel);
            return rad * Mathf.Rad2Deg;
        }

        /// <summary>
        /// Checks if a pixel falls within active sensor bounds.
        /// </summary>
        public bool IsInSensorBounds(Vector2 pixel)
        {
            return pixel.x >= 0 && pixel.x <= ImageWidth &&
                   pixel.y >= 0 && pixel.y <= ImageHeight;
        }
    }
}
