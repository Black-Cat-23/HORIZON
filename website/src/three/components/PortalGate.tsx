import React, { useMemo } from 'react';
import * as THREE from 'three';

export const PortalGate: React.FC = () => {
  const gateStone = useMemo(
    () =>
      new THREE.MeshStandardMaterial({
        color: '#151f2d',
        roughness: 0.8,
        metalness: 0.15,
      }),
    []
  );

  return (
    <group position={[0, 0, -95]}>
      {/* 1. Gatehouse Wall */}
      {/* Left Wall Wing */}
      <mesh position={[-28, 22, 0]} material={gateStone}>
        <boxGeometry args={[48, 50, 8]} />
      </mesh>
      {/* Right Wall Wing */}
      <mesh position={[28, 22, 0]} material={gateStone}>
        <boxGeometry args={[48, 50, 8]} />
      </mesh>
      {/* Upper Archway Lintel */}
      <mesh position={[0, 36, 0]} material={gateStone}>
        <boxGeometry args={[18, 24, 8]} />
      </mesh>

      {/* 2. Luminous Doorway Portal */}
      <group position={[0, 7.5, 0]}>
        {/* Doorway Backing Light Plane */}
        <mesh position={[0, 0, 0.5]}>
          <planeGeometry args={[7.0, 15.0]} />
          <meshBasicMaterial color="#ffffff" />
        </mesh>

        {/* Outer Halo Glow */}
        <mesh position={[0, 0, 0.8]}>
          <planeGeometry args={[12.0, 22.0]} />
          <meshBasicMaterial
            color="#bad6ff"
            transparent
            opacity={0.45}
            blending={THREE.AdditiveBlending}
          />
        </mesh>

        {/* 3. Forward Projecting Spotlight Illuminating the Roadway */}
        <spotLight
          position={[0, 2, 1]}
          target-position={[0, 1, 80]}
          color="#dbe8ff"
          intensity={40.0}
          distance={140}
          angle={Math.PI / 4.5}
          penumbra={0.8}
          decay={1.2}
        />
      </group>
    </group>
  );
};
