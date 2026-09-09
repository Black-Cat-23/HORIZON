import React, { useMemo } from 'react';
import * as THREE from 'three';

interface FOVFrustumProps {
  progress: number;
}

export const FOVFrustum: React.FC<FOVFrustumProps> = ({ progress }) => {
  // Compute frustum geometry for 4° horizontal x 3° vertical FOV over 60m range
  const frustumLines = useMemo(() => {
    const range = 50.0;
    const halfHRad = THREE.MathUtils.degToRad(2.0); // 4 deg full / 2
    const halfVRad = THREE.MathUtils.degToRad(1.5); // 3 deg full / 2

    const halfW = Math.tan(halfHRad) * range;
    const halfH = Math.tan(halfVRad) * range;

    const points: THREE.Vector3[] = [
      // 4 Edge rays from origin (0, 1.8, -2) to far corners
      new THREE.Vector3(0, 1.8, -2), new THREE.Vector3(-halfW, 1.8 + halfH, -range),
      new THREE.Vector3(0, 1.8, -2), new THREE.Vector3(halfW, 1.8 + halfH, -range),
      new THREE.Vector3(0, 1.8, -2), new THREE.Vector3(halfW, 1.8 - halfH, -range),
      new THREE.Vector3(0, 1.8, -2), new THREE.Vector3(-halfW, 1.8 - halfH, -range),

      // Far boundary rectangle
      new THREE.Vector3(-halfW, 1.8 + halfH, -range), new THREE.Vector3(halfW, 1.8 + halfH, -range),
      new THREE.Vector3(halfW, 1.8 + halfH, -range), new THREE.Vector3(halfW, 1.8 - halfH, -range),
      new THREE.Vector3(halfW, 1.8 - halfH, -range), new THREE.Vector3(-halfW, 1.8 - halfH, -range),
      new THREE.Vector3(-halfW, 1.8 - halfH, -range), new THREE.Vector3(-halfW, 1.8 + halfH, -range),

      // Central optical boresight line
      new THREE.Vector3(0, 1.8, -2), new THREE.Vector3(0, 1.8, -range),
    ];

    const geom = new THREE.BufferGeometry().setFromPoints(points);
    return geom;
  }, []);

  const isVisible = progress >= 0.12 && progress < 0.88;
  const opacity = progress < 0.2 ? THREE.MathUtils.lerp(0, 0.45, (progress - 0.12) / 0.08) : 0.45;

  if (!isVisible) return null;

  return (
    <group>
      <lineSegments geometry={frustumLines}>
        <lineBasicMaterial
          color="#a9d8e8"
          transparent
          opacity={opacity}
          blending={THREE.AdditiveBlending}
        />
      </lineSegments>
    </group>
  );
};
