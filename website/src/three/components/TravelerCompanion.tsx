import React, { useRef } from 'react';
import * as THREE from 'three';
import { useFrame } from '@react-three/fiber';

interface TravelerCompanionProps {
  progress: number;
}

export const TravelerCompanion: React.FC<TravelerCompanionProps> = ({ progress }) => {
  const travelerRef = useRef<THREE.Group>(null);
  const spiritRef = useRef<THREE.Group>(null);
  const capeRef = useRef<THREE.Mesh>(null);

  useFrame(({ clock }) => {
    const t = clock.getElapsedTime();

    // Map scroll progress along the bridge: z = 6.0 down to z = -85.0
    const targetZ = THREE.MathUtils.lerp(6.0, -85.0, progress);

    if (travelerRef.current) {
      travelerRef.current.position.z = targetZ;
      travelerRef.current.position.x = Math.sin(t * 0.35) * 0.35;
      
      const walkBob = Math.abs(Math.sin(targetZ * 1.4)) * 0.08;
      travelerRef.current.position.y = 1.0 + walkBob;
    }

    if (spiritRef.current) {
      spiritRef.current.position.x = -1.5 + Math.sin(t * 2.0) * 0.3;
      spiritRef.current.position.y = 1.5 + Math.cos(t * 2.4) * 0.2;
      spiritRef.current.position.z = 0.4 + Math.sin(t * 1.6) * 0.25;
      spiritRef.current.rotation.y = t * 1.6;
      spiritRef.current.rotation.z = Math.sin(t * 1.8) * 0.2;
    }

    if (capeRef.current) {
      capeRef.current.rotation.x = Math.PI / 8 + Math.sin(t * 3.5) * 0.14;
    }
  });

  return (
    <group ref={travelerRef} position={[0, 1.0, 6.0]}>
      {/* 1. Cloaked Traveler Silhouette */}
      <group>
        {/* Head / Pointed Hood */}
        <mesh position={[0, 1.25, 0]} castShadow>
          <coneGeometry args={[0.35, 0.65, 10]} />
          <meshStandardMaterial color="#080e18" roughness={0.8} />
        </mesh>

        {/* Cloak Body / Torso */}
        <mesh position={[0, 0.55, 0]} castShadow>
          <cylinderGeometry args={[0.3, 0.65, 1.25, 14]} />
          <meshStandardMaterial color="#0c1422" roughness={0.8} />
        </mesh>

        {/* Legs / Boots */}
        <mesh position={[-0.15, -0.25, 0]}>
          <boxGeometry args={[0.15, 0.5, 0.25]} />
          <meshStandardMaterial color="#050810" roughness={0.9} />
        </mesh>
        <mesh position={[0.15, -0.25, 0]}>
          <boxGeometry args={[0.15, 0.5, 0.25]} />
          <meshStandardMaterial color="#050810" roughness={0.9} />
        </mesh>

        {/* Wind-blown Cloak / Cape */}
        <mesh ref={capeRef} position={[0, 0.55, 0.32]} rotation={[Math.PI / 8, 0, 0]}>
          <planeGeometry args={[0.75, 1.15]} />
          <meshStandardMaterial color="#080e18" side={THREE.DoubleSide} roughness={0.85} />
        </mesh>
      </group>

      {/* 2. Floating Luminous Origami / Silk Spirit Companion (Matching Image 1) */}
      <group ref={spiritRef} position={[-1.5, 1.5, 0.4]}>
        {/* Origami Folded Core */}
        <mesh>
          <octahedronGeometry args={[0.35, 0]} />
          <meshBasicMaterial color="#ffffff" />
        </mesh>

        {/* Floating Folded Silk Flaps */}
        <mesh position={[-0.22, 0.08, 0]} rotation={[0, 0, Math.PI / 4]}>
          <planeGeometry args={[0.45, 0.22]} />
          <meshBasicMaterial color="#ffffff" side={THREE.DoubleSide} />
        </mesh>
        <mesh position={[0.22, 0.08, 0]} rotation={[0, 0, -Math.PI / 4]}>
          <planeGeometry args={[0.45, 0.22]} />
          <meshBasicMaterial color="#ffffff" side={THREE.DoubleSide} />
        </mesh>

        {/* Atmospheric Point Light emanating from the spirit */}
        <pointLight color="#dbe9ff" intensity={8.5} distance={20} decay={1.8} />
      </group>
    </group>
  );
};
