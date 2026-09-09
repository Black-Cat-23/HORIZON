import React from 'react';
import * as THREE from 'three';

interface UncertaintyEllipsoidProps {
  progress: number;
}

export const UncertaintyEllipsoid: React.FC<UncertaintyEllipsoidProps> = ({ progress }) => {
  const isVisible = progress >= 0.05 && progress < 0.38;
  if (!isVisible) return null;

  return (
    <group position={[18, 12, -70]}>
      {/* Outer Uncertainty Wireframe Sphere */}
      <mesh>
        <sphereGeometry args={[8.5, 24, 16]} />
        <meshBasicMaterial
          color="#e8a15c"
          wireframe
          transparent
          opacity={0.2}
          blending={THREE.AdditiveBlending}
        />
      </mesh>

      {/* Uncertainty Volume Core */}
      <mesh>
        <sphereGeometry args={[7.0, 16, 16]} />
        <meshBasicMaterial
          color="#e8a15c"
          transparent
          opacity={0.05}
        />
      </mesh>
    </group>
  );
};
