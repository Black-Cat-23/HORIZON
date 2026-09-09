import React, { useMemo, useRef } from 'react';
import * as THREE from 'three';
import { useFrame } from '@react-three/fiber';

interface CloudLayerDiveProps {
  progress: number;
}

export const CloudLayerDive: React.FC<CloudLayerDiveProps> = ({ progress }) => {
  const cloudsRef = useRef<THREE.Group>(null);

  // Generate layered cloud discs in the dive transition zone
  const cloudWisps = useMemo(() => {
    const items = [];
    const count = 35;
    for (let i = 0; i < count; i++) {
      items.push({
        x: (Math.random() - 0.5) * 35,
        y: 8.0 + Math.random() * 22,
        z: (Math.random() - 0.5) * 35,
        scale: 4.5 + Math.random() * 8.0,
        opacity: 0.15 + Math.random() * 0.25,
      });
    }
    return items;
  }, []);

  useFrame(({ clock }) => {
    if (cloudsRef.current) {
      cloudsRef.current.rotation.y = clock.getElapsedTime() * 0.015;
    }
  });

  const isDiveZone = progress >= 0.04 && progress <= 0.65;
  if (!isDiveZone) return null;

  return (
    <group ref={cloudsRef}>
      {cloudWisps.map((wisp, idx) => (
        <mesh key={idx} position={[wisp.x, wisp.y, wisp.z]} rotation={[-Math.PI / 2, 0, 0]}>
          <planeGeometry args={[wisp.scale, wisp.scale]} />
          <meshBasicMaterial
            color="#d8e8ff"
            transparent
            opacity={wisp.opacity}
            blending={THREE.AdditiveBlending}
            depthWrite={false}
          />
        </mesh>
      ))}
    </group>
  );
};
