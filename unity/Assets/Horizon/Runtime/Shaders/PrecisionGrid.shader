Shader "Horizon/PrecisionGrid"
{
    Properties
    {
        _VoidColor ("Void Background Color", Color) = (0.027, 0.035, 0.071, 1.0) // #070912
        _MajorGridColor ("Major Grid Color", Color) = (0.498, 0.831, 0.910, 0.35) // #7fd4e8 cyan
        _MinorGridColor ("Minor Grid Color", Color) = (0.078, 0.102, 0.188, 0.85) // #141a30 field
        _MajorGridSpacing ("Major Grid Spacing", Float) = 5.0
        _MinorGridSpacing ("Minor Grid Spacing", Float) = 1.0
        _LineWidth ("Line Width", Float) = 0.02
        _FadeDistance ("Fade Distance", Float) = 120.0
    }
    SubShader
    {
        Tags { "RenderType"="Opaque" "Queue"="Geometry-10" }
        LOD 100

        Pass
        {
            CGPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            #include "UnityCG.cginc"

            struct appdata
            {
                float4 vertex : POSITION;
            };

            struct v2f
            {
                float4 pos : SV_POSITION;
                float3 worldPos : TEXCOORD0;
            };

            float4 _VoidColor;
            float4 _MajorGridColor;
            float4 _MinorGridColor;
            float _MajorGridSpacing;
            float _MinorGridSpacing;
            float _LineWidth;
            float _FadeDistance;

            v2f vert (appdata v)
            {
                v2f o;
                o.pos = UnityObjectToClipPos(v.vertex);
                o.worldPos = mul(unity_ObjectToWorld, v.vertex).xyz;
                return o;
            }

            float GridIntensity(float2 coord, float spacing, float width)
            {
                float2 g = abs(frac(coord / spacing - 0.5) - 0.5) / (fwidth(coord / spacing) + width);
                float lineVal = 1.0 - min(min(g.x, g.y), 1.0);
                return saturate(lineVal);
            }

            fixed4 frag (v2f i) : SV_Target
            {
                float2 planeXZ = i.worldPos.xz;
                float dist = length(planeXZ);

                // Anti-aliased procedural grid lines
                float minor = GridIntensity(planeXZ, _MinorGridSpacing, _LineWidth * 0.5);
                float major = GridIntensity(planeXZ, _MajorGridSpacing, _LineWidth);

                // Radial concentric reference rings every 10 meters
                float ring = 1.0 - saturate(abs(frac(dist / 10.0 - 0.5) - 0.5) / (fwidth(dist / 10.0) + 0.03));

                // Composite color
                fixed4 col = _VoidColor;
                col = lerp(col, _MinorGridColor, minor * 0.7);
                col = lerp(col, _MajorGridColor, major * 0.85);
                col = lerp(col, _MajorGridColor * 1.2, ring * 0.6);

                // Distance fade
                float fade = saturate(1.0 - (dist / _FadeDistance));
                col.rgb *= fade;

                return col;
            }
            ENDCG
        }
    }
}
