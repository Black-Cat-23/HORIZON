Shader "Horizon/FrustumVolume"
{
    Properties
    {
        _FrustumColor ("Frustum Color", Color) = (0.498, 0.831, 0.910, 0.12) // #7fd4e8 cyan translucent
        _EdgeColor ("Edge Highlight", Color) = (0.498, 0.831, 0.910, 0.85)
        _ScanlineSpeed ("Scanline Speed", Float) = 1.5
        _ScanlineDensity ("Scanline Density", Float) = 8.0
        _FresnelPower ("Fresnel Power", Float) = 2.5
    }
    SubShader
    {
        Tags { "Queue"="Transparent+10" "RenderType"="Transparent" "IgnoreProjector"="True" }
        Blend SrcAlpha OneMinusSrcAlpha
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
                float3 normal : NORMAL;
                float2 uv : TEXCOORD0;
            };

            struct v2f
            {
                float4 pos : SV_POSITION;
                float3 normal : NORMAL;
                float3 viewDir : TEXCOORD0;
                float3 worldPos : TEXCOORD1;
            };

            float4 _FrustumColor;
            float4 _EdgeColor;
            float _ScanlineSpeed;
            float _ScanlineDensity;
            float _FresnelPower;

            v2f vert (appdata v)
            {
                v2f o;
                o.pos = UnityObjectToClipPos(v.vertex);
                o.worldPos = mul(unity_ObjectToWorld, v.vertex).xyz;
                o.normal = UnityObjectToWorldNormal(v.normal);
                o.viewDir = normalize(_WorldSpaceCameraPos - o.worldPos);
                return o;
            }

            fixed4 frag (v2f i) : SV_Target
            {
                // Fresnel edge glow
                float NdotV = abs(dot(normalize(i.normal), normalize(i.viewDir)));
                float fresnel = pow(1.0 - NdotV, _FresnelPower);

                // Scanning cross-hatch along the frustum length
                float scan = sin((i.worldPos.z * _ScanlineDensity) - (_Time.y * _ScanlineSpeed * 3.14159));
                scan = smoothstep(0.7, 0.95, scan);

                fixed4 col = _FrustumColor;
                col.rgb = lerp(col.rgb, _EdgeColor.rgb, fresnel * 0.75 + scan * 0.4);
                col.a = saturate(_FrustumColor.a + (fresnel * 0.45) + (scan * 0.25));

                return col;
            }
            ENDCG
        }
    }
}
