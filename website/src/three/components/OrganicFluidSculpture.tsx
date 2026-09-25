import React, { useRef, useMemo } from 'react';
import * as THREE from 'three';
import { useFrame } from '@react-three/fiber';

interface OrganicFluidSculptureProps {
  progress: number;
}

// Custom GLSL Shader for Organic Fluid Silk Ribbon with Fresnel Rim Glow
const SilkRibbonShader = {
  vertexShader: `
    uniform float uTime;
    uniform float uProgress;
    varying vec3 vNormal;
    varying vec3 vViewPosition;
    varying vec2 vUv;
    varying vec3 vWorldPosition;

    void main() {
      vUv = uv;
      vNormal = normalize(normalMatrix * normal);
      
      // Undulating organic silk waves
      vec3 pos = position;
      float wave1 = sin(pos.x * 0.4 + uTime * 0.8 + uProgress * 4.0) * 0.35;
      float wave2 = cos(pos.y * 0.5 + uTime * 0.6) * 0.25;
      float wave3 = sin(pos.z * 0.3 + uTime * 1.0) * 0.30;
      pos += normal * (wave1 + wave2 + wave3);

      vec4 worldPosition = modelMatrix * vec4(pos, 1.0);
      vWorldPosition = worldPosition.xyz;
      vec4 mvPosition = viewMatrix * worldPosition;
      vViewPosition = -mvPosition.xyz;
      gl_Position = projectionMatrix * mvPosition;
    }
  `,
  fragmentShader: `
    uniform float uTime;
    uniform float uProgress;
    uniform vec3 uStateColor;
    varying vec3 vNormal;
    varying vec3 vViewPosition;
    varying vec2 vUv;
    varying vec3 vWorldPosition;

    void main() {
      vec3 normal = normalize(vNormal);
      vec3 viewDir = normalize(vViewPosition);

      // Fresnel Rim Effect (Japanese luxury glass / silk edge glow)
      float fresnel = pow(1.0 - max(dot(normal, viewDir), 0.0), 3.2);
      
      // Iridescent dispersion gradient
      vec3 deepVoid = vec3(0.015, 0.035, 0.06);
      vec3 midSilk = vec3(0.08, 0.14, 0.22);
      vec3 rimHighlight = mix(vec3(0.83, 0.88, 1.0), uStateColor, 0.5);

      // Energy wave propagating down the ribbon
      float pulse = sin(vUv.x * 24.0 - uTime * 2.2 + uProgress * 12.0) * 0.5 + 0.5;
      pulse = pow(pulse, 4.0) * 0.4;

      vec3 baseColor = mix(deepVoid, midSilk, normal.y * 0.5 + 0.5);
      vec3 finalColor = baseColor + (rimHighlight * fresnel * 1.6) + (uStateColor * pulse);

      float alpha = clamp(0.45 + fresnel * 0.55 + pulse * 0.3, 0.0, 1.0);
      gl_FragColor = vec4(finalColor, alpha);
    }
  `,
};

export const OrganicFluidSculpture: React.FC<OrganicFluidSculptureProps> = ({ progress }) => {
  const ribbonGroupRef = useRef<THREE.Group>(null);
  const crystalCoreRef = useRef<THREE.Mesh>(null);
  const outerRingsRef = useRef<THREE.Group>(null);
  const materialRef = useRef<THREE.ShaderMaterial>(null);

  // Dynamic State Color derived from current chapter
  const stateColor = useMemo(() => {
    if (progress >= 0.33 && progress < 0.53) return new THREE.Color('#6fe8a8'); // Lock Green
    if (progress >= 0.53 && progress < 0.63) return new THREE.Color('#e8a15c'); // Disturbance Amber
    if (progress >= 0.63 && progress < 0.72) return new THREE.Color('#e86f7f'); // Loss Red
    if (progress >= 0.72) return new THREE.Color('#6fe8a8'); // Reacquire Green
    return new THREE.Color('#a9d8e8'); // Default Optical Cyan
  }, [progress]);

  const uniforms = useMemo(
    () => ({
      uTime: { value: 0 },
      uProgress: { value: 0 },
      uStateColor: { value: new THREE.Color('#a9d8e8') },
    }),
    []
  );

  useFrame(({ clock }, delta) => {
    const t = clock.getElapsedTime();

    if (materialRef.current) {
      materialRef.current.uniforms.uTime.value = t;
      materialRef.current.uniforms.uProgress.value = progress;
      materialRef.current.uniforms.uStateColor.value.lerp(stateColor, delta * 4);
    }

    if (ribbonGroupRef.current) {
      // Gentle continuous spatial rotation & responsive morph
      ribbonGroupRef.current.rotation.y = t * 0.12 + progress * Math.PI;
      ribbonGroupRef.current.rotation.x = Math.sin(t * 0.15) * 0.2 + progress * 0.5;
      ribbonGroupRef.current.rotation.z = Math.cos(t * 0.1) * 0.15;
    }

    if (crystalCoreRef.current) {
      crystalCoreRef.current.rotation.y = -t * 0.25;
      crystalCoreRef.current.rotation.x = t * 0.18;
      const breathe = 1.0 + Math.sin(t * 2.5) * 0.08;
      crystalCoreRef.current.scale.set(breathe, breathe, breathe);
    }

    if (outerRingsRef.current) {
      outerRingsRef.current.rotation.z = t * 0.06;
      outerRingsRef.current.rotation.y = -t * 0.04;
    }
  });

  return (
    <group position={[0, 1.5, 0]}>
      {/* 1. Organic Swirling Silk Ribbon Knot */}
      <group ref={ribbonGroupRef}>
        <mesh>
          <torusKnotGeometry args={[2.4, 0.45, 180, 48, 2, 3]} />
          <shaderMaterial
            ref={materialRef}
            vertexShader={SilkRibbonShader.vertexShader}
            fragmentShader={SilkRibbonShader.fragmentShader}
            uniforms={uniforms}
            transparent={true}
            side={THREE.DoubleSide}
            depthWrite={false}
          />
        </mesh>
      </group>

      {/* 2. Central Luminous Crystalline Optical Core */}
      <mesh ref={crystalCoreRef} position={[0, 0, 0]}>
        <octahedronGeometry args={[0.95, 0]} />
        <meshPhysicalMaterial
          color="#d5e0ff"
          emissive={stateColor}
          emissiveIntensity={0.65}
          roughness={0.05}
          metalness={0.1}
          transmission={0.9}
          ior={1.65}
          thickness={1.2}
          transparent={true}
          opacity={0.95}
        />
      </mesh>

      {/* Core Volumetric Light Glow Sphere */}
      <mesh position={[0, 0, 0]}>
        <sphereGeometry args={[1.4, 32, 32]} />
        <meshBasicMaterial
          color={stateColor}
          transparent={true}
          opacity={0.18}
          blending={THREE.AdditiveBlending}
        />
      </mesh>

      {/* 3. Architectural Thin Celestial Rings (Hubtown / IVRESS style) */}
      <group ref={outerRingsRef}>
        <mesh rotation={[Math.PI / 3, 0, 0]}>
          <ringGeometry args={[3.8, 3.82, 64]} />
          <meshBasicMaterial color="#d5e0ff" transparent opacity={0.25} side={THREE.DoubleSide} />
        </mesh>
        <mesh rotation={[-Math.PI / 4, Math.PI / 6, 0]}>
          <ringGeometry args={[4.4, 4.415, 64]} />
          <meshBasicMaterial color="#a9d8e8" transparent opacity={0.15} side={THREE.DoubleSide} />
        </mesh>
      </group>
    </group>
  );
};
