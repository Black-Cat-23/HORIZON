using System;
using UnityEngine;

namespace Horizon.Visual
{
    /// <summary>
    /// Renders the physical optical line-of-sight (LOS) alignment ray connecting
    /// the camera optical aperture to the target beacon. Modulates color and pulse based on tracking state.
    /// </summary>
    [RequireComponent(typeof(LineRenderer))]
    public class LosRenderer : MonoBehaviour
    {
        public Transform CameraAperture;
        public Transform TargetBeacon;
        public Horizon.Control.ModeManager ModeManager;

        private LineRenderer _line;
        private Material _beamMaterial;

        private static readonly int BeamColorProp = Shader.PropertyToID("_BeamColor");

        private void Awake()
        {
            _line = GetComponent<LineRenderer>();
            _line.positionCount = 2;
            _line.startWidth = 0.06f;
            _line.endWidth = 0.08f;
            _line.useWorldSpace = true;

            _beamMaterial = _line.material;
        }

        private void LateUpdate()
        {
            if (CameraAperture == null || TargetBeacon == null) return;

            _line.SetPosition(0, CameraAperture.position);
            _line.SetPosition(1, TargetBeacon.position);

            UpdateBeamColor();
        }

        private void UpdateBeamColor()
        {
            if (ModeManager == null || _beamMaterial == null) return;

            Color targetColor = Horizon.HorizonTokens.LockCyanColor;

            switch (ModeManager.CurrentMode)
            {
                case TrackMode.Search:
                case TrackMode.Acquire:
                    targetColor = Horizon.HorizonTokens.LockCyanColor;
                    break;

                case TrackMode.Track:
                    targetColor = Horizon.HorizonTokens.ConfirmGreenColor;
                    break;

                case TrackMode.Degraded:
                    targetColor = Horizon.HorizonTokens.DisturbanceAmberColor;
                    break;

                case TrackMode.Reacquire:
                    targetColor = Horizon.HorizonTokens.LostRedColor;
                    break;
            }

            if (_beamMaterial.HasProperty(BeamColorProp))
            {
                _beamMaterial.SetColor(BeamColorProp, targetColor);
            }
        }
    }
}
