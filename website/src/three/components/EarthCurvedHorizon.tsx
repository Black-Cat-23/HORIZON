import React, { useRef, useMemo } from 'react';
import * as THREE from 'three';
import { useFrame, useLoader } from '@react-three/fiber';
import { TextureLoader } from 'three';

// Fine, Delicate Rayleigh Atmosphere Limb Glow (Hugging only the outer space horizon curve)
const AtmosphereLimbGlowShader = {
  vertexShader: `
    varying vec3 vNormal;
    varying vec3 vPositionView;
    void main() {
      vNormal = normalize(normalMatrix * normal);
      vec4 mvPos = modelViewMatrix * vec4(position, 1.0);
      vPositionView = normalize(-mvPos.xyz);
      gl_Position = projectionMatrix * mvPos;
    }
  `,
  fragmentShader: `
    varying vec3 vNormal;
    varying vec3 vPositionView;
    void main() {
      float fresnel = 1.0 - max(0.0, dot(vNormal, vPositionView));
      float intensity = pow(fresnel, 4.0);
      vec3 atmosphereColor = vec3(0.35, 0.72, 1.0);
      gl_FragColor = vec4(atmosphereColor, 0.48) * intensity;
    }
  `,
};

interface EarthCurvedHorizonProps {
  progress: number;
}

export const EarthCurvedHorizon: React.FC<EarthCurvedHorizonProps> = ({ progress }) => {
  const earthGlobeRef = useRef<THREE.Group>(null);
  const cloudsRef = useRef<THREE.Mesh>(null);

  // Grand Curved Planet Horizon (Top ~40% visible in Hero section)
  const earthRadius = 38.0;
  const earthCenter = [0.0, -32.5, 0.0] as const;

  // Load Earth 2 Blender Texture Maps from /textures/earth/
  const [albedoMap, bumpMap, specMap, cloudsMap] = useLoader(TextureLoader, [
    '/textures/earth/earth albedo.jpg',
    '/textures/earth/earth bump.jpg',
    '/textures/earth/earth land ocean mask.png',
    '/textures/earth/clouds earth.png',
  ]);

  useMemo(() => {
    albedoMap.colorSpace = THREE.SRGBColorSpace;
  }, [albedoMap]);

  useFrame((_, delta) => {
    if (earthGlobeRef.current) {
      earthGlobeRef.current.rotation.y += delta * 0.025;
    }
    if (cloudsRef.current) {
      cloudsRef.current.rotation.y += delta * 0.04;
    }
  });

  const isVisible = progress < 0.25;

  return (
    <group position={earthCenter} visible={isVisible}>
      {/* 1. Main Curved Earth Planet Sphere (Cinematic Realistic Lighting & Opacity) */}
      <group ref={earthGlobeRef} rotation={[-0.75, -1.8, 0.0]}>
        <mesh receiveShadow castShadow>
          <sphereGeometry args={[earthRadius, 64, 64]} />
          <meshStandardMaterial
            map={albedoMap}
            bumpMap={bumpMap}
            bumpScale={0.55}
            roughnessMap={specMap}
            roughness={0.50}
            metalness={0.06}
            transparent={true}
            opacity={0.92}
          />
        </mesh>

        {/* Dynamic Atmospheric Cloud Shell */}
        <mesh ref={cloudsRef}>
          <sphereGeometry args={[earthRadius + 0.18, 64, 64]} />
          <meshStandardMaterial
            map={cloudsMap}
            transparent={true}
            opacity={0.42}
            depthWrite={false}
          />
        </mesh>
      </group>

      {/* 2. Outer Atmospheric Rayleigh Limb Edge */}
      <mesh scale={[1.015, 1.015, 1.015]}>
        <sphereGeometry args={[earthRadius, 64, 64]} />
        <shaderMaterial
          vertexShader={AtmosphereLimbGlowShader.vertexShader}
          fragmentShader={AtmosphereLimbGlowShader.fragmentShader}
          blending={THREE.AdditiveBlending}
          side={THREE.FrontSide}
          transparent={true}
          depthWrite={false}
        />
      </mesh>
    </group>
  );
};
