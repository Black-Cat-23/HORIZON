import React, { useMemo } from 'react';
import * as THREE from 'three';

interface OpticalBeamProps {
  progress: number;
}

export const OpticalBeam: React.FC<OpticalBeamProps> = ({ progress }) => {
  const isLocked = (progress >= 0.35 && progress < 0.53) || (progress >= 0.74 && progress < 0.98);

  const beamLine = useMemo(() => {
    const points = [
      new THREE.Vector3(0, 1.8, -2),
      new THREE.Vector3(0, 2.5, -55),
    ];
    const geom = new THREE.BufferGeometry().setFromPoints(points);
    const mat = new THREE.LineBasicMaterial({
      color: '#6fe8a8',
      transparent: true,
      opacity: 0.8,
      blending: THREE.AdditiveBlending,
    });
    return new THREE.Line(geom, mat);
  }, []);

  if (!isLocked) return null;

  return (
    <group>
      {/* Primary Optical Carrier Line */}
      <primitive object={beamLine} />

      {/* Atmospheric Beam Scatter Tube */}
      <mesh position={[0, 2.15, -28.5]} rotation={[Math.PI / 2, 0, 0]}>
        <cylinderGeometry args={[0.08, 0.25, 53, 16]} />
        <meshBasicMaterial
          color="#6fe8a8"
          transparent
          opacity={0.12}
          blending={THREE.AdditiveBlending}
        />
      </mesh>
    </group>
  );
};
