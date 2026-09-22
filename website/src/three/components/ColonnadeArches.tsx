import React, { useMemo } from 'react';
import * as THREE from 'three';

export const ColonnadeArches: React.FC = () => {
  const stoneMaterial = useMemo(
    () =>
      new THREE.MeshStandardMaterial({
        color: '#1e2938',
        roughness: 0.75,
        metalness: 0.15,
      }),
    []
  );

  const darkStone = useMemo(
    () =>
      new THREE.MeshStandardMaterial({
        color: '#101722',
        roughness: 0.88,
        metalness: 0.1,
      }),
    []
  );

  // Colossal pillar positions along the left side of the viaduct
  const archPositions = useMemo(() => {
    const items = [];
    const step = 12.0;
    for (let z = 35; z >= -120; z -= step) {
      items.push(z);
    }
    return items;
  }, []);

  return (
    <group position={[-8.5, 0, 0]}>
      {archPositions.map((z, idx) => (
        <group key={idx} position={[0, 0, z]}>
          {/* 1. Main Cathedral Pillar (28m tall) */}
          <mesh position={[0, 14.0, 0]} material={stoneMaterial} castShadow>
            <cylinderGeometry args={[1.6, 2.0, 28, 20]} />
          </mesh>

          {/* Monumental Base Pedestal */}
          <mesh position={[0, 1.2, 0]} material={darkStone}>
            <boxGeometry args={[4.4, 2.4, 4.4]} />
          </mesh>

          {/* Capital Ring Trim & Corbel */}
          <mesh position={[0, 26.5, 0]} material={darkStone}>
            <cylinderGeometry args={[2.4, 1.9, 2.2, 20]} />
          </mesh>

          {/* 2. Soaring Gothic Arch Arm curving over the bridge */}
          <mesh position={[4.0, 31.0, 0]} rotation={[0, 0, -Math.PI / 4]} material={stoneMaterial}>
            <cylinderGeometry args={[1.3, 1.6, 12.0, 16]} />
          </mesh>

          {/* Horizontal Top Archway Span linking colonnades */}
          <mesh position={[0, 28.5, 0]} material={darkStone}>
            <boxGeometry args={[3.2, 3.2, 12.5]} />
          </mesh>

          {/* 3. Subtle Cold Blue Overhead Skylight Illumination */}
          {idx % 2 === 0 && (
            <pointLight position={[0, 28.0, 0]} color="#7fa6ec" intensity={3.5} distance={30} decay={2} />
          )}
        </group>
      ))}
    </group>
  );
};
