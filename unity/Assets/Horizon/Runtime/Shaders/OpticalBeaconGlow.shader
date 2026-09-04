Shader "Horizon/OpticalBeaconGlow"
{
    Properties
    {
        _CoreColor ("Core Luminescence", Color) = (1.0, 1.0, 1.0, 1.0)
        _AuraColor ("Optical Aura Color", Color) = (0.498, 0.831, 0.910, 1.0) // #7fd4e8 cyan
        _Intensity ("Radiant Intensity", Float) = 3.5
        _CoreRadius ("Core Radius", Range(0.01, 0.5)) = 0.08
        _DiffractionRings ("Diffraction Ring Count", Float) = 4.0
    }
    SubShader
    {
        Tags { "Queue"="Transparent" "RenderType"="Transparent" "IgnoreProjector"="True" }
        Blend One One // Additive HDR blending
        ZWrite Off
        Cull Off

        Pass
        {
            CGPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            #include "UnityCG.cginc"

            struct appdata
            {
                float4 vertex : POSITION;
                float2 uv : TEXCOORD0;
            };

            struct v2f
            {
                float4 pos : SV_POSITION;
                float2 uv : TEXCOORD0;
            };

            float4 _CoreColor;
            float4 _AuraColor;
            float _Intensity;
            float _CoreRadius;
            float _DiffractionRings;

            v2f vert (appdata v)
            {
                v2f o;
                o.pos = UnityObjectToClipPos(v.vertex);
                o.uv = v.uv * 2.0 - 1.0; // [-1, 1]
                return o;
            }

            fixed4 frag (v2f i) : SV_Target
            {
                float r = length(i.uv);
                if (r > 1.0) discard;

                // Core Gaussian spot
                float core = exp(- (r * r) / (_CoreRadius * _CoreRadius * 2.0));

                // Airy diffraction pattern rings: J1(x)/x approximation via cosine wave envelope
                float ringWave = cos(r * 3.14159265 * _DiffractionRings * 2.0);
                float ringEnvelope = exp(-r * 3.5);
                float airyRings = max(0.0, ringWave) * ringEnvelope * 0.4;

                // Outer halo falloff: 1 / (1 + r^2)
                float halo = 1.0 / (1.0 + (r * r * 15.0));

                // Composite optical radiance
                float3 col = (_CoreColor.rgb * core * 2.5) +
                             (_AuraColor.rgb * (airyRings + halo) * _Intensity);

                return fixed4(col, 1.0);
            }
            ENDCG
        }
    }
}
