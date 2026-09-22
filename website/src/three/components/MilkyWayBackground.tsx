import React, { useMemo } from 'react';
import * as THREE from 'three';
import { useLoader } from '@react-three/fiber';
import { TextureLoader } from 'three';

export const MilkyWayBackground: React.FC = () => {
  const starsMap = useLoader(TextureLoader, '/images/5.jpg');

  useMemo(() => {
    starsMap.colorSpace = THREE.SRGBColorSpace;
  }, [starsMap]);

  return (
    <mesh>
      <sphereGeometry args={[350, 48, 48]} />
      <meshBasicMaterial
        map={starsMap}
        side={THREE.BackSide}
        transparent={true}
        opacity={0.85}
      />
    </mesh>
  );
};
