import React, { useRef, useMemo } from 'react';
import * as THREE from 'three';
import { useFrame, useLoader } from '@react-three/fiber';
import { TextureLoader } from 'three';

// Custom Atmosphere Rayleigh Scattering Glow Shader
const AtmosphereGlowShader = {
  vertexShader: `
    varying vec3 vNormal;
    void main() {
      vNormal = normalize(normalMatrix * normal);
      gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
    }
  `,
  fragmentShader: `
    varying vec3 vNormal;
    void main() {
      // Fresnel rim glow
      float intensity = pow(0.75 - dot(vNormal, vec3(0.0, 0.0, 1.0)), 2.8);
      gl_FragColor = vec4(0.38, 0.65, 1.0, 1.0) * intensity * 1.8;
    }
  `,
};

export const RealisticEarth: React.FC = () => {
  const earthRef = useRef<THREE.Group>(null);
  const cloudsRef = useRef<THREE.Mesh>(null);

  // Load Earth 4K/8K Texture Maps from Blender Assets
  const [albedoMap, bumpMap, specMap, cloudsMap, nightLightsMap] = useLoader(TextureLoader, [
    '/textures/earth/earth albedo.jpg',
    '/textures/earth/earth bump.jpg',
    '/textures/earth/earth land ocean mask.png',
    '/textures/earth/clouds earth.png',
    '/textures/earth/earth night_lights_modified.png',
  ]);

  useMemo(() => {
    albedoMap.colorSpace = THREE.SRGBColorSpace;
    nightLightsMap.colorSpace = THREE.SRGBColorSpace;
  }, [albedoMap, nightLightsMap]);

  useFrame((_, delta) => {
    if (earthRef.current) {
      earthRef.current.rotation.y += delta * 0.015;
    }
    if (cloudsRef.current) {
      cloudsRef.current.rotation.y += delta * 0.022; // Clouds rotate slightly faster
    }
  });

  return (
    <group position={[0, -25, -95]}>
      {/* Main Earth Planet Globe */}
      <group ref={earthRef} rotation={[0.2, 0, 0.15]}>
        <mesh receiveShadow castShadow>
          <sphereGeometry args={[35, 64, 64]} />
          <meshStandardMaterial
            map={albedoMap}
            bumpMap={bumpMap}
            bumpScale={0.8}
            roughnessMap={specMap}
            roughness={0.7}
            metalness={0.1}
          />
        </mesh>

        {/* Dynamic Cloud Atmosphere Shell */}
        <mesh ref={cloudsRef}>
          <sphereGeometry args={[35.35, 64, 64]} />
          <meshStandardMaterial
            map={cloudsMap}
            transparent={true}
            opacity={0.45}
            blending={THREE.AdditiveBlending}
            depthWrite={false}
          />
        </mesh>
      </group>

      {/* Volumetric Atmospheric Rayleigh Glow Shell */}
      <mesh scale={[1.14, 1.14, 1.14]}>
        <sphereGeometry args={[35, 48, 48]} />
        <shaderMaterial
          vertexShader={AtmosphereGlowShader.vertexShader}
          fragmentShader={AtmosphereGlowShader.fragmentShader}
          blending={THREE.AdditiveBlending}
          side={THREE.BackSide}
          transparent={true}
        />
      </mesh>
    </group>
  );
};
