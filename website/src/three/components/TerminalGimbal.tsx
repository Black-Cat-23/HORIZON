import React, { useRef } from 'react';
import * as THREE from 'three';
import { useFrame } from '@react-three/fiber';

interface TerminalGimbalProps {
  progress: number;
  panAngle?: number;
  tiltAngle?: number;
}

export const TerminalGimbal: React.FC<TerminalGimbalProps> = ({
  progress,
  panAngle = 0,
  tiltAngle = 0,
}) => {
  const yokeRef = useRef<THREE.Group>(null);
  const tubeRef = useRef<THREE.Group>(null);

  useFrame((_, delta) => {
    if (yokeRef.current && tubeRef.current) {
      // Smooth dynamic rotation based on tracking or progress
      let targetPan = panAngle;
      let targetTilt = tiltAngle;

      // During Search (Phase 3 ~ 0.24-0.33), simulate spiral search sweep
      if (progress >= 0.22 && progress <= 0.35) {
        const time = Date.now() * 0.003;
        targetPan = Math.sin(time) * 0.35;
        targetTilt = Math.cos(time * 0.8) * 0.25;
      }

      yokeRef.current.rotation.y = THREE.MathUtils.damp(
        yokeRef.current.rotation.y,
        targetPan,
        6,
        delta
      );
      tubeRef.current.rotation.x = THREE.MathUtils.damp(
        tubeRef.current.rotation.x,
        targetTilt,
        6,
        delta
      );
    }
  });

  return (
    <group position={[0, 0, 0]}>
      {/* 1. Base Pedestal Mount */}
      <mesh position={[0, 0.4, 0]}>
        <cylinderGeometry args={[1.8, 2.2, 0.8, 32]} />
        <meshStandardMaterial
          color="#0e1722"
          metalness={0.85}
          roughness={0.25}
        />
      </mesh>

      {/* Pedestal Accent Ring */}
      <mesh position={[0, 0.82, 0]}>
        <cylinderGeometry args={[1.65, 1.65, 0.08, 32]} />
        <meshStandardMaterial
          color="#182330"
          emissive="#a9d8e8"
          emissiveIntensity={0.15}
          metalness={0.9}
          roughness={0.1}
        />
      </mesh>

      {/* 2. Azimuth Yoke (Pan Rotation) */}
      <group ref={yokeRef} position={[0, 0.86, 0]}>
        {/* Yoke Turntable */}
        <mesh position={[0, 0.25, 0]}>
          <cylinderGeometry args={[1.5, 1.5, 0.5, 32]} />
          <meshStandardMaterial color="#121a24" metalness={0.8} roughness={0.3} />
        </mesh>

        {/* Left Yoke Arm */}
        <mesh position={[-1.1, 1.4, 0]}>
          <boxGeometry args={[0.35, 1.8, 0.8]} />
          <meshStandardMaterial color="#182330" metalness={0.8} roughness={0.2} />
        </mesh>

        {/* Right Yoke Arm */}
        <mesh position={[1.1, 1.4, 0]}>
          <boxGeometry args={[0.35, 1.8, 0.8]} />
          <meshStandardMaterial color="#182330" metalness={0.8} roughness={0.2} />
        </mesh>

        {/* 3. Elevation Casing & Telescope Tube (Tilt Rotation) */}
        <group ref={tubeRef} position={[0, 1.8, 0]}>
          {/* Main Sensor Optical Cylinder */}
          <mesh rotation={[Math.PI / 2, 0, 0]} position={[0, 0, -0.6]}>
            <cylinderGeometry args={[0.75, 0.82, 2.2, 32]} />
            <meshStandardMaterial color="#0B1018" metalness={0.9} roughness={0.15} />
          </mesh>

          {/* Aperture Sunshade & Baffle */}
          <mesh rotation={[Math.PI / 2, 0, 0]} position={[0, 0, -1.8]}>
            <cylinderGeometry args={[0.85, 0.75, 0.6, 32]} />
            <meshStandardMaterial color="#121a24" metalness={0.7} roughness={0.3} />
          </mesh>

          {/* Optical Glass Lens (Aperture Front) */}
          <mesh rotation={[Math.PI / 2, 0, 0]} position={[0, 0, -1.9]}>
            <circleGeometry args={[0.7, 32]} />
            <meshStandardMaterial
              color="#05070B"
              emissive="#a9d8e8"
              emissiveIntensity={0.4}
              metalness={0.95}
              roughness={0.05}
              transparent
              opacity={0.85}
            />
          </mesh>

          {/* Aperture Status Ring (Changes color to lock green / loss red) */}
          <mesh rotation={[Math.PI / 2, 0, 0]} position={[0, 0, -2.05]}>
            <ringGeometry args={[0.72, 0.84, 32]} />
            <meshBasicMaterial
              color={
                progress >= 0.35 && progress < 0.6
                  ? '#6fe8a8'
                  : progress >= 0.6 && progress < 0.75
                  ? '#e86f7f'
                  : '#a9d8e8'
              }
            />
          </mesh>
        </group>
      </group>
    </group>
  );
};
