import React, { useRef, useMemo } from 'react';
import * as THREE from 'three';
import { useFrame } from '@react-three/fiber';

interface GroundTerminalStationProps {
  progress: number;
}

export const GroundTerminalStation: React.FC<GroundTerminalStationProps> = ({ progress }) => {
  const gimbalYokeRef = useRef<THREE.Group>(null);
  const telescopeTubeRef = useRef<THREE.Group>(null);
  const beamRef = useRef<THREE.Mesh>(null);

  // Material setup for the ground terminal antenna
  const darkMetal = useMemo(
    () =>
      new THREE.MeshStandardMaterial({
        color: '#121a24',
        metalness: 0.85,
        roughness: 0.25,
      }),
    []
  );

  const whiteAlloy = useMemo(
    () =>
      new THREE.MeshStandardMaterial({
        color: '#dbe5f2',
        metalness: 0.6,
        roughness: 0.3,
      }),
    []
  );

  useFrame(({ clock }, delta) => {
    const t = clock.getElapsedTime();

    if (gimbalYokeRef.current && telescopeTubeRef.current) {
      // Antenna tracking and alignment dynamics
      const targetPan = Math.sin(t * 0.4 + progress * 2.0) * 0.35;
      const targetTilt = -Math.PI / 3.8 + Math.cos(t * 0.3) * 0.15;

      gimbalYokeRef.current.rotation.y = THREE.MathUtils.damp(
        gimbalYokeRef.current.rotation.y,
        targetPan,
        4.0,
        delta
      );
      telescopeTubeRef.current.rotation.x = THREE.MathUtils.damp(
        telescopeTubeRef.current.rotation.x,
        targetTilt,
        4.0,
        delta
      );
    }

    if (beamRef.current) {
      const pulse = 0.85 + Math.sin(t * 8.0) * 0.15;
      beamRef.current.scale.set(pulse, 1, pulse);
    }
  });

  const isBeamActive = progress >= 0.15;

  return (
    <group position={[0, 4.8, 0]}>
      {/* 1. Ground Station Base Pedestal & Observatory Platform */}
      <mesh position={[0, 0.4, 0]} material={darkMetal}>
        <cylinderGeometry args={[3.2, 4.0, 0.8, 32]} />
      </mesh>

      {/* Platform Level Deck */}
      <mesh position={[0, 0.85, 0]} material={whiteAlloy}>
        <cylinderGeometry args={[3.0, 3.0, 0.1, 32]} />
      </mesh>

      {/* 2. Azimuth Gimbal Yoke (Pan Rotation) */}
      <group ref={gimbalYokeRef} position={[0, 0.9, 0]}>
        {/* Turntable */}
        <mesh position={[0, 0.4, 0]} material={darkMetal}>
          <cylinderGeometry args={[2.0, 2.0, 0.8, 32]} />
        </mesh>

        {/* Left Yoke Arm */}
        <mesh position={[-1.6, 2.2, 0]} material={whiteAlloy}>
          <boxGeometry args={[0.5, 2.8, 1.2]} />
        </mesh>
        {/* Right Yoke Arm */}
        <mesh position={[1.6, 2.2, 0]} material={whiteAlloy}>
          <boxGeometry args={[0.5, 2.8, 1.2]} />
        </mesh>

        {/* 3. Elevation Telescope Casing & Optical Aperture (Tilt Rotation) */}
        <group ref={telescopeTubeRef} position={[0, 2.8, 0]} rotation={[-Math.PI / 3.8, 0, 0]}>
          {/* Main Primary Telescope Tube */}
          <mesh position={[0, 0, -1.2]} rotation={[Math.PI / 2, 0, 0]} material={darkMetal}>
            <cylinderGeometry args={[1.2, 1.35, 3.8, 32]} />
          </mesh>

          {/* Optical Aperture Baffle */}
          <mesh position={[0, 0, -3.2]} rotation={[Math.PI / 2, 0, 0]} material={whiteAlloy}>
            <cylinderGeometry args={[1.35, 1.2, 0.8, 32]} />
          </mesh>

          {/* Aperture Glass Lens */}
          <mesh position={[0, 0, -3.4]} rotation={[Math.PI / 2, 0, 0]}>
            <circleGeometry args={[1.1, 32]} />
            <meshPhysicalMaterial
              color="#05080e"
              emissive="#a9d8e8"
              emissiveIntensity={0.6}
              roughness={0.05}
              metalness={0.95}
              transmission={0.9}
            />
          </mesh>

          {/* 4. Powerful Optical Carrier Laser Beam firing into space */}
          {isBeamActive && (
            <group position={[0, 0, -3.5]} rotation={[-Math.PI / 2, 0, 0]}>
              {/* Central Intense Carrier Core */}
              <mesh ref={beamRef} position={[0, 60, 0]}>
                <cylinderGeometry args={[0.06, 0.18, 120, 16]} />
                <meshBasicMaterial color="#6fe8a8" />
              </mesh>

              {/* Volumetric Atmospheric Beam Scatter Cone */}
              <mesh position={[0, 60, 0]}>
                <cylinderGeometry args={[0.2, 1.2, 120, 16]} />
                <meshBasicMaterial
                  color="#6fe8a8"
                  transparent
                  opacity={0.22}
                  blending={THREE.AdditiveBlending}
                />
              </mesh>

              {/* Optical Emitter Point Light */}
              <pointLight color="#6fe8a8" intensity={8.0} distance={40} decay={1.5} />
            </group>
          )}
        </group>
      </group>
    </group>
  );
};
