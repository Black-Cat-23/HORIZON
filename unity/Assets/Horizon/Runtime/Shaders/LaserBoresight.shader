Shader "Horizon/LaserBoresight"
{
    Properties
    {
        _BeamColor ("Beam Core Color", Color) = (0.498, 0.831, 0.910, 1.0) // #7fd4e8 cyan
        _CoreBrightness ("Core Brightness", Float) = 2.5
        _PulseSpeed ("Pulse Speed", Float) = 4.0
        _PulseFrequency ("Pulse Frequency", Float) = 6.0
    }
    SubShader
    {
        Tags { "Queue"="Transparent+20" "RenderType"="Transparent" "IgnoreProjector"="True" }
        Blend One One // Additive
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

            float4 _BeamColor;
            float _CoreBrightness;
            float _PulseSpeed;
            float _PulseFrequency;

            v2f vert (appdata v)
            {
                v2f o;
                o.pos = UnityObjectToClipPos(v.vertex);
                o.uv = v.uv;
                return o;
            }

            fixed4 frag (v2f i) : SV_Target
            {
                // Core beam intensity across width (V axis centered at 0.5)
                float d = abs(i.uv.y - 0.5) * 2.0; // [0, 1]
                float core = exp(- (d * d) * 12.0);

                // Longitudinal pulse wave (U axis along beam length)
                float pulse = sin((i.uv.x * _PulseFrequency) - (_Time.y * _PulseSpeed));
                pulse = (pulse * 0.5) + 0.5;

                float intensity = core * (0.8 + pulse * 0.4) * _CoreBrightness;

                float3 rgb = _BeamColor.rgb * intensity;
                return fixed4(rgb, 1.0);
            }
            ENDCG
        }
    }
}
